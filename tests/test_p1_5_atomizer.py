import socket

import pytest

from aby.contracts.frames import ActionFrame, DissipationFrame, MacroFrame
from aby.semantic.atomizer import FrameAtomizer
from aby.semantic.ir import SemanticAtomType, SourceLane


def test_explicit_frame_field_mapping_preserves_provenance_and_confidence(monkeypatch):
    def forbidden_network(*args, **kwargs):
        raise AssertionError("atomizer attempted network access")

    monkeypatch.setattr(socket, "create_connection", forbidden_network)
    macro = MacroFrame(
        macro_state=["fact"], relevant_history=["history"],
        active_constraints=["constraint"], long_term_goals=["goal"],
        continuity_risks=["risk"], candidate_interpretations=["claim"],
        confidence=0.8, evidence_refs=["a-ref"],
    )
    action = ActionFrame(
        current_intent="intent", local_plan=["plan"],
        candidate_actions=["candidate"], tool_requests=["tool"],
        expected_result="result", local_uncertainties=["uncertain"],
        confidence=0.7, evidence_refs=["b-ref"],
    )
    dissipation = DissipationFrame(
        conflicts=["conflict"], uncertainties=["uncertain-y"],
        goal_drift=["drift"], memory_mismatch=["memory"],
        factual_mismatch=["factual"], redundancy=["redundant"],
        rework_risk=["rework"], context_drift=["context"],
        unresolved_tension=["tension"], estimated_y=0.9, confidence=0.6,
        recommended_resolution_targets=["target"],
    )
    atoms = FrameAtomizer().atomize(macro, action, dissipation)
    by_key = {(atom.source_lane, atom.source_field): atom for atom in atoms}

    assert by_key[(SourceLane.A, "long_term_goals")].atom_type is SemanticAtomType.GOAL
    assert by_key[(SourceLane.A, "macro_state")].atom_type is SemanticAtomType.FACT
    assert by_key[(SourceLane.A, "relevant_history")].atom_type is SemanticAtomType.EVIDENCE
    assert by_key[(SourceLane.B, "current_intent")].atom_type is SemanticAtomType.INTENT
    assert by_key[(SourceLane.B, "tool_requests")].atom_type is SemanticAtomType.ACTION
    assert by_key[(SourceLane.Y, "conflicts")].atom_type is SemanticAtomType.CLAIM
    assert by_key[(SourceLane.Y, "goal_drift")].atom_type is SemanticAtomType.UNCERTAINTY
    assert by_key[(SourceLane.Y, "recommended_resolution_targets")].atom_type is SemanticAtomType.INTENT
    assert by_key[(SourceLane.A, "macro_state")].evidence_refs == ("a-ref",)
    assert by_key[(SourceLane.B, "local_plan")].evidence_refs == ("b-ref",)
    assert by_key[(SourceLane.Y, "conflicts")].evidence_refs == ()
    assert by_key[(SourceLane.A, "macro_state")].confidence == 0.8
    assert by_key[(SourceLane.Y, "conflicts")].confidence == 0.6
    assert "estimated_y" not in {atom.source_field for atom in atoms}
    assert not hasattr(FrameAtomizer(), "provider")


def test_atomizer_preserves_duplicate_source_positions():
    atoms = FrameAtomizer().atomize_macro(
        MacroFrame(macro_state=["same", "same"])
    )
    assert [atom.source_index for atom in atoms] == [0, 1]
    assert atoms[0].atom_id != atoms[1].atom_id


def test_atomizer_rejects_blank_list_entries_but_allows_absent_scalar_fields():
    with pytest.raises(ValueError, match=r"A\.macro_state\[0\]"):
        FrameAtomizer().atomize_macro(MacroFrame(macro_state=[" "]))
    assert FrameAtomizer().atomize_action(ActionFrame()) == []
