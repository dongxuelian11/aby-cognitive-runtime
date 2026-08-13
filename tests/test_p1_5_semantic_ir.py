import pytest

from aby.semantic.ir import (
    SEMANTIC_ATOM_SCHEMA_VERSION,
    SemanticAtom,
    SemanticAtomType,
    SourceLane,
)


def _atom(**overrides):
    values = {
        "atom_type": SemanticAtomType.GOAL,
        "content": "Preserve reproducibility",
        "source_lane": SourceLane.A,
        "source_field": "long_term_goals",
        "source_index": 0,
        "evidence_refs": ("evidence:1",),
        "confidence": 0.8,
    }
    values.update(overrides)
    return SemanticAtom.create(**values)


def test_required_atom_types_and_source_lanes_are_explicit():
    assert {item.value for item in SemanticAtomType} >= {
        "GOAL", "CONSTRAINT", "FACT", "CLAIM", "ENTITY", "RELATION",
        "INTENT", "ACTION", "EVIDENCE", "UNCERTAINTY",
    }
    assert {item.value for item in SourceLane} == {"A", "B", "Y", "EXTERNAL"}
    assert SEMANTIC_ATOM_SCHEMA_VERSION == "p1.5-v0.1"


def test_atom_rejects_blank_content_and_invalid_confidence():
    with pytest.raises(ValueError):
        _atom(content="  ")
    with pytest.raises(ValueError):
        _atom(confidence=1.1)


def test_atom_identity_is_stable_and_source_or_content_changes_it():
    first = _atom()
    second = _atom()
    assert first.atom_id == second.atom_id
    assert _atom(content="Preserve auditability").atom_id != first.atom_id
    assert _atom(source_lane=SourceLane.B).atom_id != first.atom_id
    assert _atom(source_field="active_constraints").atom_id != first.atom_id


def test_duplicate_source_positions_retain_distinct_provenance():
    first = _atom(content="duplicate", source_index=0)
    second = _atom(content="duplicate", source_index=1)
    assert first.atom_id != second.atom_id
    assert (first.source_index, second.source_index) == (0, 1)


def test_atom_round_trip_and_tamper_rejection():
    atom = _atom()
    restored = SemanticAtom.model_validate_json(atom.model_dump_json())
    assert restored == atom
    tampered = atom.model_dump()
    tampered["atom_id"] = "atom-" + "0" * 64
    with pytest.raises(ValueError, match="atom_id"):
        SemanticAtom.model_validate(tampered)
