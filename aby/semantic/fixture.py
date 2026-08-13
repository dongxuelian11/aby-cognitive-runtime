"""Meaningful deterministic offline P1.5 fixture; never semantic-quality evidence."""

from __future__ import annotations

from ..contracts.frames import ActionFrame, DissipationFrame, MacroFrame
from .bundle import SemanticGeometryBundle, build_semantic_geometry_bundle
from .encoder import DeterministicHashingEncoder

REFERENCE_FIXTURE_ENCODER_DIMENSION = 32
REFERENCE_FIXTURE_ATLAS_K = 3


def reference_frames() -> tuple[MacroFrame, ActionFrame, DissipationFrame]:
    return (
        MacroFrame(
            macro_state=["The experiment must remain reproducible and auditable."],
            relevant_history=["P0 frames are accepted and frozen."],
            active_constraints=["Do not modify frozen P0 contracts."],
            long_term_goals=["Build a falsifiable semantic geometry substrate."],
            continuity_risks=["A provider-specific embedding could break replayability."],
            candidate_interpretations=["A shared external encoder can coordinate lane evidence."],
            confidence=0.9,
            evidence_refs=["docs/p0/freeze", "docs/authority/p1-hypothesis"],
        ),
        ActionFrame(
            current_intent="Construct the bounded offline semantic geometry bundle.",
            local_plan=["Atomize frames", "Normalize encoded semantic points"],
            candidate_actions=["Build a directed local kNN atlas"],
            tool_requests=["Write deterministic geometry artifacts"],
            expected_result="Repeated runs produce byte-identical evidence.",
            local_uncertainties=["Reference hashing does not establish semantic quality."],
            confidence=0.85,
            evidence_refs=["task:p1.5"],
        ),
        DissipationFrame(
            conflicts=["A whole-output embedding would violate the atomization boundary."],
            uncertainties=["Local proximity is only a match candidate, not equivalence."],
            goal_drift=["Adding a geodesic resolver would exceed P1.5."],
            memory_mismatch=["No accepted evidence supports Y edge penalties yet."],
            factual_mismatch=[],
            redundancy=[],
            rework_risk=["Unstable ordering would invalidate artifact replay."],
            context_drift=[],
            unresolved_tension=["Semantic quality remains experimentally unvalidated."],
            estimated_y=0.25,
            confidence=0.75,
            recommended_resolution_targets=["Preserve the P1.5-only boundary."],
        ),
    )


def build_reference_fixture_bundle() -> SemanticGeometryBundle:
    macro, action, dissipation = reference_frames()
    return build_semantic_geometry_bundle(
        macro,
        action,
        dissipation,
        encoder=DeterministicHashingEncoder(
            dimension=REFERENCE_FIXTURE_ENCODER_DIMENSION
        ),
        k=REFERENCE_FIXTURE_ATLAS_K,
        matches_per_source=2,
    )


__all__ = [
    "REFERENCE_FIXTURE_ENCODER_DIMENSION",
    "REFERENCE_FIXTURE_ATLAS_K",
    "reference_frames",
    "build_reference_fixture_bundle",
]
