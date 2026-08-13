"""High-level deterministic P1.5 semantic geometry pipeline and bundle."""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..contracts.frames import ActionFrame, DissipationFrame, MacroFrame
from .atlas import (
    MAX_ATLAS_K,
    SEMANTIC_ATLAS_VERSION,
    SemanticAtlas,
    SemanticAtlasEdge,
    build_directed_knn_atlas,
)
from .atomizer import FRAME_ATOMIZER_VERSION, FrameAtomizer
from .encoder import EncoderProvenance, SharedEncoder
from .geometry import SPHERICAL_METRIC_VERSION, SemanticPoint, encode_semantic_atoms
from .ir import (
    SEMANTIC_ATOM_SCHEMA_VERSION,
    SemanticAtom,
    SemanticAtomType,
    SourceLane,
)
from .matcher import (
    MAX_MATCHES_PER_SOURCE,
    SEMANTIC_MATCHER_VERSION,
    SemanticMatchCandidate,
    match_cross_lane_candidates,
)

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
    atomizer_version: Literal["frame-atomizer-v0.1"] = FRAME_ATOMIZER_VERSION
    encoder: EncoderProvenance
    metric_version: Literal["spherical-arccos-v0.1"] = SPHERICAL_METRIC_VERSION
    atlas_version: Literal["directed-local-knn-v0.1"] = SEMANTIC_ATLAS_VERSION
    matcher_version: Literal[
        "atlas-local-cross-lane-v0.1"
    ] = SEMANTIC_MATCHER_VERSION
    k: int = Field(ge=1, le=MAX_ATLAS_K)
    matches_per_source: int = Field(ge=1, le=MAX_MATCHES_PER_SOURCE)
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
    def _integrity_and_fingerprint_must_match(self) -> "SemanticGeometryBundle":
        atom_by_id = {atom.atom_id: atom for atom in self.atoms}
        if len(atom_by_id) != len(self.atoms):
            raise ValueError("bundle atom IDs must be unique")
        point_by_id = {point.atom_id: point for point in self.points}
        if len(point_by_id) != len(self.points):
            raise ValueError("bundle point atom IDs must be unique")
        if set(point_by_id) != set(atom_by_id):
            raise ValueError("bundle atom and point ID sets must match exactly")
        if len(self.points) < 2 or self.k > len(self.points) - 1:
            raise ValueError("bundle k must not exceed point count minus one")

        expected_encoder = (
            self.encoder.encoder_id,
            self.encoder.encoder_revision,
            self.encoder.algorithm_fingerprint,
            self.encoder.dimension,
        )
        for point in self.points:
            point_encoder = (
                point.encoder_id,
                point.encoder_revision,
                point.algorithm_fingerprint,
                point.dimension,
            )
            if point_encoder != expected_encoder:
                raise ValueError("bundle point encoder provenance must match bundle encoder")

        for atom in self.atoms:
            if atom.source_lane == SourceLane.Y and atom.atom_type in (
                SemanticAtomType.INTENT,
                SemanticAtomType.ACTION,
            ):
                raise ValueError("bundle Y-origin atoms must not be INTENT/ACTION")
            if (
                atom.source_lane == SourceLane.Y
                and atom.source_field == "recommended_resolution_targets"
                and atom.atom_type != SemanticAtomType.DISSIPATION_TARGET
            ):
                raise ValueError(
                    "Y recommended_resolution_targets must be DISSIPATION_TARGET"
                )

        edge_pairs: set[tuple[str, str]] = set()
        ranks_by_source: dict[str, set[int]] = {}
        for edge in self.edges:
            if (
                edge.source_atom_id not in point_by_id
                or edge.target_atom_id not in point_by_id
            ):
                raise ValueError("bundle edge endpoints must reference known points")
            pair = (edge.source_atom_id, edge.target_atom_id)
            if pair in edge_pairs:
                raise ValueError("bundle edge source/target pairs must be unique")
            edge_pairs.add(pair)
            source_ranks = ranks_by_source.setdefault(edge.source_atom_id, set())
            if edge.neighbor_rank in source_ranks:
                raise ValueError("bundle neighbor ranks must be unique per source")
            source_ranks.add(edge.neighbor_rank)

        for match in self.matches:
            if (
                match.source_atom_id not in atom_by_id
                or match.target_atom_id not in atom_by_id
            ):
                raise ValueError("bundle match endpoints must reference known atoms")
            source_atom = atom_by_id[match.source_atom_id]
            target_atom = atom_by_id[match.target_atom_id]
            if (
                source_atom.source_lane != match.source_lane
                or target_atom.source_lane != match.target_lane
            ):
                raise ValueError("bundle match lanes must agree with endpoint atoms")
            actual_forward = (
                match.source_atom_id,
                match.target_atom_id,
            ) in edge_pairs
            actual_reverse = (
                match.target_atom_id,
                match.source_atom_id,
            ) in edge_pairs
            if not (actual_forward or actual_reverse):
                raise ValueError("bundle matches require actual atlas-local backing")
            if (
                match.forward_knn != actual_forward
                or match.reverse_knn != actual_reverse
                or match.mutual_knn != (actual_forward and actual_reverse)
            ):
                raise ValueError("bundle match locality flags must agree with atlas edges")

        expected_atlas = build_directed_knn_atlas(self.points, k=self.k)
        if self.edges != expected_atlas.edges:
            raise ValueError(
                "bundle edges must equal the canonical directed local kNN atlas"
            )
        atlas = SemanticAtlas(
            k=self.k,
            points=expected_atlas.points,
            edges=self.edges,
        )
        expected_matches = match_cross_lane_candidates(
            self.atoms,
            atlas,
            per_source_limit=self.matches_per_source,
        )
        if self.matches != expected_matches:
            raise ValueError(
                "bundle matches must equal canonical atlas-local matcher evidence"
            )

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
    atomizer_instance = atomizer or FrameAtomizer()
    if getattr(atomizer_instance, "version", None) != FRAME_ATOMIZER_VERSION:
        raise ValueError("unsupported or unversioned frame atomizer")
    atoms = atomizer_instance.atomize(macro, action, dissipation)
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
        "atomizer_version": FRAME_ATOMIZER_VERSION,
        "encoder": encoder.provenance.model_dump(mode="json"),
        "metric_version": SPHERICAL_METRIC_VERSION,
        "atlas_version": SEMANTIC_ATLAS_VERSION,
        "matcher_version": SEMANTIC_MATCHER_VERSION,
        "k": k,
        "matches_per_source": matches_per_source,
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
