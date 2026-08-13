"""Deterministic directed local kNN semantic atlas."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .geometry import SPHERICAL_METRIC_VERSION, SemanticPoint, spherical_distance

SEMANTIC_ATLAS_VERSION = "directed-local-knn-v0.1"
MAX_ATLAS_K = 64


class SemanticAtlasEdge(BaseModel):
    """Base spherical neighbor evidence; deliberately contains no Y penalty."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_atom_id: str = Field(min_length=1)
    target_atom_id: str = Field(min_length=1)
    base_distance: float = Field(ge=0.0, le=3.141592653589793)
    neighbor_rank: int = Field(ge=1)

    @model_validator(mode="after")
    def _not_self_edge(self) -> "SemanticAtlasEdge":
        if self.source_atom_id == self.target_atom_id:
            raise ValueError("semantic atlas self edges are forbidden")
        return self


class SemanticAtlas(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    atlas_version: Literal["directed-local-knn-v0.1"] = SEMANTIC_ATLAS_VERSION
    metric_version: Literal["spherical-arccos-v0.1"] = SPHERICAL_METRIC_VERSION
    k: int = Field(ge=1, le=MAX_ATLAS_K)
    points: tuple[SemanticPoint, ...]
    edges: tuple[SemanticAtlasEdge, ...]


def build_directed_knn_atlas(
    points: Sequence[SemanticPoint], *, k: int
) -> SemanticAtlas:
    if not isinstance(k, int) or isinstance(k, bool):
        raise TypeError("k must be an integer")
    if k < 1 or k > MAX_ATLAS_K:
        raise ValueError(f"k must be in [1, {MAX_ATLAS_K}]")
    ordered = tuple(sorted(points, key=lambda point: point.atom_id))
    if len(ordered) < 2:
        raise ValueError("at least two semantic points are required")
    if k > len(ordered) - 1:
        raise ValueError("k must not exceed n - 1")
    ids = [point.atom_id for point in ordered]
    if len(set(ids)) != len(ids):
        raise ValueError("semantic point atom IDs must be unique")
    provenance = {
        (
            point.encoder_id,
            point.encoder_revision,
            point.algorithm_fingerprint,
            point.dimension,
        )
        for point in ordered
    }
    if len(provenance) != 1:
        raise ValueError("all atlas points must share encoder provenance and dimension")

    edges: list[SemanticAtlasEdge] = []
    for source in ordered:
        candidates = [
            (spherical_distance(source.vector, target.vector), target.atom_id)
            for target in ordered
            if target.atom_id != source.atom_id
        ]
        candidates.sort(key=lambda item: (item[0], item[1]))
        for rank, (distance, target_id) in enumerate(candidates[:k], start=1):
            edges.append(
                SemanticAtlasEdge(
                    source_atom_id=source.atom_id,
                    target_atom_id=target_id,
                    base_distance=distance,
                    neighbor_rank=rank,
                )
            )
    return SemanticAtlas(k=k, points=ordered, edges=tuple(edges))


__all__ = [
    "SEMANTIC_ATLAS_VERSION",
    "MAX_ATLAS_K",
    "SemanticAtlasEdge",
    "SemanticAtlas",
    "build_directed_knn_atlas",
]
