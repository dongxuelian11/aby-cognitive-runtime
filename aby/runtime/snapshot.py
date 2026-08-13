"""Versioned immutable accepted-snapshot boundary for P1.6 A/B/Y lanes."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ._canonical import canonical_json, canonical_sha256

RUNTIME_SNAPSHOT_SCHEMA_VERSION = "p1.6-v0.1"


class RuntimeSnapshot(BaseModel):
    """One deeply immutable accepted input shared by all three live lanes."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshot_schema_version: Literal["p1.6-v0.1"] = RUNTIME_SNAPSHOT_SCHEMA_VERSION
    snapshot_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    episode_id: str = Field(min_length=1)
    current_event: str = Field(min_length=1)
    current_task: str = Field(min_length=1)
    accepted_facts: tuple[str, ...] = ()
    selected_evidence: tuple[str, ...] = ()
    active_constraints: tuple[str, ...] = ()
    long_term_goals: tuple[str, ...] = ()
    relevant_history: tuple[str, ...] = ()
    local_context: tuple[str, ...] = ()
    available_tools: tuple[str, ...] = ()

    def identity_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"snapshot_id"})

    def canonical_json(self) -> str:
        return canonical_json(self.model_dump(mode="json"))

    @model_validator(mode="after")
    def _identity_must_match_content(self) -> "RuntimeSnapshot":
        expected = canonical_sha256(self.identity_payload())
        if self.snapshot_id != expected:
            raise ValueError("snapshot_id does not match canonical accepted content")
        return self

    @classmethod
    def create(
        cls,
        *,
        episode_id: str,
        current_event: str,
        current_task: str,
        accepted_facts: tuple[str, ...] = (),
        selected_evidence: tuple[str, ...] = (),
        active_constraints: tuple[str, ...] = (),
        long_term_goals: tuple[str, ...] = (),
        relevant_history: tuple[str, ...] = (),
        local_context: tuple[str, ...] = (),
        available_tools: tuple[str, ...] = (),
    ) -> "RuntimeSnapshot":
        payload = {
            "snapshot_schema_version": RUNTIME_SNAPSHOT_SCHEMA_VERSION,
            "episode_id": episode_id,
            "current_event": current_event,
            "current_task": current_task,
            "accepted_facts": accepted_facts,
            "selected_evidence": selected_evidence,
            "active_constraints": active_constraints,
            "long_term_goals": long_term_goals,
            "relevant_history": relevant_history,
            "local_context": local_context,
            "available_tools": available_tools,
        }
        return cls(**payload, snapshot_id=canonical_sha256(payload))


class SnapshotSection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    values: tuple[str, ...]


class LaneSnapshotProjection(BaseModel):
    """Deterministic, role-bounded view derived from one RuntimeSnapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    lane: Literal["A", "B", "Y"]
    snapshot_schema_version: Literal["p1.6-v0.1"]
    snapshot_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    episode_id: str
    current_event: str
    current_task: str
    sections: tuple[SnapshotSection, ...]

    def canonical_json(self) -> str:
        return canonical_json(self.model_dump(mode="json"))


_PROJECTION_FIELDS: dict[str, tuple[str, ...]] = {
    "A": (
        "accepted_facts",
        "selected_evidence",
        "active_constraints",
        "long_term_goals",
        "relevant_history",
    ),
    "B": (
        "active_constraints",
        "local_context",
        "selected_evidence",
        "available_tools",
    ),
    "Y": (
        "accepted_facts",
        "selected_evidence",
        "active_constraints",
        "long_term_goals",
        "relevant_history",
        "local_context",
    ),
}


def project_snapshot(
    snapshot: RuntimeSnapshot, lane: Literal["A", "B", "Y"]
) -> LaneSnapshotProjection:
    return LaneSnapshotProjection(
        lane=lane,
        snapshot_schema_version=snapshot.snapshot_schema_version,
        snapshot_id=snapshot.snapshot_id,
        episode_id=snapshot.episode_id,
        current_event=snapshot.current_event,
        current_task=snapshot.current_task,
        sections=tuple(
            SnapshotSection(name=name, values=getattr(snapshot, name))
            for name in _PROJECTION_FIELDS[lane]
        ),
    )


__all__ = [
    "RUNTIME_SNAPSHOT_SCHEMA_VERSION",
    "RuntimeSnapshot",
    "SnapshotSection",
    "LaneSnapshotProjection",
    "project_snapshot",
]
