"""Pure-Python normalized spherical base geometry for P1.5."""

from __future__ import annotations

import math
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .encoder import SharedEncoder
from .ir import SemanticAtom

SPHERICAL_METRIC_VERSION = "spherical-arccos-v0.1"
_UNIT_TOLERANCE = 1e-12


def _validated_vector(vector: Sequence[float], *, name: str) -> tuple[float, ...]:
    if not vector:
        raise ValueError(f"{name} must not be empty")
    values = tuple(float(value) for value in vector)
    if not all(math.isfinite(value) for value in values):
        raise ValueError(f"{name} must contain finite values only")
    return values


def normalize_vector(vector: Sequence[float]) -> tuple[float, ...]:
    values = _validated_vector(vector, name="vector")
    norm = math.sqrt(math.fsum(value * value for value in values))
    if not math.isfinite(norm) or norm <= 0.0:
        raise ValueError("vector must have a finite, non-zero L2 norm")
    normalized = tuple(value / norm for value in values)
    if not all(math.isfinite(value) for value in normalized):
        raise ValueError("normalized vector contains non-finite values")
    return normalized


def dot_product(left: Sequence[float], right: Sequence[float]) -> float:
    left_values = _validated_vector(left, name="left vector")
    right_values = _validated_vector(right, name="right vector")
    if len(left_values) != len(right_values):
        raise ValueError("vector dimensions must match")
    result = math.fsum(a * b for a, b in zip(left_values, right_values, strict=True))
    if not math.isfinite(result):
        raise ValueError("dot product is non-finite")
    return result


def _require_normalized(vector: Sequence[float], *, name: str) -> tuple[float, ...]:
    values = _validated_vector(vector, name=name)
    norm_squared = math.fsum(value * value for value in values)
    if not math.isclose(norm_squared, 1.0, rel_tol=0.0, abs_tol=_UNIT_TOLERANCE):
        raise ValueError(f"{name} must be L2-normalized")
    return values


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    left_values = _require_normalized(left, name="left vector")
    right_values = _require_normalized(right, name="right vector")
    return max(-1.0, min(1.0, dot_product(left_values, right_values)))


def spherical_distance(left: Sequence[float], right: Sequence[float]) -> float:
    """arccos(clamp(dot, -1, 1)); this is base geometry, never Y cost."""
    return math.acos(cosine_similarity(left, right))


class SemanticPoint(BaseModel):
    """One normalized point bound to atom and encoder provenance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    atom_id: str = Field(min_length=1)
    encoder_id: str = Field(min_length=1)
    encoder_revision: str = Field(min_length=1)
    algorithm_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    dimension: int = Field(ge=1)
    vector: tuple[float, ...]

    @field_validator("vector")
    @classmethod
    def _finite_vector(cls, value: tuple[float, ...]) -> tuple[float, ...]:
        return _validated_vector(value, name="semantic point vector")

    @model_validator(mode="after")
    def _dimension_and_norm_must_match(self) -> "SemanticPoint":
        if len(self.vector) != self.dimension:
            raise ValueError("semantic point dimension does not match vector length")
        _require_normalized(self.vector, name="semantic point vector")
        return self


def encode_semantic_atoms(
    atoms: Sequence[SemanticAtom], encoder: SharedEncoder
) -> tuple[SemanticPoint, ...]:
    provenance = encoder.provenance
    raw_vectors = encoder.encode([atom.content for atom in atoms])
    if len(raw_vectors) != len(atoms):
        raise ValueError("encoder returned a vector count different from input count")
    points: list[SemanticPoint] = []
    for atom, raw_vector in zip(atoms, raw_vectors, strict=True):
        if len(raw_vector) != provenance.dimension:
            raise ValueError("encoder vector dimension differs from declared dimension")
        points.append(
            SemanticPoint(
                atom_id=atom.atom_id,
                encoder_id=provenance.encoder_id,
                encoder_revision=provenance.encoder_revision,
                algorithm_fingerprint=provenance.algorithm_fingerprint,
                dimension=provenance.dimension,
                vector=normalize_vector(raw_vector),
            )
        )
    return tuple(points)


__all__ = [
    "SPHERICAL_METRIC_VERSION",
    "SemanticPoint",
    "normalize_vector",
    "dot_product",
    "cosine_similarity",
    "spherical_distance",
    "encode_semantic_atoms",
]
