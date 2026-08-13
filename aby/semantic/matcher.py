"""Bounded local cross-lane correspondence candidates over the shared atlas."""

from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .atlas import SemanticAtlas
from .geometry import spherical_distance
from .ir import SemanticAtom, SourceLane

LANE_PAIRS = (
    (SourceLane.A, SourceLane.B),
    (SourceLane.A, SourceLane.Y),
    (SourceLane.B, SourceLane.Y),
)
MAX_MATCHES_PER_SOURCE = 16
SEMANTIC_MATCHER_VERSION = "atlas-local-cross-lane-v0.1"


class SemanticMatchCandidate(BaseModel):
    """Distance evidence for a candidate correspondence, never equivalence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_atom_id: str = Field(min_length=1)
    target_atom_id: str = Field(min_length=1)
    source_lane: SourceLane
    target_lane: SourceLane
    distance: float = Field(ge=0.0, le=3.141592653589793)
    rank: int = Field(ge=1)
    mutual_nearest: bool
    forward_knn: bool
    reverse_knn: bool
    mutual_knn: bool

    @model_validator(mode="after")
    def _must_be_cross_lane(self) -> "SemanticMatchCandidate":
        if self.source_lane == self.target_lane:
            raise ValueError("semantic match candidates must be cross-lane")
        if not (self.forward_knn or self.reverse_knn):
            raise ValueError("semantic match candidates require atlas-local adjacency")
        if self.mutual_knn != (self.forward_knn and self.reverse_knn):
            raise ValueError("mutual_knn must equal forward_knn AND reverse_knn")
        return self


def match_cross_lane_candidates(
    atoms: Sequence[SemanticAtom],
    atlas: SemanticAtlas,
    *,
    per_source_limit: int = 2,
) -> tuple[SemanticMatchCandidate, ...]:
    if (
        not isinstance(per_source_limit, int)
        or isinstance(per_source_limit, bool)
        or per_source_limit < 1
        or per_source_limit > MAX_MATCHES_PER_SOURCE
    ):
        raise ValueError(
            f"per_source_limit must be an integer in [1, {MAX_MATCHES_PER_SOURCE}]"
        )
    atom_by_id = {atom.atom_id: atom for atom in atoms}
    if len(atom_by_id) != len(atoms):
        raise ValueError("atom IDs must be unique")
    point_by_id = {point.atom_id: point for point in atlas.points}
    if set(atom_by_id) != set(point_by_id):
        raise ValueError("atoms and atlas points must have identical atom IDs")
    knn_edges = {
        (edge.source_atom_id, edge.target_atom_id) for edge in atlas.edges
    }

    def local_relation(source_id: str, target_id: str) -> tuple[bool, bool]:
        return (
            (source_id, target_id) in knn_edges,
            (target_id, source_id) in knn_edges,
        )

    def eligible_ranked(
        source_id: str, target_ids: Sequence[str]
    ) -> list[tuple[float, str, bool, bool]]:
        source = point_by_id[source_id]
        result: list[tuple[float, str, bool, bool]] = []
        for target_id in target_ids:
            forward_knn, reverse_knn = local_relation(source_id, target_id)
            if not (forward_knn or reverse_knn):
                continue
            result.append(
                (
                    spherical_distance(source.vector, point_by_id[target_id].vector),
                    target_id,
                    forward_knn,
                    reverse_knn,
                )
            )
        result.sort(key=lambda item: (item[0], item[1]))
        return result

    matches: list[SemanticMatchCandidate] = []
    for source_lane, target_lane in LANE_PAIRS:
        source_ids = sorted(
            atom.atom_id for atom in atoms if atom.source_lane == source_lane
        )
        target_ids = sorted(
            atom.atom_id for atom in atoms if atom.source_lane == target_lane
        )
        if not source_ids or not target_ids:
            continue
        reverse_nearest: dict[str, str] = {}
        for target_id in target_ids:
            eligible_sources = [
                (
                    spherical_distance(
                        point_by_id[target_id].vector,
                        point_by_id[source_id].vector,
                    ),
                    source_id,
                )
                for source_id in source_ids
                if any(local_relation(source_id, target_id))
            ]
            eligible_sources.sort(key=lambda item: (item[0], item[1]))
            if eligible_sources:
                reverse_nearest[target_id] = eligible_sources[0][1]
        for source_id in source_ids:
            for rank, (distance, target_id, forward_knn, reverse_knn) in enumerate(
                eligible_ranked(source_id, target_ids)[:per_source_limit], start=1
            ):
                matches.append(
                    SemanticMatchCandidate(
                        source_atom_id=source_id,
                        target_atom_id=target_id,
                        source_lane=source_lane,
                        target_lane=target_lane,
                        distance=distance,
                        rank=rank,
                        mutual_nearest=(
                            rank == 1 and reverse_nearest.get(target_id) == source_id
                        ),
                        forward_knn=forward_knn,
                        reverse_knn=reverse_knn,
                        mutual_knn=(forward_knn and reverse_knn),
                    )
                )
    return tuple(
        sorted(
            matches,
            key=lambda match: (
                match.source_lane.value,
                match.target_lane.value,
                match.source_atom_id,
                match.rank,
                match.target_atom_id,
            ),
        )
    )


__all__ = [
    "LANE_PAIRS",
    "MAX_MATCHES_PER_SOURCE",
    "SEMANTIC_MATCHER_VERSION",
    "SemanticMatchCandidate",
    "match_cross_lane_candidates",
]
