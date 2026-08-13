"""Committed shared memory for the P1.3 S1 baseline.

The implementation is deliberately small and replaceable: process-local
episode records, versioned structured facts, and deterministic lexical
retrieval.  It performs no network or model calls.  Only the runner-side S1
finalizer publishes episode records; worker threads merely produce proposals.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from threading import RLock
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

MEMORY_BACKEND_ID = "in_memory_keyword"
MAX_MEMORY_TOP_K = 100
MAX_MEMORY_CONTEXT_CHARS = 100_000
_TOKEN_PATTERN = re.compile(r"\w+", flags=re.UNICODE)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _stable_id(prefix: str, value: Any) -> str:
    digest = hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()
    return f"{prefix}-{digest[:24]}"


def _as_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return _canonical_json(value)


def _tokens(value: str) -> list[str]:
    return _TOKEN_PATTERN.findall(value.casefold())


class EpisodeMemory(BaseModel):
    """One immutable, committed episode memory item."""

    model_config = ConfigDict(frozen=True)

    item_id: str
    episode_id: str
    task_family: str
    task: str
    answer: str
    committed: Literal[True] = True


class FactVersion(BaseModel):
    """One immutable value in an auditable structured-fact history."""

    model_config = ConfigDict(frozen=True)

    item_id: str
    key: str
    value: Any
    evidence_refs: tuple[str, ...] = ()


class FactHistory(BaseModel):
    """All non-destructive versions for one structured-fact key."""

    model_config = ConfigDict(frozen=True)

    key: str
    versions: tuple[FactVersion, ...] = ()


class MemorySearchHit(BaseModel):
    """Bounded deterministic lexical-search evidence."""

    model_config = ConfigDict(frozen=True)

    item_id: str
    kind: Literal["episode", "fact"]
    score: int = Field(ge=1)
    text: str


class SharedMemory:
    """Deliberately simple shared-memory facade from the P0 design."""

    backend_id = "abstract"

    def store_episode(self, episode_id: str, events: Any) -> EpisodeMemory:
        raise NotImplementedError

    def load_episode(self, episode_id: str) -> EpisodeMemory | None:
        raise NotImplementedError

    def upsert_fact(
        self, key: str, value: Any, evidence_refs: Sequence[str] | None = None
    ) -> FactVersion:
        raise NotImplementedError

    def get_fact(self, key: str) -> FactHistory | None:
        raise NotImplementedError

    def search(
        self, query: str, k: int = 5, *, max_chars: int | None = None
    ) -> list[MemorySearchHit]:
        raise NotImplementedError


class InMemoryKeywordMemory(SharedMemory):
    """Thread-safe committed store with reproducible keyword retrieval.

    There is intentionally no staging area in this backend.  A detached S1
    worker cannot publish anything because it receives only read methods and
    returns a proposal to ``EpisodeRunner``.  ``store_episode`` is the atomic
    publication boundary called by the accepted runner outcome finalizer.
    """

    backend_id = MEMORY_BACKEND_ID

    def __init__(self) -> None:
        self._episodes: dict[str, EpisodeMemory] = {}
        self._facts: dict[str, list[FactVersion]] = {}
        self._lock = RLock()

    def store_episode(self, episode_id: str, events: Any) -> EpisodeMemory:
        """Atomically publish one committed episode; never overwrite it."""
        if not isinstance(episode_id, str) or not episode_id:
            raise ValueError("episode_id must be a non-empty string")
        if isinstance(events, EpisodeMemory):
            if events.episode_id != episode_id:
                raise ValueError("episode_id does not match the memory item")
            task_family, task, answer = events.task_family, events.task, events.answer
        elif isinstance(events, Mapping):
            task_family = _as_text(events.get("task_family", ""))
            task = _as_text(events.get("task", events.get("input", "")))
            answer = _as_text(events.get("answer", events.get("output", "")))
        else:
            raise TypeError("episode memory payload must be a mapping or EpisodeMemory")

        identity = {
            "episode_id": episode_id,
            "task_family": task_family,
            "task": task,
            "answer": answer,
        }
        item = EpisodeMemory(
            item_id=_stable_id("mem-episode", identity),
            episode_id=episode_id,
            task_family=task_family,
            task=task,
            answer=answer,
        )
        with self._lock:
            existing = self._episodes.get(episode_id)
            if existing is not None:
                if existing.item_id != item.item_id:
                    raise ValueError(
                        f"committed episode {episode_id!r} cannot be overwritten"
                    )
                return existing.model_copy(deep=True)
            self._episodes[episode_id] = item
            return item.model_copy(deep=True)

    def load_episode(self, episode_id: str) -> EpisodeMemory | None:
        with self._lock:
            item = self._episodes.get(episode_id)
            return item.model_copy(deep=True) if item is not None else None

    def upsert_fact(
        self, key: str, value: Any, evidence_refs: Sequence[str] | None = None
    ) -> FactVersion:
        """Idempotently add a value, preserving every conflicting version."""
        if not isinstance(key, str) or not key:
            raise ValueError("fact key must be a non-empty string")
        copied_value = copy.deepcopy(value)
        refs = tuple(str(ref) for ref in (evidence_refs or ()))
        value_identity = _canonical_json(copied_value)
        with self._lock:
            versions = self._facts.setdefault(key, [])
            for existing in versions:
                if _canonical_json(existing.value) == value_identity:
                    return existing.model_copy(deep=True)
            version = FactVersion(
                item_id=_stable_id(
                    "mem-fact",
                    {"key": key, "value": copied_value, "ordinal": len(versions) + 1},
                ),
                key=key,
                value=copied_value,
                evidence_refs=refs,
            )
            versions.append(version)
            return version.model_copy(deep=True)

    def get_fact(self, key: str) -> FactHistory | None:
        with self._lock:
            versions = self._facts.get(key)
            if not versions:
                return None
            return FactHistory(
                key=key,
                versions=tuple(version.model_copy(deep=True) for version in versions),
            )

    def search(
        self, query: str, k: int = 5, *, max_chars: int | None = None
    ) -> list[MemorySearchHit]:
        """Search a committed snapshot using stable lexical scoring.

        Score is the sum of per-token occurrence counts for unique query
        tokens.  Results are sorted by descending score and then stable item
        ID, so identical committed state, query, and bounds reproduce exactly.
        """
        if isinstance(k, bool) or not isinstance(k, int) or not 1 <= k <= MAX_MEMORY_TOP_K:
            raise ValueError(f"k must be an integer in [1, {MAX_MEMORY_TOP_K}]")
        if max_chars is not None and (
            isinstance(max_chars, bool)
            or not isinstance(max_chars, int)
            or not 1 <= max_chars <= MAX_MEMORY_CONTEXT_CHARS
        ):
            raise ValueError(
                f"max_chars must be an integer in [1, {MAX_MEMORY_CONTEXT_CHARS}]"
            )
        query_tokens = set(_tokens(query))
        if not query_tokens:
            return []

        with self._lock:
            episodes = [item.model_copy(deep=True) for item in self._episodes.values()]
            facts = [
                version.model_copy(deep=True)
                for versions in self._facts.values()
                for version in versions
            ]

        candidates: list[MemorySearchHit] = []
        for item in episodes:
            text = (
                f"episode_id: {item.episode_id}\n"
                f"task_family: {item.task_family}\n"
                f"task: {item.task}\nanswer: {item.answer}"
            )
            score = _lexical_score(query_tokens, text)
            if score:
                candidates.append(
                    MemorySearchHit(
                        item_id=item.item_id, kind="episode", score=score, text=text
                    )
                )
        for version in facts:
            text = (
                f"fact_key: {version.key}\nvalue: {_as_text(version.value)}\n"
                f"evidence_refs: {_canonical_json(version.evidence_refs)}"
            )
            score = _lexical_score(query_tokens, text)
            if score:
                candidates.append(
                    MemorySearchHit(
                        item_id=version.item_id, kind="fact", score=score, text=text
                    )
                )

        ordered = sorted(candidates, key=lambda hit: (-hit.score, hit.item_id))[:k]
        if max_chars is None:
            return [hit.model_copy(deep=True) for hit in ordered]

        bounded: list[MemorySearchHit] = []
        remaining = max_chars
        for hit in ordered:
            if remaining <= 0:
                break
            retained = hit.text[:remaining]
            if retained:
                bounded.append(hit.model_copy(update={"text": retained}, deep=True))
                remaining -= len(retained)
        return bounded

    @property
    def committed_episode_count(self) -> int:
        with self._lock:
            return len(self._episodes)


def _lexical_score(query_tokens: set[str], text: str) -> int:
    counts = Counter(_tokens(text))
    return sum(counts[token] for token in query_tokens)


__all__ = [
    "MEMORY_BACKEND_ID",
    "MAX_MEMORY_TOP_K",
    "MAX_MEMORY_CONTEXT_CHARS",
    "EpisodeMemory",
    "FactVersion",
    "FactHistory",
    "MemorySearchHit",
    "SharedMemory",
    "InMemoryKeywordMemory",
]
