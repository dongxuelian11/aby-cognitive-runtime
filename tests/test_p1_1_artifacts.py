"""P1.1 artifact, telemetry, and provenance tests."""

import hashlib
import json
import subprocess
from pathlib import Path

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


def test_provenance_binds_exact_repo_commit(tmp_path):
    config = _make_config("echo", experiment_id="prov-exp")
    run_experiment(config, EchoSystem(), artifacts_root=tmp_path)
    directory = episode_artifact_dir(tmp_path, config.experiment_id, "prov-exp-ep0001")
    provenance = json.loads((directory / "provenance.json").read_text(encoding="utf-8"))
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True
    ).stdout.strip()
    assert provenance["repo_commit"] == head


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
