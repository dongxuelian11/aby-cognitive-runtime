import math

import pytest

from aby.semantic.encoder import (
    REFERENCE_ENCODER_ID,
    REFERENCE_ENCODER_REVISION,
    REFERENCE_ENCODER_STATUS,
    DeterministicHashingEncoder,
    SharedEncoder,
)


def test_reference_encoder_is_deterministic_fixed_dimension_and_finite():
    first = DeterministicHashingEncoder(dimension=32)
    second = DeterministicHashingEncoder(dimension=32)
    texts = ["shared semantic atom", "bounded local atlas"]
    assert first.encode(texts) == second.encode(texts)
    assert all(len(vector) == 32 for vector in first.encode(texts))
    assert all(math.isfinite(value) for vector in first.encode(texts) for value in vector)
    assert first.encode(["alpha"]) != first.encode(["beta"])
    assert isinstance(first, SharedEncoder)


def test_reference_identity_and_scientific_boundary_are_explicit():
    encoder = DeterministicHashingEncoder(dimension=32)
    assert encoder.encoder_id == REFERENCE_ENCODER_ID == "reference_hashing"
    assert encoder.encoder_revision == REFERENCE_ENCODER_REVISION == "p1.5-v0.1"
    assert encoder.scientific_status == REFERENCE_ENCODER_STATUS
    assert REFERENCE_ENCODER_STATUS == "REFERENCE_ONLY_NOT_SEMANTIC_QUALITY_EVIDENCE"
    assert encoder.provenance.dimension == 32
    assert len(encoder.provenance.algorithm_fingerprint) == 64
    assert encoder.provenance == DeterministicHashingEncoder(32).provenance
    assert encoder.provenance != DeterministicHashingEncoder(64).provenance


@pytest.mark.parametrize("text", ["", "  ", "!!!"])
def test_reference_encoder_rejects_unencodable_content(text):
    with pytest.raises(ValueError):
        DeterministicHashingEncoder().encode([text])


@pytest.mark.parametrize("dimension", [0, 7, 4097, 8.5, True])
def test_reference_encoder_dimension_is_bounded(dimension):
    with pytest.raises((TypeError, ValueError)):
        DeterministicHashingEncoder(dimension=dimension)
