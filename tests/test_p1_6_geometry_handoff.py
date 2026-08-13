import threading

from aby.semantic.bundle import build_semantic_geometry_bundle
from aby.semantic.encoder import DeterministicHashingEncoder, REFERENCE_ENCODER_STATUS
from aby.semantic.ir import SemanticAtomType, SourceLane
from aby.runtime.bundle import RuntimeStatus
from tests.p1_6_support import (
    build_runtime,
    runtime_config,
    runtime_providers,
    sample_snapshot,
)


def test_all_lane_success_hands_exact_frames_to_accepted_p1_5_geometry():
    encoder = DeterministicHashingEncoder(32)
    result = build_runtime(runtime_providers(), encoder=encoder).run(
        sample_snapshot(), runtime_config(geometry=True)
    )
    assert result.status is RuntimeStatus.SUCCEEDED
    bundle = result.semantic_geometry_bundle
    assert bundle is not None
    expected = build_semantic_geometry_bundle(
        result.a_lane.proposal.frame,
        result.b_lane.proposal.frame,
        result.y_lane.proposal.frame,
        encoder=DeterministicHashingEncoder(32),
        k=3,
        matches_per_source=2,
    )
    assert bundle == expected
    assert bundle.bundle_fingerprint == expected.bundle_fingerprint
    assert encoder.scientific_status == REFERENCE_ENCODER_STATUS
    assert bundle.metric_version == "spherical-arccos-v0.1"
    assert bundle.atlas_version == "directed-local-knn-v0.1"
    assert not any(
        atom.source_lane is SourceLane.Y
        and atom.atom_type in (SemanticAtomType.INTENT, SemanticAtomType.ACTION)
        for atom in bundle.atoms
    )
    assert not any(atom.source_field == "estimated_y" for atom in bundle.atoms)


def test_geometry_enabled_without_encoder_fails_closed_after_successful_lanes():
    result = build_runtime(runtime_providers()).run(
        sample_snapshot(), runtime_config(geometry=True)
    )
    assert result.status is RuntimeStatus.FAILED
    assert result.semantic_geometry_bundle is None
    assert result.coordinator_failure.error_category == "SEMANTIC_GEOMETRY_ENCODER_REQUIRED"


def _providers_for_completion_order(order):
    completed = {lane: threading.Event() for lane in order}
    overrides = {}
    for index, lane in enumerate(order):
        overrides[lane] = {
            "wait_for": completed[order[index - 1]] if index else None,
            "signal": completed[lane],
        }
    return runtime_providers(**overrides)


def test_different_completion_schedules_preserve_all_semantic_fingerprints():
    snapshot = sample_snapshot()
    evidence = []
    for order in (("A", "B", "Y"), ("B", "Y", "A"), ("Y", "A", "B")):
        result = build_runtime(
            _providers_for_completion_order(order),
            encoder=DeterministicHashingEncoder(32),
        ).run(snapshot, runtime_config(geometry=True))
        evidence.append(
            (
                result.a_lane.proposal.proposal_fingerprint,
                result.b_lane.proposal.proposal_fingerprint,
                result.y_lane.proposal.proposal_fingerprint,
                tuple((event.lane, event.local_ordinal, event.kind) for event in result.canonical_lane_events),
                result.runtime_semantic_fingerprint,
                result.semantic_geometry_bundle.bundle_fingerprint,
            )
        )
    assert evidence[0] == evidence[1] == evidence[2]
