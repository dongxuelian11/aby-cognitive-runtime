"""Deterministic, zero-LLM adapters from frozen P0 frames to P1 atoms."""

from __future__ import annotations

from collections.abc import Iterable

from ..contracts.frames import ActionFrame, DissipationFrame, MacroFrame
from .ir import SemanticAtom, SemanticAtomType, SourceLane


class FrameAtomizer:
    """Explicitly map frozen frame fields without reinterpreting P0 schemas."""

    MACRO_FIELDS = (
        ("macro_state", SemanticAtomType.FACT),
        ("relevant_history", SemanticAtomType.EVIDENCE),
        ("active_constraints", SemanticAtomType.CONSTRAINT),
        ("long_term_goals", SemanticAtomType.GOAL),
        ("continuity_risks", SemanticAtomType.UNCERTAINTY),
        ("candidate_interpretations", SemanticAtomType.CLAIM),
    )
    ACTION_LIST_FIELDS = (
        ("local_plan", SemanticAtomType.ACTION),
        ("candidate_actions", SemanticAtomType.ACTION),
        ("tool_requests", SemanticAtomType.ACTION),
        ("local_uncertainties", SemanticAtomType.UNCERTAINTY),
    )
    DISSIPATION_FIELDS = (
        ("conflicts", SemanticAtomType.CLAIM),
        ("uncertainties", SemanticAtomType.UNCERTAINTY),
        ("goal_drift", SemanticAtomType.UNCERTAINTY),
        ("memory_mismatch", SemanticAtomType.CLAIM),
        ("factual_mismatch", SemanticAtomType.CLAIM),
        ("redundancy", SemanticAtomType.UNCERTAINTY),
        ("rework_risk", SemanticAtomType.UNCERTAINTY),
        ("context_drift", SemanticAtomType.UNCERTAINTY),
        ("unresolved_tension", SemanticAtomType.UNCERTAINTY),
        ("recommended_resolution_targets", SemanticAtomType.INTENT),
    )

    @staticmethod
    def _from_values(
        values: Iterable[str],
        *,
        atom_type: SemanticAtomType,
        lane: SourceLane,
        source_field: str,
        evidence_refs: tuple[str, ...],
        confidence: float,
    ) -> list[SemanticAtom]:
        atoms: list[SemanticAtom] = []
        for index, content in enumerate(values):
            if not isinstance(content, str) or not content.strip():
                raise ValueError(
                    f"{lane.value}.{source_field}[{index}] contains blank/invalid semantic content"
                )
            atoms.append(
                SemanticAtom.create(
                    atom_type=atom_type,
                    content=content,
                    source_lane=lane,
                    source_field=source_field,
                    source_index=index,
                    evidence_refs=evidence_refs,
                    confidence=confidence,
                )
            )
        return atoms

    def atomize_macro(self, frame: MacroFrame) -> list[SemanticAtom]:
        refs = tuple(frame.evidence_refs)
        atoms: list[SemanticAtom] = []
        for field, atom_type in self.MACRO_FIELDS:
            atoms.extend(
                self._from_values(
                    getattr(frame, field),
                    atom_type=atom_type,
                    lane=SourceLane.A,
                    source_field=field,
                    evidence_refs=refs,
                    confidence=frame.confidence,
                )
            )
        return atoms

    def atomize_action(self, frame: ActionFrame) -> list[SemanticAtom]:
        refs = tuple(frame.evidence_refs)
        atoms: list[SemanticAtom] = []
        for field, atom_type in (
            ("current_intent", SemanticAtomType.INTENT),
            ("expected_result", SemanticAtomType.CLAIM),
        ):
            content = getattr(frame, field)
            if content:
                atoms.extend(
                    self._from_values(
                        (content,),
                        atom_type=atom_type,
                        lane=SourceLane.B,
                        source_field=field,
                        evidence_refs=refs,
                        confidence=frame.confidence,
                    )
                )
        for field, atom_type in self.ACTION_LIST_FIELDS:
            atoms.extend(
                self._from_values(
                    getattr(frame, field),
                    atom_type=atom_type,
                    lane=SourceLane.B,
                    source_field=field,
                    evidence_refs=refs,
                    confidence=frame.confidence,
                )
            )
        return atoms

    def atomize_dissipation(self, frame: DissipationFrame) -> list[SemanticAtom]:
        # estimated_y is deliberately not atomized and never becomes edge cost.
        atoms: list[SemanticAtom] = []
        for field, atom_type in self.DISSIPATION_FIELDS:
            atoms.extend(
                self._from_values(
                    getattr(frame, field),
                    atom_type=atom_type,
                    lane=SourceLane.Y,
                    source_field=field,
                    evidence_refs=(),
                    confidence=frame.confidence,
                )
            )
        return atoms

    def atomize(
        self,
        macro: MacroFrame,
        action: ActionFrame,
        dissipation: DissipationFrame,
    ) -> tuple[SemanticAtom, ...]:
        return tuple(
            self.atomize_macro(macro)
            + self.atomize_action(action)
            + self.atomize_dissipation(dissipation)
        )


__all__ = ["FrameAtomizer"]
