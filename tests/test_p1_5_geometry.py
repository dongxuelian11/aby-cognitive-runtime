import math

import pytest

from aby.semantic.geometry import (
    SemanticPoint,
    cosine_similarity,
    dot_product,
    normalize_vector,
    spherical_distance,
)


def test_normalization_is_unit_length_and_dimension_preserving():
    vector = normalize_vector([3.0, 4.0])
    assert vector == (0.6, 0.8)
    assert math.isclose(dot_product(vector, vector), 1.0, abs_tol=1e-12)


@pytest.mark.parametrize("vector", [[0.0, 0.0], [math.nan, 1.0], [math.inf, 1.0]])
def test_normalization_rejects_zero_and_non_finite_vectors(vector):
    with pytest.raises(ValueError):
        normalize_vector(vector)


def test_spherical_distance_self_symmetry_range_and_orthogonal_value():
    x = normalize_vector([1.0, 0.0, 0.0])
    y = normalize_vector([0.0, 1.0, 0.0])
    z = normalize_vector([-1.0, 0.0, 0.0])
    assert spherical_distance(x, x) == pytest.approx(0.0, abs=1e-12)
    assert spherical_distance(x, y) == pytest.approx(math.pi / 2)
    assert spherical_distance(x, y) == spherical_distance(y, x)
    assert spherical_distance(x, z) == pytest.approx(math.pi)
    for distance in (spherical_distance(x, x), spherical_distance(x, y), spherical_distance(x, z)):
        assert 0.0 <= distance <= math.pi
    assert cosine_similarity(x, x) == 1.0


def test_vector_operations_fail_closed_on_dimension_or_normalization_mismatch():
    with pytest.raises(ValueError, match="dimensions"):
        dot_product([1.0], [1.0, 0.0])
    with pytest.raises(ValueError, match="normalized"):
        spherical_distance([2.0, 0.0], [1.0, 0.0])


def test_semantic_point_binds_dimension_normalization_and_encoder_provenance():
    point = SemanticPoint(
        atom_id="atom-a", encoder_id="encoder", encoder_revision="r1",
        algorithm_fingerprint="a" * 64, dimension=2, vector=(1.0, 0.0),
    )
    assert point.dimension == len(point.vector)
    with pytest.raises(ValueError, match="dimension"):
        SemanticPoint(
            atom_id="atom-a", encoder_id="encoder", encoder_revision="r1",
            algorithm_fingerprint="a" * 64, dimension=3, vector=(1.0, 0.0),
        )
    with pytest.raises(ValueError, match="normalized"):
        SemanticPoint(
            atom_id="atom-a", encoder_id="encoder", encoder_revision="r1",
            algorithm_fingerprint="a" * 64, dimension=2, vector=(0.5, 0.0),
        )
