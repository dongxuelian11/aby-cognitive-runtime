"""Frozen lane I/O contracts — ABY P0 V0.1.

Source: docs/p0/ABY_P0_THEORY_FREEZE_EXPERIMENTAL_ARCHITECTURE_V0_1.md

- MacroFrame        (P0 §5.1)
- ActionFrame       (P0 §5.2)
- DissipationFrame  (P0 §5.3)
- ResolveDecision   (P0 §6.3) + allowed decision kinds (P0 §6.4)

FROZEN: field names and top-level structure.
NOT FROZEN: element schemas inside the list fields (P0 shows `[]` only).
`list[str]` is a P1 working assumption and may evolve without a P0 version bump.
"""

from enum import Enum

from pydantic import BaseModel, Field


class MacroFrame(BaseModel):
    """A-Layer output contract (P0 §5.1)."""

    macro_state: list[str] = Field(default_factory=list)
    relevant_history: list[str] = Field(default_factory=list)
    active_constraints: list[str] = Field(default_factory=list)
    long_term_goals: list[str] = Field(default_factory=list)
    continuity_risks: list[str] = Field(default_factory=list)
    candidate_interpretations: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_refs: list[str] = Field(default_factory=list)


class ActionFrame(BaseModel):
    """B-Layer output contract (P0 §5.2)."""

    current_intent: str = ""
    local_plan: list[str] = Field(default_factory=list)
    candidate_actions: list[str] = Field(default_factory=list)
    tool_requests: list[str] = Field(default_factory=list)
    expected_result: str = ""
    local_uncertainties: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    evidence_refs: list[str] = Field(default_factory=list)


class DissipationFrame(BaseModel):
    """Y-Layer output contract (P0 §5.3). Y is not a third answer generator."""

    conflicts: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    goal_drift: list[str] = Field(default_factory=list)
    memory_mismatch: list[str] = Field(default_factory=list)
    factual_mismatch: list[str] = Field(default_factory=list)
    redundancy: list[str] = Field(default_factory=list)
    rework_risk: list[str] = Field(default_factory=list)
    context_drift: list[str] = Field(default_factory=list)
    unresolved_tension: list[str] = Field(default_factory=list)
    # y in [0, 1] follows from the normalized state a + b + y = 1 (P0 §2.1).
    estimated_y: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    recommended_resolution_targets: list[str] = Field(default_factory=list)


class ResolveDecisionKind(str, Enum):
    """Allowed Resolver decisions (P0 §6.4).

    Adding or renaming a kind requires a new P0 version (see CHANGELOG rules).
    """

    EXECUTE_B = "EXECUTE_B"
    REQUEST_EVIDENCE = "REQUEST_EVIDENCE"
    REQUEST_A_REFRESH = "REQUEST_A_REFRESH"
    REQUEST_B_REPLAN = "REQUEST_B_REPLAN"
    DEFER = "DEFER"
    RETURN_UNCERTAINTY = "RETURN_UNCERTAINTY"


class ResolveDecision(BaseModel):
    """Resolver output contract (P0 §6.3)."""

    decision: ResolveDecisionKind
    macro_constraints_applied: list[str] = Field(default_factory=list)
    unresolved_conflicts: list[str] = Field(default_factory=list)
    requires_more_evidence: bool = False
    requested_evidence: list[str] = Field(default_factory=list)
    memory_write_candidates: list[str] = Field(default_factory=list)
    reason_codes: list[str] = Field(default_factory=list)


__all__ = [
    "MacroFrame",
    "ActionFrame",
    "DissipationFrame",
    "ResolveDecisionKind",
    "ResolveDecision",
]
