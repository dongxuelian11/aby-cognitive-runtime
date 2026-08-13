"""Versioned P1.5 semantic intermediate representation.

This module adapts frozen P0 frame content into auditable P1 atoms.  It is an
implementation hypothesis, not P0 authority or evidence of semantic quality.
"""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SEMANTIC_ATOM_SCHEMA_VERSION = "p1.5-v0.1"


class SemanticAtomType(str, Enum):
    GOAL = "GOAL"
    CONSTRAINT = "CONSTRAINT"
    FACT = "FACT"
    CLAIM = "CLAIM"
    ENTITY = "ENTITY"
    RELATION = "RELATION"
    INTENT = "INTENT"
    ACTION = "ACTION"
    EVIDENCE = "EVIDENCE"
    UNCERTAINTY = "UNCERTAINTY"


class SourceLane(str, Enum):
    """Semantic provenance only; never the measured lowercase a/b/y state."""

    A = "A"
    B = "B"
    Y = "Y"
    EXTERNAL = "EXTERNAL"


def semantic_atom_id(
    *,
    atom_type: SemanticAtomType,
    content: str,
    source_lane: SourceLane,
    source_field: str,
    source_index: int,
    evidence_refs: tuple[str, ...] = (),
) -> str:
    """Return a stable identity bound to semantic content and provenance."""
    identity = {
        "schema_version": SEMANTIC_ATOM_SCHEMA_VERSION,
        "atom_type": atom_type.value,
        "content": content,
        "source_lane": source_lane.value,
        "source_field": source_field,
        "source_index": source_index,
        "evidence_refs": list(evidence_refs),
    }
    raw = json.dumps(
        identity,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return f"atom-{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"


class SemanticAtom(BaseModel):
    """One immutable, source-bound P1 semantic unit."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    atom_id: str
    schema_version: Literal["p1.5-v0.1"] = SEMANTIC_ATOM_SCHEMA_VERSION
    atom_type: SemanticAtomType
    content: str
    source_lane: SourceLane
    source_field: str
    source_index: int = Field(ge=0)
    evidence_refs: tuple[str, ...] = ()
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("content", "source_field")
    @classmethod
    def _non_blank_text(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("semantic content and source fields must be non-blank")
        return value.strip()

    @field_validator("evidence_refs")
    @classmethod
    def _non_blank_evidence_refs(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        refs = tuple(ref.strip() for ref in value)
        if any(not ref for ref in refs):
            raise ValueError("evidence references must be non-blank")
        return refs

    @model_validator(mode="after")
    def _identity_must_match_payload(self) -> "SemanticAtom":
        expected = semantic_atom_id(
            atom_type=self.atom_type,
            content=self.content,
            source_lane=self.source_lane,
            source_field=self.source_field,
            source_index=self.source_index,
            evidence_refs=self.evidence_refs,
        )
        if self.atom_id != expected:
            raise ValueError("atom_id does not match canonical semantic/provenance input")
        return self

    @classmethod
    def create(
        cls,
        *,
        atom_type: SemanticAtomType,
        content: str,
        source_lane: SourceLane,
        source_field: str,
        source_index: int,
        evidence_refs: tuple[str, ...] = (),
        confidence: float,
    ) -> "SemanticAtom":
        normalized_content = content.strip() if isinstance(content, str) else content
        normalized_field = source_field.strip() if isinstance(source_field, str) else source_field
        normalized_refs = tuple(
            ref.strip() if isinstance(ref, str) else ref for ref in evidence_refs
        )
        atom_id = semantic_atom_id(
            atom_type=atom_type,
            content=normalized_content,
            source_lane=source_lane,
            source_field=normalized_field,
            source_index=source_index,
            evidence_refs=normalized_refs,
        )
        return cls(
            atom_id=atom_id,
            atom_type=atom_type,
            content=normalized_content,
            source_lane=source_lane,
            source_field=normalized_field,
            source_index=source_index,
            evidence_refs=normalized_refs,
            confidence=confidence,
        )


__all__ = [
    "SEMANTIC_ATOM_SCHEMA_VERSION",
    "SemanticAtomType",
    "SourceLane",
    "SemanticAtom",
    "semantic_atom_id",
]
