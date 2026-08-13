import pytest
from pydantic import ValidationError

from aby.runtime.snapshot import (
    RUNTIME_SNAPSHOT_SCHEMA_VERSION,
    RuntimeSnapshot,
    project_snapshot,
)
from tests.p1_6_support import sample_snapshot


def test_snapshot_is_versioned_deeply_immutable_and_content_addressed():
    snapshot = sample_snapshot()
    assert snapshot.snapshot_schema_version == RUNTIME_SNAPSHOT_SCHEMA_VERSION == "p1.6-v0.1"
    assert isinstance(snapshot.accepted_facts, tuple)
    with pytest.raises(ValidationError):
        snapshot.current_task = "mutated"
    with pytest.raises(ValidationError):
        snapshot.accepted_facts += ("mutated",)
    with pytest.raises(ValidationError, match="snapshot_id"):
        RuntimeSnapshot(**snapshot.model_dump() | {"snapshot_id": "0" * 64})


def test_snapshot_id_is_deterministic_and_changes_with_any_lane_input():
    first = sample_snapshot()
    second = sample_snapshot()
    changed = sample_snapshot(local_context=("different accepted local context",))
    assert first == second
    assert first.snapshot_id == second.snapshot_id
    assert first.canonical_json() == second.canonical_json()
    assert changed.snapshot_id != first.snapshot_id


def test_all_lane_projections_bind_same_snapshot_but_preserve_role_purity():
    snapshot = sample_snapshot(relevant_history=("full-history-sentinel",))
    projections = {lane: project_snapshot(snapshot, lane) for lane in ("A", "B", "Y")}
    assert {view.snapshot_id for view in projections.values()} == {snapshot.snapshot_id}
    assert {view.snapshot_schema_version for view in projections.values()} == {"p1.6-v0.1"}
    a_names = {section.name for section in projections["A"].sections}
    b_names = {section.name for section in projections["B"].sections}
    y_names = {section.name for section in projections["Y"].sections}
    assert "relevant_history" in a_names and "relevant_history" in y_names
    assert "relevant_history" not in b_names
    assert "available_tools" in b_names and "available_tools" not in a_names
    assert "full-history-sentinel" not in projections["B"].canonical_json()
