"""P1.1 artifact, telemetry, and provenance tests."""

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from aby.events import EventLog
from aby.experiments import (
    EXPERIMENT_CONFIG_SCHEMA_VERSION,
    EchoSystem,
    ExperimentConfig,
    FixtureSystem,
    NullSystem,
    run_experiment,
)
from aby.experiments.artifacts import episode_artifact_dir

REPO_ROOT = Path(__file__).resolve().parent.parent


def _make_config(system_id: str, experiment_id: str = "artifacts-exp") -> ExperimentConfig:
    return ExperimentConfig(
        schema_version=EXPERIMENT_CONFIG_SCHEMA_VERSION,
        experiment_id=experiment_id,
        seed=11,
        system_id=system_id,
        dataset_id="synthetic",
        task_family="unit_test",
        episode_limit=1,
        timeout_seconds=5.0,
    )


# --- artifact generation -----------------------------------------------------


def test_artifact_generation_produces_five_files(tmp_path):
    config = _make_config("echo")
    summary = run_experiment(config, EchoSystem(), artifacts_root=tmp_path)
    directory = episode_artifact_dir(tmp_path, config.experiment_id, "artifacts-exp-ep0001")
    assert directory == summary.artifact_dirs[0]
    for name in ("config.json", "events.jsonl", "result.json", "telemetry.json", "provenance.json"):
        assert (directory / name).is_file()
    restored = ExperimentConfig.from_json((directory / "config.json").read_text(encoding="utf-8"))
    assert restored == config
    result = json.loads((directory / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == "SUCCEEDED"


def test_events_jsonl_is_replayable(tmp_path):
    config = _make_config("fixture")
    run_experiment(config, FixtureSystem(), artifacts_root=tmp_path)
    directory = episode_artifact_dir(tmp_path, config.experiment_id, "artifacts-exp-ep0001")
    lines = [
        json.loads(line)
        for line in (directory / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    restored = EventLog.from_json(lines)
    kinds = [e.kind for e in restored.replay("artifacts-exp-ep0001")]
    assert kinds == [
        "episode_created",
        "episode_started",
        "tool_call",
        "tool_call",
        "rework",
        "episode_completed",
    ]


_FORBIDDEN_KEYS = {"api_key", "apikey", "access_token", "token", "secret", "password", "authorization"}
_FORBIDDEN_VALUES = ("api_key", "apikey", "access_token", "password", "authorization", "bearer ")


def _assert_no_secrets(value, path: str):
    if isinstance(value, dict):
        for key, item in value.items():
            assert key.lower() not in _FORBIDDEN_KEYS, f"{key} at {path}"
            _assert_no_secrets(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _assert_no_secrets(item, f"{path}[{index}]")
    elif isinstance(value, str):
        lowered = value.lower()
        for word in _FORBIDDEN_VALUES:
            assert word not in lowered, f"{word!r} in value at {path}"


def test_artifacts_contain_no_secret_material(tmp_path):
    config = _make_config("fixture")
    run_experiment(config, FixtureSystem(), artifacts_root=tmp_path)
    directory = episode_artifact_dir(tmp_path, config.experiment_id, "artifacts-exp-ep0001")
    for file in directory.iterdir():
        text = file.read_text(encoding="utf-8")
        if file.name == "events.jsonl":  # JSON-lines: one object per line
            for line in text.splitlines():
                if line.strip():
                    _assert_no_secrets(json.loads(line), file.name)
        else:
            _assert_no_secrets(json.loads(text), file.name)


# --- provenance --------------------------------------------------------------


def test_provenance_binds_repo_commit_and_propagates_git_state(tmp_path):
    from aby.experiments import provenance as prov

    config = _make_config("echo", experiment_id="prov-exp")
    run_experiment(config, EchoSystem(), artifacts_root=tmp_path)
    directory = episode_artifact_dir(tmp_path, config.experiment_id, "prov-exp-ep0001")
    provenance = json.loads((directory / "provenance.json").read_text(encoding="utf-8"))
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True
    ).stdout.strip()
    assert provenance["repo_commit"] == head
    # The artifact must reflect the real, current binding state exactly.
    expected = prov.get_git_state()
    assert provenance["source_binding"] == expected.source_binding
    assert provenance["worktree_state"] == expected.worktree_state


def test_provenance_clean_commit_state_is_labeled_exact(tmp_path, monkeypatch):
    from aby.experiments import provenance as prov

    clean = prov.GitState(
        repo_commit="f5ada87eb65f29bf6a4e798160ed562cde7e84c2",
        worktree_state="CLEAN",
        source_binding="EXACT_CLEAN_COMMIT",
    )
    monkeypatch.setattr(prov, "get_git_state", lambda: clean)

    config = _make_config("echo", experiment_id="clean-exp")
    run_experiment(config, EchoSystem(), artifacts_root=tmp_path)
    directory = episode_artifact_dir(tmp_path, config.experiment_id, "clean-exp-ep0001")
    provenance = json.loads((directory / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["source_binding"] == "EXACT_CLEAN_COMMIT"
    assert provenance["worktree_state"] == "CLEAN"
    assert provenance["repo_commit"] == "f5ada87eb65f29bf6a4e798160ed562cde7e84c2"


def test_provenance_dirty_worktree_is_non_exact(tmp_path, monkeypatch):
    from aby.experiments import provenance as prov

    fake = prov.GitState(
        repo_commit="abc123def456",
        worktree_state="DIRTY",
        source_binding="NON_EXACT_DIRTY",
        tracked_diff_sha256="deadbeef",
    )
    monkeypatch.setattr(prov, "get_git_state", lambda: fake)

    config = _make_config("echo", experiment_id="dirty-exp")
    run_experiment(config, EchoSystem(), artifacts_root=tmp_path)
    directory = episode_artifact_dir(tmp_path, config.experiment_id, "dirty-exp-ep0001")
    provenance = json.loads((directory / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["repo_commit"] == "abc123def456"
    assert provenance["source_binding"] == "NON_EXACT_DIRTY"
    assert provenance["worktree_state"] == "DIRTY"
    assert provenance["tracked_diff_sha256"] == "deadbeef"
    # Normal fields remain intact.
    for field in ("experiment_schema_version", "system_id", "seed", "config_sha256"):
        assert field in provenance


def test_provenance_not_a_git_repo_is_unavailable(tmp_path):
    from aby.experiments import provenance as prov

    state = prov.get_git_state(cwd=tmp_path)  # pytest tmp dir has no .git
    assert state.source_binding == "UNAVAILABLE"
    assert state.worktree_state == "UNKNOWN"
    assert state.repo_commit == ""


def test_provenance_git_unavailable_is_explicit(monkeypatch):
    from aby.experiments import provenance as prov

    def _git_missing(*args, **kwargs):
        raise FileNotFoundError("git not installed")

    monkeypatch.setattr(prov.subprocess, "run", _git_missing)
    state = prov.get_git_state()
    assert state.source_binding == "UNAVAILABLE"
    assert state.worktree_state == "UNKNOWN"
    assert state.repo_commit == ""


# --- artifact path containment (correction D) --------------------------------


def test_artifact_dir_rejects_path_traversal_ids(tmp_path):
    for experiment_id in ("../escape", "a/b"):
        with pytest.raises(ValueError):
            episode_artifact_dir(tmp_path, experiment_id, "ep0001")
    for episode_id in ("..\\escape", "a\\b", "/absolute"):
        with pytest.raises(ValueError):
            episode_artifact_dir(tmp_path, "exp", episode_id)


def test_artifact_dir_resolves_under_experiments_root(tmp_path):
    directory = episode_artifact_dir(tmp_path, "exp-1.0_test", "ep0001")
    base = (Path(tmp_path) / "experiments").resolve()
    assert directory.is_relative_to(base)


def test_config_rejects_unsafe_experiment_ids():
    from pydantic import ValidationError

    for bad in ("../escape", "..\\escape", "a/b", "a\\b", "/absolute", "..", ""):
        with pytest.raises(ValidationError):
            ExperimentConfig(
                schema_version=EXPERIMENT_CONFIG_SCHEMA_VERSION,
                experiment_id=bad,
                seed=1,
                system_id="echo",
                dataset_id="synthetic",
                task_family="unit_test",
            )


def test_config_accepts_valid_identifier_shapes():
    for good in ("exp-1.0_test", "plain", "UPPER_42"):
        config = ExperimentConfig(
            schema_version=EXPERIMENT_CONFIG_SCHEMA_VERSION,
            experiment_id=good,
            seed=1,
            system_id="echo",
            dataset_id="synthetic",
            task_family="unit_test",
        )
        assert config.experiment_id == good


def test_provenance_has_required_fields_and_config_hash(tmp_path):
    config = _make_config("echo", experiment_id="prov-exp2")
    run_experiment(config, EchoSystem(), artifacts_root=tmp_path)
    directory = episode_artifact_dir(tmp_path, config.experiment_id, "prov-exp2-ep0001")
    provenance = json.loads((directory / "provenance.json").read_text(encoding="utf-8"))
    for field in (
        "repo_commit",
        "experiment_schema_version",
        "system_id",
        "seed",
        "python_version",
        "platform",
        "started_at",
        "finished_at",
    ):
        assert field in provenance
    config_text = (directory / "config.json").read_text(encoding="utf-8")
    assert provenance["config_sha256"] == hashlib.sha256(config_text.encode()).hexdigest()


# --- telemetry ---------------------------------------------------------------


def test_telemetry_collected_from_fixture_evidence(tmp_path):
    config = _make_config("fixture")
    run_experiment(config, FixtureSystem(), artifacts_root=tmp_path)
    directory = episode_artifact_dir(tmp_path, config.experiment_id, "artifacts-exp-ep0001")
    telemetry = json.loads((directory / "telemetry.json").read_text(encoding="utf-8"))
    assert telemetry["schema"] == "ABY_RUNTIME_TELEMETRY_V0.1"
    assert telemetry["episode_id"] == "artifacts-exp-ep0001"
    assert telemetry["tool_calls"] == 2
    assert telemetry["failed_tool_calls"] == 0
    assert telemetry["rework_count"] == 1
    assert telemetry["input_tokens"] == 12
    assert telemetry["output_tokens"] == 8
    assert telemetry["latency_ms"] >= 0
    # ABY-instrumentation fields: not applicable, not fabricated (P1.1 convention).
    assert telemetry["A_raw"] == 0 and telemetry["B_raw"] == 0 and telemetry["W_raw"] == 0
    assert telemetry["a"] == 0.0 and telemetry["b"] == 0.0 and telemetry["y"] == 0.0 and telemetry["r"] == 0.0
    # Frozen wire-format field names present (P0 §8).
    for frozen in ("qA", "qB", "qY", "latency_ms", "tool_calls", "failed_tool_calls", "user_result"):
        assert frozen in telemetry


def test_telemetry_not_fabricated_for_null_system(tmp_path):
    config = _make_config("null")
    run_experiment(config, NullSystem(), artifacts_root=tmp_path)
    directory = episode_artifact_dir(tmp_path, config.experiment_id, "artifacts-exp-ep0001")
    telemetry = json.loads((directory / "telemetry.json").read_text(encoding="utf-8"))
    assert telemetry["tool_calls"] == 0
    assert telemetry["rework_count"] == 0
    assert telemetry["input_tokens"] == 0
    assert telemetry["user_result"] is None
