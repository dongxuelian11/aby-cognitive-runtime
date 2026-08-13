import hashlib
import json
from copy import deepcopy

import pytest

from aby.semantic.artifacts import (
    SEMANTIC_ARTIFACT_FILENAMES,
    semantic_geometry_artifact_dir,
    write_semantic_geometry_artifacts,
)
from aby.semantic.atomizer import FRAME_ATOMIZER_VERSION
from aby.semantic.bundle import (
    SemanticGeometryBundle,
    build_semantic_geometry_bundle,
)
from aby.semantic.encoder import DeterministicHashingEncoder
from aby.semantic.fixture import build_reference_fixture_bundle, reference_frames
from aby.semantic.matcher import SEMANTIC_MATCHER_VERSION


def _recompute_bundle_fingerprint(payload):
    fingerprint_payload = {
        key: value for key, value in payload.items() if key != "bundle_fingerprint"
    }
    raw = json.dumps(
        fingerprint_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    payload["bundle_fingerprint"] = hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _assert_rehashed_bundle_rejected(mutator, error_match):
    bundle = build_reference_fixture_bundle()
    payload = deepcopy(bundle.model_dump(mode="json"))
    mutator(payload, bundle)
    _recompute_bundle_fingerprint(payload)
    assert payload["bundle_fingerprint"] != bundle.bundle_fingerprint
    with pytest.raises(ValueError, match=error_match):
        SemanticGeometryBundle.model_validate(payload)


def test_fresh_pipeline_instances_produce_same_bundle_and_fingerprint():
    first = build_reference_fixture_bundle()
    second = build_reference_fixture_bundle()
    assert first.bundle_fingerprint == second.bundle_fingerprint
    assert first.canonical_json() == second.canonical_json()
    assert SemanticGeometryBundle.model_validate_json(first.canonical_json()) == first


def test_artifacts_are_byte_stable_and_manifest_hashes_are_exact(tmp_path):
    first_bundle = build_reference_fixture_bundle()
    second_bundle = build_reference_fixture_bundle()
    first_dir, first_evidence = write_semantic_geometry_artifacts(
        tmp_path / "run-a", artifact_id="fixture", bundle=first_bundle
    )
    second_dir, second_evidence = write_semantic_geometry_artifacts(
        tmp_path / "run-b", artifact_id="fixture", bundle=second_bundle
    )
    assert first_evidence == second_evidence
    assert {path.name for path in first_dir.iterdir()} == set(SEMANTIC_ARTIFACT_FILENAMES)
    for filename in SEMANTIC_ARTIFACT_FILENAMES:
        assert (first_dir / filename).read_bytes() == (second_dir / filename).read_bytes()

    manifest = json.loads((first_dir / "semantic_geometry_manifest.json").read_text(encoding="utf-8"))
    assert manifest["bundle_fingerprint"] == first_bundle.bundle_fingerprint
    assert manifest["atomizer_version"] == first_bundle.atomizer_version
    assert manifest["matcher_version"] == first_bundle.matcher_version
    assert manifest["matches_per_source"] == first_bundle.matches_per_source
    for filename, expected_hash in manifest["artifact_file_sha256"].items():
        assert hashlib.sha256((first_dir / filename).read_bytes()).hexdigest() == expected_hash
    assert set(manifest["artifact_file_sha256"]) == {
        "semantic_atoms.jsonl", "semantic_points.json", "semantic_atlas.json", "semantic_matches.json"
    }


def test_artifacts_are_dedicated_secret_free_serializable_evidence(tmp_path):
    bundle = build_reference_fixture_bundle()
    directory, _ = write_semantic_geometry_artifacts(
        tmp_path, artifact_id="fixture", bundle=bundle
    )
    combined = b"".join((directory / name).read_bytes() for name in SEMANTIC_ARTIFACT_FILENAMES)
    lowered = combined.lower()
    for forbidden in (b"api_key", b"authorization", b"bearer ", b"llmprovider", b"openai"):
        assert forbidden not in lowered


@pytest.mark.parametrize("artifact_id", ["", ".", "..", "../escape", "a/b", "a\\b"])
def test_artifact_path_containment_rejects_unsafe_ids(tmp_path, artifact_id):
    with pytest.raises(ValueError):
        semantic_geometry_artifact_dir(tmp_path, artifact_id)


def test_artifact_directory_resolves_beneath_semantic_root(tmp_path):
    directory = semantic_geometry_artifact_dir(tmp_path, "fixture-1.0")
    assert directory.is_relative_to((tmp_path / "semantic_geometry").resolve())


def test_bundle_and_manifest_bind_transform_provenance_and_match_limit(tmp_path):
    frames = reference_frames()
    one = build_semantic_geometry_bundle(
        *frames, encoder=DeterministicHashingEncoder(32), k=3, matches_per_source=1
    )
    two = build_semantic_geometry_bundle(
        *frames, encoder=DeterministicHashingEncoder(32), k=3, matches_per_source=2
    )
    assert one.atomizer_version == FRAME_ATOMIZER_VERSION == "frame-atomizer-v0.1"
    assert one.matcher_version == SEMANTIC_MATCHER_VERSION == "atlas-local-cross-lane-v0.1"
    assert (one.matches_per_source, two.matches_per_source) == (1, 2)
    assert one.bundle_fingerprint != two.bundle_fingerprint

    directory, _ = write_semantic_geometry_artifacts(
        tmp_path, artifact_id="provenance", bundle=two
    )
    manifest = json.loads(
        (directory / "semantic_geometry_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["atomizer_version"] == FRAME_ATOMIZER_VERSION
    assert manifest["matcher_version"] == SEMANTIC_MATCHER_VERSION
    assert manifest["matches_per_source"] == 2


def test_bundle_rejects_rehashed_unknown_point_atom_id():
    def mutate(payload, _bundle):
        payload["points"][0]["atom_id"] = "atom-" + "0" * 64

    _assert_rehashed_bundle_rejected(mutate, "atom and point ID sets")


def test_bundle_rejects_rehashed_unknown_edge_endpoint():
    def mutate(payload, _bundle):
        payload["edges"][0]["target_atom_id"] = "atom-" + "0" * 64

    _assert_rehashed_bundle_rejected(mutate, "edge endpoints")


def test_bundle_rejects_rehashed_duplicate_edge_pair():
    def mutate(payload, _bundle):
        payload["edges"][1] = deepcopy(payload["edges"][0])

    _assert_rehashed_bundle_rejected(mutate, "edge source/target pairs")


def test_bundle_rejects_rehashed_match_lane_disagreement():
    def mutate(payload, _bundle):
        payload["matches"][0]["source_lane"] = "EXTERNAL"

    _assert_rehashed_bundle_rejected(mutate, "match lanes")


def test_bundle_rejects_rehashed_match_without_local_atlas_backing():
    def mutate(payload, _bundle):
        edge_pairs = {
            (edge["source_atom_id"], edge["target_atom_id"])
            for edge in payload["edges"]
        }
        atoms_by_lane = {}
        for atom in payload["atoms"]:
            atoms_by_lane.setdefault(atom["source_lane"], []).append(atom["atom_id"])
        for match in payload["matches"]:
            for target_id in atoms_by_lane[match["target_lane"]]:
                pair = (match["source_atom_id"], target_id)
                reverse = (target_id, match["source_atom_id"])
                if pair not in edge_pairs and reverse not in edge_pairs:
                    match["target_atom_id"] = target_id
                    match["forward_knn"] = True
                    match["reverse_knn"] = False
                    match["mutual_knn"] = False
                    match["mutual_nearest"] = False
                    return
        raise AssertionError("fixture must contain a non-local cross-lane pair")

    _assert_rehashed_bundle_rejected(mutate, "actual atlas-local backing")


def test_bundle_rejects_rehashed_point_encoder_provenance_disagreement():
    def mutate(payload, _bundle):
        payload["points"][0]["encoder_revision"] = "mismatched-revision"

    _assert_rehashed_bundle_rejected(mutate, "point encoder provenance")
