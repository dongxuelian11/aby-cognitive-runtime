import pytest

from aby.semantic.fixture import build_reference_fixture_bundle, reference_frames
from aby.semantic.atomizer import FrameAtomizer
from aby.semantic.encoder import DeterministicHashingEncoder
from aby.semantic.geometry import encode_semantic_atoms
from aby.semantic.atlas import build_directed_knn_atlas
from aby.semantic.ir import SourceLane
from aby.semantic.matcher import SemanticMatchCandidate, match_cross_lane_candidates


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


def test_fixture_bundle_contains_match_candidates_without_future_geometry_fields():
    bundle = build_reference_fixture_bundle()
    edge_fields = set(type(bundle.edges[0]).model_fields)
    assert edge_fields == {"source_atom_id", "target_atom_id", "base_distance", "neighbor_rank"}
    assert not edge_fields & {"y_penalty", "dissipation_cost", "geodesic_path", "resolver_decision"}
