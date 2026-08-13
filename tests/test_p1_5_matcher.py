import math

import pytest

from aby.semantic.fixture import build_reference_fixture_bundle, reference_frames
from aby.semantic.atomizer import FrameAtomizer
from aby.semantic.encoder import DeterministicHashingEncoder
from aby.semantic.geometry import SemanticPoint, encode_semantic_atoms
from aby.semantic.atlas import build_directed_knn_atlas
from aby.semantic.ir import SemanticAtom, SemanticAtomType, SourceLane
from aby.semantic.matcher import (
    SEMANTIC_MATCHER_VERSION,
    SemanticMatchCandidate,
    match_cross_lane_candidates,
)


def _inputs():
    atoms = FrameAtomizer().atomize(*reference_frames())
    points = encode_semantic_atoms(atoms, DeterministicHashingEncoder(32))
    return atoms, build_directed_knn_atlas(points, k=3)


def test_matcher_is_cross_lane_bounded_stable_and_candidate_only():
    atoms, atlas = _inputs()
    first = match_cross_lane_candidates(atoms, atlas, per_source_limit=2)
    second = match_cross_lane_candidates(tuple(reversed(atoms)), atlas, per_source_limit=2)
    assert first == second
    assert first
    assert all(match.source_lane != match.target_lane for match in first)
    assert {(match.source_lane, match.target_lane) for match in first} == {
        (SourceLane.A, SourceLane.B),
        (SourceLane.A, SourceLane.Y),
        (SourceLane.B, SourceLane.Y),
    }
    assert all(1 <= match.rank <= 2 for match in first)
    assert all(match.forward_knn or match.reverse_knn for match in first)
    assert all(
        match.mutual_knn == (match.forward_knn and match.reverse_knn)
        for match in first
    )
    assert "equivalence" not in SemanticMatchCandidate.model_fields
    assert any(match.mutual_nearest for match in first)
    assert any(match.mutual_knn for match in first)


def test_matcher_result_count_is_bounded_per_canonical_source_lane():
    atoms, atlas = _inputs()
    matches = match_cross_lane_candidates(atoms, atlas, per_source_limit=1)
    expected_max = (
        sum(atom.source_lane == SourceLane.A for atom in atoms) * 2
        + sum(atom.source_lane == SourceLane.B for atom in atoms)
    )
    assert len(matches) <= expected_max


@pytest.mark.parametrize("limit", [0, 17, True])
def test_matcher_limit_is_bounded(limit):
    atoms, atlas = _inputs()
    with pytest.raises(ValueError):
        match_cross_lane_candidates(atoms, atlas, per_source_limit=limit)


def _locality_regression_inputs():
    def atom(label, lane, index):
        return SemanticAtom.create(
            atom_type=(
                SemanticAtomType.FACT if lane is SourceLane.A else SemanticAtomType.ACTION
            ),
            content=label,
            source_lane=lane,
            source_field="locality_fixture",
            source_index=index,
            confidence=1.0,
        )

    labeled_atoms = {
        "a_source": atom("a-source", SourceLane.A, 0),
        "a_peer": atom("a-peer", SourceLane.A, 1),
        "b_global_near": atom("b-global-near", SourceLane.B, 0),
        "b_peer": atom("b-peer", SourceLane.B, 1),
        "b_reverse_only": atom("b-reverse-only", SourceLane.B, 2),
    }
    angles = {
        "a_source": 0.0,
        "a_peer": 0.005,
        "b_global_near": 0.02,
        "b_peer": 0.021,
        "b_reverse_only": -0.03,
    }
    points = [
        SemanticPoint(
            atom_id=labeled_atoms[label].atom_id,
            encoder_id="locality-fixture",
            encoder_revision="r1",
            algorithm_fingerprint="c" * 64,
            dimension=2,
            vector=(math.cos(angle), math.sin(angle)),
        )
        for label, angle in angles.items()
    ]
    atlas = build_directed_knn_atlas(points, k=1)
    return tuple(labeled_atoms.values()), atlas, labeled_atoms


def test_matcher_has_no_global_fallback_and_accepts_reverse_only_locality():
    atoms, atlas, labeled = _locality_regression_inputs()
    matches = match_cross_lane_candidates(atoms, atlas, per_source_limit=2)
    pairs = {(match.source_atom_id, match.target_atom_id): match for match in matches}
    source_id = labeled["a_source"].atom_id
    globally_near_id = labeled["b_global_near"].atom_id
    reverse_only_id = labeled["b_reverse_only"].atom_id

    # b_global_near is the closest B point to a_source, but both endpoints have
    # closer same-lane peers; with no atlas edge in either direction it is ineligible.
    assert (source_id, globally_near_id) not in pairs
    reverse_only = pairs[(source_id, reverse_only_id)]
    assert reverse_only.forward_knn is False
    assert reverse_only.reverse_knn is True
    assert reverse_only.mutual_knn is False
    assert reverse_only.rank == 1
    assert all(match.forward_knn or match.reverse_knn for match in matches)
    # a_peer has no cross-lane atlas relation and therefore gets no fallback match.
    assert not any(
        match.source_atom_id == labeled["a_peer"].atom_id for match in matches
    )


def test_matcher_version_and_locality_evidence_are_explicit():
    assert SEMANTIC_MATCHER_VERSION == "atlas-local-cross-lane-v0.1"
    assert {"forward_knn", "reverse_knn", "mutual_knn"} <= set(
        SemanticMatchCandidate.model_fields
    )


def test_fixture_bundle_contains_match_candidates_without_future_geometry_fields():
    bundle = build_reference_fixture_bundle()
    edge_fields = set(type(bundle.edges[0]).model_fields)
    assert edge_fields == {"source_atom_id", "target_atom_id", "base_distance", "neighbor_rank"}
    assert not edge_fields & {"y_penalty", "dissipation_cost", "geodesic_path", "resolver_decision"}
