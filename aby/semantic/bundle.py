"""High-level deterministic P1.5 semantic geometry pipeline and bundle."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..contracts.frames import ActionFrame, DissipationFrame, MacroFrame
from .atlas import (
    SEMANTIC_ATLAS_VERSION,
    SemanticAtlasEdge,
    build_directed_knn_atlas,
)
from .atomizer import FrameAtomizer
from .encoder import EncoderProvenance, SharedEncoder
from .geometry import SPHERICAL_METRIC_VERSION, SemanticPoint, encode_semantic_atoms
from .ir import SEMANTIC_ATOM_SCHEMA_VERSION, SemanticAtom
from .matcher import SemanticMatchCandidate, match_cross_lane_candidates

SEMANTIC_GEOMETRY_BUNDLE_SCHEMA_VERSION = "p1.5-semantic-geometry-bundle-v0.1"


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


class SemanticGeometryBundle(BaseModel):
    """Serializable evidence only; contains no provider, LLM, or runtime object."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    bundle_schema_version: Literal[
        "p1.5-semantic-geometry-bundle-v0.1"
    ] = SEMANTIC_GEOMETRY_BUNDLE_SCHEMA_VERSION
    atom_schema_version: Literal["p1.5-v0.1"] = SEMANTIC_ATOM_SCHEMA_VERSION
    encoder: EncoderProvenance
    metric_version: Literal["spherical-arccos-v0.1"] = SPHERICAL_METRIC_VERSION
    atlas_version: Literal["directed-local-knn-v0.1"] = SEMANTIC_ATLAS_VERSION
    k: int = Field(ge=1)
    atoms: tuple[SemanticAtom, ...]
    points: tuple[SemanticPoint, ...]
    edges: tuple[SemanticAtlasEdge, ...]
    matches: tuple[SemanticMatchCandidate, ...]
    bundle_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    def fingerprint_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"bundle_fingerprint"})

    def canonical_json(self) -> str:
        return _canonical_json(self.model_dump(mode="json"))

    @model_validator(mode="after")
    def _fingerprint_must_match(self) -> "SemanticGeometryBundle":
        expected = hashlib.sha256(
            _canonical_json(self.fingerprint_payload()).encode("utf-8")
        ).hexdigest()
        if self.bundle_fingerprint != expected:
            raise ValueError("bundle_fingerprint does not match canonical bundle content")
        return self


def build_semantic_geometry_bundle(
    macro: MacroFrame,
    action: ActionFrame,
    dissipation: DissipationFrame,
    *,
    encoder: SharedEncoder,
    k: int = 3,
    matches_per_source: int = 2,
    atomizer: FrameAtomizer | None = None,
) -> SemanticGeometryBundle:
    atoms = (atomizer or FrameAtomizer()).atomize(macro, action, dissipation)
    if len(atoms) < 2:
        raise ValueError("semantic geometry bundle requires at least two atoms")
    points = encode_semantic_atoms(atoms, encoder)
    atlas = build_directed_knn_atlas(points, k=k)
    matches = match_cross_lane_candidates(
        atoms, atlas, per_source_limit=matches_per_source
    )
    payload = {
        "bundle_schema_version": SEMANTIC_GEOMETRY_BUNDLE_SCHEMA_VERSION,
        "atom_schema_version": SEMANTIC_ATOM_SCHEMA_VERSION,
        "encoder": encoder.provenance.model_dump(mode="json"),
        "metric_version": SPHERICAL_METRIC_VERSION,
        "atlas_version": SEMANTIC_ATLAS_VERSION,
        "k": k,
        "atoms": [atom.model_dump(mode="json") for atom in atoms],
        "points": [point.model_dump(mode="json") for point in points],
        "edges": [edge.model_dump(mode="json") for edge in atlas.edges],
        "matches": [match.model_dump(mode="json") for match in matches],
    }
    fingerprint = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return SemanticGeometryBundle(**payload, bundle_fingerprint=fingerprint)


__all__ = [
    "SEMANTIC_GEOMETRY_BUNDLE_SCHEMA_VERSION",
    "SemanticGeometryBundle",
    "build_semantic_geometry_bundle",
]
