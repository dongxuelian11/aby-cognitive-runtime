import math

import pytest

from aby.semantic.atlas import build_directed_knn_atlas
from aby.semantic.geometry import SemanticPoint


def _point(atom_id, angle):
    return SemanticPoint(
        atom_id=atom_id,
        encoder_id="test-encoder",
        encoder_revision="r1",
        algorithm_fingerprint="b" * 64,
        dimension=2,
        vector=(math.cos(angle), math.sin(angle)),
    )


def test_directed_knn_has_no_self_edges_stable_order_and_stable_ties():
    points = [_point("atom-c", math.pi), _point("atom-a", 0.0), _point("atom-b", math.pi / 2)]
    atlas = build_directed_knn_atlas(points, k=1)
    replay = build_directed_knn_atlas(list(reversed(points)), k=1)
    assert atlas == replay
    assert [point.atom_id for point in atlas.points] == ["atom-a", "atom-b", "atom-c"]
    assert all(edge.source_atom_id != edge.target_atom_id for edge in atlas.edges)
    assert all(edge.neighbor_rank == 1 for edge in atlas.edges)
    # atom-b is equidistant from atom-a and atom-c; target atom ID breaks the tie.
    edge_b = next(edge for edge in atlas.edges if edge.source_atom_id == "atom-b")
    assert edge_b.target_atom_id == "atom-a"


def test_local_knn_can_be_asymmetric():
    atlas = build_directed_knn_atlas(
        [_point("atom-a", 0.0), _point("atom-b", 0.1), _point("atom-c", 0.3)],
        k=1,
    )
    pairs = {(edge.source_atom_id, edge.target_atom_id) for edge in atlas.edges}
    assert ("atom-c", "atom-b") in pairs
    assert ("atom-b", "atom-c") not in pairs


@pytest.mark.parametrize("k", [0, 3, 65, True])
def test_atlas_k_is_bounded_and_no_larger_than_n_minus_one(k):
    points = [_point("atom-a", 0.0), _point("atom-b", 0.1), _point("atom-c", 0.3)]
    with pytest.raises((TypeError, ValueError)):
        build_directed_knn_atlas(points, k=k)


def test_atlas_rejects_mixed_encoder_provenance():
    first = _point("atom-a", 0.0)
    second = _point("atom-b", 0.2).model_copy(update={"encoder_revision": "r2"})
    with pytest.raises(ValueError, match="provenance"):
        build_directed_knn_atlas([first, second], k=1)
