"""P1.3 S1: one LLM inference plus committed shared memory/RAG.

S1 differs from S0 only by deterministic retrieval and baseline-local,
runner-authorized memory publication.  Retrieval and writing perform zero LLM
calls.  This module does not contain A/B/Y lanes, MoA, tools, judges, semantic
geometry, or the future ABY Commit Barrier.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from ..events import Event, EventLog
from ..experiments.config import ExperimentConfig
from ..experiments.system import EpisodeInput, EpisodeResult
from ..memory import (
    MAX_MEMORY_CONTEXT_CHARS,
    MAX_MEMORY_TOP_K,
    MEMORY_BACKEND_ID,
    InMemoryKeywordMemory,
    MemorySearchHit,
    SharedMemory,
)
from ..providers import (
    FakeProvider,
    LLMMessage,
    LLMProvider,
    LLMRequest,
    OpenAICompatProvider,
    ProviderError,
)
from .s0 import _extract_task, validate_s0_provider_config

S1_SYSTEM_ID = "S1"
S1_PROMPT_VERSION = "S1_PROMPT_V0_1"
S1_SYSTEM_PROMPT_V0_1 = (
    "Answer the supplied task directly and correctly. Use retrieved memory "
    "when relevant, and ignore retrieved memory when it is irrelevant."
)
S1_USER_TEMPLATE_V0_1 = "Task:\n{task}\n\nRetrieved committed memory:\n{memory_context}"
S1_PROMPT_SHA256 = hashlib.sha256(
    (S1_SYSTEM_PROMPT_V0_1 + "\n" + S1_USER_TEMPLATE_V0_1).encode("utf-8")
).hexdigest()

_PENDING_EVENTS_KEY = "_s1_pending_events"
_PENDING_WRITE_KEY = "_s1_pending_memory_write"


def _bounded_context(
    hits: list[MemorySearchHit], max_context_chars: int
) -> tuple[str, list[MemorySearchHit]]:
    """Render retained hits deterministically within the exact char budget."""
    parts: list[str] = []
    retained: list[MemorySearchHit] = []
    remaining = max_context_chars
    for hit in hits:
        separator = "\n\n" if parts else ""
        section = (
            f"[{hit.item_id} kind={hit.kind} score={hit.score}]\n{hit.text}"
        )
        available = remaining - len(separator)
        if available <= 0:
            break
        kept = section[:available]
        if not kept:
            break
        parts.append(separator + kept)
        retained.append(hit)
        remaining -= len(separator) + len(kept)
        if len(kept) < len(section):
            break
    return "".join(parts), retained


class S1SingleLLM:
    """Single provider call with read-before-call, commit-after-outcome memory."""

    SYSTEM_ID = S1_SYSTEM_ID
    PROMPT_VERSION = S1_PROMPT_VERSION

    def __init__(
        self,
        provider: LLMProvider,
        *,
        memory: SharedMemory | None = None,
        memory_top_k: int = 5,
        memory_max_context_chars: int = 4000,
        temperature: float = 0.0,
        max_output_tokens: int = 1024,
        provider_timeout_seconds: float | None = None,
        seed: int | None = None,
    ) -> None:
        if not 1 <= memory_top_k <= MAX_MEMORY_TOP_K:
            raise ValueError(f"memory_top_k must be in [1, {MAX_MEMORY_TOP_K}]")
        if not 1 <= memory_max_context_chars <= MAX_MEMORY_CONTEXT_CHARS:
            raise ValueError(
                "memory_max_context_chars must be in "
                f"[1, {MAX_MEMORY_CONTEXT_CHARS}]"
            )
        self.provider = provider
        self.memory = memory if memory is not None else InMemoryKeywordMemory()
        self.memory_top_k = memory_top_k
        self.memory_max_context_chars = memory_max_context_chars
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.provider_timeout_seconds = float(
            provider_timeout_seconds
            if provider_timeout_seconds is not None
            else getattr(provider, "timeout_seconds", 30.0)
        )
        self.seed = seed

    def run_episode(self, episode_input: EpisodeInput) -> EpisodeResult:
        """Read committed memory and propose, but never publish, one write."""
        task = _extract_task(episode_input.input)
        hits = self.memory.search(task, self.memory_top_k)
        context, retained_hits = _bounded_context(
            hits, self.memory_max_context_chars
        )
        rendered_context = context or "(no relevant committed memory)"
        pending_events: list[dict[str, Any]] = [
            {
                "kind": "memory_retrieval",
                "payload": {
                    "backend": self.memory.backend_id,
                    "memory_reads": 1,
                    "memory_hits": len(retained_hits),
                    "retrieved_memory_ids": [hit.item_id for hit in retained_hits],
                    "retrieved_memory_chars": len(context),
                    "scores": [
                        {
                            "item_id": hit.item_id,
                            "kind": hit.kind,
                            "score": hit.score,
                        }
                        for hit in retained_hits
                    ],
                },
            }
        ]

        def sink(kind: str, payload: dict[str, Any]) -> None:
            pending_events.append({"kind": kind, "payload": dict(payload)})

        request = LLMRequest(
            model=getattr(self.provider, "model", "unknown"),
            messages=[
                LLMMessage(role="system", content=S1_SYSTEM_PROMPT_V0_1),
                LLMMessage(
                    role="user",
                    content=S1_USER_TEMPLATE_V0_1.format(
                        task=task, memory_context=rendered_context
                    ),
                ),
            ],
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
            timeout_seconds=self.provider_timeout_seconds,
            seed=self.seed,
        )
        base_metadata: dict[str, Any] = {
            "system_id": S1_SYSTEM_ID,
            "provider": getattr(self.provider, "name", "unknown"),
            "model": request.model,
            "prompt_version": S1_PROMPT_VERSION,
            "prompt_sha256": S1_PROMPT_SHA256,
            "temperature": self.temperature,
            "max_output_tokens": self.max_output_tokens,
            "provider_timeout_seconds": self.provider_timeout_seconds,
            "seed": self.seed,
            "logical_model_calls": 1,
            "memory_llm_calls": 0,
            "memory_reads": 1,
            "memory_hits": len(retained_hits),
            "memory_writes_committed": 0,
            "retrieved_memory_ids": [hit.item_id for hit in retained_hits],
            "retrieved_memory_chars": len(context),
            "retrieval_evidence": [
                {"item_id": hit.item_id, "kind": hit.kind, "score": hit.score}
                for hit in retained_hits
            ],
            "memory_backend": self.memory.backend_id,
            "memory_top_k": self.memory_top_k,
            "memory_max_context_chars": self.memory_max_context_chars,
            _PENDING_EVENTS_KEY: pending_events,
        }

        try:
            response = self.provider.generate(request, event_sink=sink)
        except ProviderError as exc:
            return EpisodeResult(
                output=None,
                status="FAILED",
                error=f"{exc.kind.value}: {exc.message}",
                metadata={
                    **base_metadata,
                    "provider_error_kind": exc.kind.value,
                    "transport_retries": exc.transport_retries,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "usage_available": False,
                    "provider_latency_ms": 0,
                },
            )

        return EpisodeResult(
            output={"answer": response.content},
            status="SUCCEEDED",
            tool_events=[],
            metadata={
                **base_metadata,
                _PENDING_WRITE_KEY: {
                    "task_family": episode_input.task_family,
                    "task": task,
                    "answer": response.content,
                },
                "finish_reason": response.finish_reason,
                "provider_request_id": response.provider_request_id,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "total_tokens": response.total_tokens,
                "usage_available": response.usage_available,
                "provider_latency_ms": response.latency_ms,
                "transport_retries": response.transport_retries,
            },
        )

    def finalize_episode_outcome(
        self,
        episode_input: EpisodeInput,
        result: EpisodeResult,
        outcome: str,
        event_log: EventLog,
    ) -> EpisodeResult:
        """Publish exactly one proposal only for an accepted COMPLETED outcome.

        ``EpisodeRunner`` is the sole caller.  A timed-out worker's late return
        is discarded by the runner, so this method is never reached for it.
        This baseline-local publication hook is not the future ABY Commit
        Barrier architecture.
        """
        metadata = dict(result.metadata)
        pending_events = metadata.pop(_PENDING_EVENTS_KEY, [])
        proposal = metadata.pop(_PENDING_WRITE_KEY, None)
        for pending in pending_events:
            event_log.append(
                Event(
                    episode_id=episode_input.episode_id,
                    kind=str(pending["kind"]),
                    payload=dict(pending.get("payload", {})),
                )
            )

        metadata["memory_writes_committed"] = 0
        if outcome == "COMPLETED" and result.status == "SUCCEEDED":
            if not isinstance(proposal, Mapping):
                raise ValueError("completed S1 episode is missing its memory proposal")
            item = self.memory.store_episode(episode_input.episode_id, proposal)
            metadata["memory_writes_committed"] = 1
            metadata["committed_memory_id"] = item.item_id
            event_log.append(
                Event(
                    episode_id=episode_input.episode_id,
                    kind="memory_commit",
                    payload={
                        "backend": self.memory.backend_id,
                        "memory_writes_committed": 1,
                        "committed_memory_id": item.item_id,
                    },
                )
            )
        result.metadata = metadata
        return result


def validate_s1_config(config: ExperimentConfig) -> dict[str, dict[str, Any]]:
    """Normalize S1 provider and memory settings with zero I/O."""
    try:
        provider = validate_s0_provider_config(config)
    except ValueError as exc:
        raise ValueError(str(exc).replace("S0", "S1")) from exc

    raw_memory = (config.metadata or {}).get("memory")
    if raw_memory is None:
        raw_memory = {
            "backend": MEMORY_BACKEND_ID,
            "top_k": 5,
            "max_context_chars": 4000,
        }
    if not isinstance(raw_memory, dict):
        raise ValueError("S1 config metadata.memory must be an object")
    unknown = set(raw_memory) - {"backend", "top_k", "max_context_chars"}
    if unknown:
        raise ValueError(f"unknown S1 memory fields: {sorted(unknown)}")
    backend = raw_memory.get("backend", MEMORY_BACKEND_ID)
    if backend != MEMORY_BACKEND_ID:
        raise ValueError(
            f"unknown S1 memory backend {backend!r} (expected {MEMORY_BACKEND_ID!r})"
        )
    top_k = raw_memory.get("top_k", 5)
    if (
        isinstance(top_k, bool)
        or not isinstance(top_k, int)
        or not 1 <= top_k <= MAX_MEMORY_TOP_K
    ):
        raise ValueError(f"S1 memory top_k must be an integer in [1, {MAX_MEMORY_TOP_K}]")
    max_chars = raw_memory.get("max_context_chars", 4000)
    if (
        isinstance(max_chars, bool)
        or not isinstance(max_chars, int)
        or not 1 <= max_chars <= MAX_MEMORY_CONTEXT_CHARS
    ):
        raise ValueError(
            "S1 memory max_context_chars must be an integer in "
            f"[1, {MAX_MEMORY_CONTEXT_CHARS}]"
        )
    return {
        "provider": provider,
        "memory": {
            "backend": backend,
            "top_k": top_k,
            "max_context_chars": max_chars,
        },
    }


def build_s1(
    config: ExperimentConfig, *, memory: SharedMemory | None = None
) -> S1SingleLLM:
    """Build S1 with a fresh memory store unless one is explicitly injected."""
    spec = validate_s1_config(config)
    provider_spec = spec["provider"]
    if provider_spec["type"] == "fake":
        provider: LLMProvider = FakeProvider(model=provider_spec["model"])
    else:
        provider = OpenAICompatProvider(
            base_url=provider_spec["base_url"],
            model=provider_spec["model"],
            api_key_env=provider_spec["api_key_env"],
            timeout_seconds=provider_spec["timeout_seconds"],
            temperature=provider_spec["temperature"],
            max_output_tokens=provider_spec["max_output_tokens"],
            seed=provider_spec["seed"],
            max_retries=provider_spec["max_retries"],
        )
    memory_spec = spec["memory"]
    return S1SingleLLM(
        provider,
        memory=memory if memory is not None else InMemoryKeywordMemory(),
        memory_top_k=memory_spec["top_k"],
        memory_max_context_chars=memory_spec["max_context_chars"],
        temperature=provider_spec["temperature"],
        max_output_tokens=provider_spec["max_output_tokens"],
        provider_timeout_seconds=provider_spec["timeout_seconds"],
        seed=provider_spec["seed"],
    )


def s1_requires_missing_credential(config: ExperimentConfig) -> str | None:
    """Return the required unset env-var name without exposing a credential."""
    import os

    provider = validate_s1_config(config)["provider"]
    if provider["type"] != "openai_compat":
        return None
    env_name = provider["api_key_env"]
    return env_name if not os.environ.get(env_name) else None


__all__ = [
    "S1_SYSTEM_ID",
    "S1_PROMPT_VERSION",
    "S1_SYSTEM_PROMPT_V0_1",
    "S1_USER_TEMPLATE_V0_1",
    "S1_PROMPT_SHA256",
    "S1SingleLLM",
    "validate_s1_config",
    "build_s1",
    "s1_requires_missing_credential",
]
