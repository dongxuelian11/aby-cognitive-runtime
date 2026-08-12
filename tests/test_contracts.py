"""Contract-level tests for the P0 V0.1 freeze.

These tests verify the freeze itself (schemas, decision set, measurement
model, replayability). They do not test lane/resolver implementation — none
exists yet, by design (P0 §16).
"""

import pytest
from pydantic import ValidationError

from aby.contracts import (
    DissipationFrame,
    MacroFrame,
    ResolveDecision,
    ResolveDecisionKind,
    SCHEMA_VERSION,
    TelemetryRecord,
)


def test_macro_frame_defaults_are_empty_lists():
    m = MacroFrame()
    assert m.macro_state == []
    assert m.relevant_history == []
    assert m.active_constraints == []
    assert m.long_term_goals == []
    assert m.continuity_risks == []
    assert m.candidate_interpretations == []
    assert m.evidence_refs == []
    assert m.confidence == 0.0


def test_frame_confidence_is_bounded():
    with pytest.raises(ValidationError):
        MacroFrame(confidence=1.5)
    with pytest.raises(ValidationError):
        DissipationFrame(confidence=-0.1)


def test_dissipation_frame_y_is_bounded():
    # y in [0,1] follows from a + b + y = 1 (P0 §2.1)
    with pytest.raises(ValidationError):
        DissipationFrame(estimated_y=2.0)
    frame = DissipationFrame(estimated_y=0.3)
    assert frame.estimated_y == 0.3


def test_resolver_allowed_decisions_are_frozen():
    # P0 §6.4 — any change requires a new P0 version
    assert {k.value for k in ResolveDecisionKind} == {
        "EXECUTE_B",
        "REQUEST_EVIDENCE",
        "REQUEST_A_REFRESH",
        "REQUEST_B_REPLAN",
        "DEFER",
        "RETURN_UNCERTAINTY",
    }


def test_resolve_decision_roundtrip():
    decision = ResolveDecision(decision=ResolveDecisionKind.EXECUTE_B)
    restored = ResolveDecision.model_validate_json(decision.model_dump_json())
    assert restored.decision is ResolveDecisionKind.EXECUTE_B


def test_telemetry_record_schema_constant():
    trace = TelemetryRecord(episode_id="e1")
    raw = trace.model_dump_json()
    assert SCHEMA_VERSION == "ABY_RUNTIME_TELEMETRY_V0.1"
    assert "ABY_RUNTIME_TELEMETRY_V0.1" in raw
    assert "episode_id" in raw
    # Frozen JSON field names must survive pydantic aliasing (P0 §8)
    for frozen_key in ("schema", "model_config", "memory_config", "user_quality_score"):
        assert f'"{frozen_key}"' in raw, f"frozen key {frozen_key} missing from trace JSON"
    # qA/qB/qY are recorded but NOT required to sum to 1 at the record level
    # (allocation is reported, not enforced, in the frozen schema).
    assert trace.qA == 0.0 and trace.qB == 0.0 and trace.qY == 0.0
