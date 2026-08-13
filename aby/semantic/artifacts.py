"""Deterministic, contained evidence export for P1.5 semantic geometry."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from ..experiments.config import validate_safe_identifier
from .bundle import SemanticGeometryBundle

SEMANTIC_ARTIFACT_FILENAMES = (
    "semantic_atoms.jsonl",
    "semantic_points.json",
    "semantic_atlas.json",
    "semantic_matches.json",
    "semantic_geometry_manifest.json",
)


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def semantic_geometry_artifact_dir(
    artifacts_root: str | Path, artifact_id: str
) -> Path:
    validate_safe_identifier(artifact_id, field="artifact_id")
    base = (Path(artifacts_root) / "semantic_geometry").resolve()
    directory = (base / artifact_id).resolve()
    if not directory.is_relative_to(base):
        raise ValueError(f"artifact path {directory} escapes the artifact root {base}")
    return directory


class SemanticArtifactSet(BaseModel):
    """Serializable artifact evidence; path is returned separately by the writer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    bundle_fingerprint: str
    artifact_file_sha256: dict[str, str]


def write_semantic_geometry_artifacts(
    artifacts_root: str | Path,
    *,
    artifact_id: str,
    bundle: SemanticGeometryBundle,
) -> tuple[Path, SemanticArtifactSet]:
    directory = semantic_geometry_artifact_dir(artifacts_root, artifact_id)
    directory.mkdir(parents=True, exist_ok=True)

    atoms_bytes = b"".join(
        _canonical_bytes(atom.model_dump(mode="json"))
        for atom in sorted(bundle.atoms, key=lambda item: item.atom_id)
    )
    payloads = {
        "semantic_atoms.jsonl": atoms_bytes,
        "semantic_points.json": _canonical_bytes(
            {
                "points": [
                    point.model_dump(mode="json")
                    for point in sorted(bundle.points, key=lambda item: item.atom_id)
                ]
            }
        ),
        "semantic_atlas.json": _canonical_bytes(
            {
                "atlas_version": bundle.atlas_version,
                "metric_version": bundle.metric_version,
                "k": bundle.k,
                "edges": [edge.model_dump(mode="json") for edge in bundle.edges],
            }
        ),
        "semantic_matches.json": _canonical_bytes(
            {"matches": [match.model_dump(mode="json") for match in bundle.matches]}
        ),
    }
    hashes = {
        filename: hashlib.sha256(content).hexdigest()
        for filename, content in sorted(payloads.items())
    }
    manifest = {
        "bundle_schema_version": bundle.bundle_schema_version,
        "atom_schema_version": bundle.atom_schema_version,
        "encoder": bundle.encoder.model_dump(mode="json"),
        "metric_version": bundle.metric_version,
        "atlas_version": bundle.atlas_version,
        "k": bundle.k,
        "bundle_fingerprint": bundle.bundle_fingerprint,
        "artifact_file_sha256": hashes,
    }
    payloads["semantic_geometry_manifest.json"] = _canonical_bytes(manifest)
    for filename in SEMANTIC_ARTIFACT_FILENAMES:
        (directory / filename).write_bytes(payloads[filename])
    return directory, SemanticArtifactSet(
        bundle_fingerprint=bundle.bundle_fingerprint,
        artifact_file_sha256=hashes,
    )


__all__ = [
    "SEMANTIC_ARTIFACT_FILENAMES",
    "SemanticArtifactSet",
    "semantic_geometry_artifact_dir",
    "write_semantic_geometry_artifacts",
]
