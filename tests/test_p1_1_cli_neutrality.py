"""P1.1 CLI, architecture-neutrality, and P0 freeze-invariant tests."""

import hashlib
import json
from pathlib import Path

from aby import cli
from aby.events import Event, EventLog
from aby.experiments import (
    EXPERIMENT_CONFIG_SCHEMA_VERSION,
    EchoSystem,
    ExperimentConfig,
    run_experiment,
)

REPO_ROOT = Path(__file__).resolve().parent.parent

P0_FROZEN_DOC = REPO_ROOT / "docs" / "p0" / "ABY_P0_THEORY_FREEZE_EXPERIMENTAL_ARCHITECTURE_V0_1.md"
EXPECTED_P0_FROZEN_SHA256 = "0900350395d44ba478990af47686ecdab5a8c7918fd2a377ced5303ff72984d4"

EXAMPLE_CONFIG = REPO_ROOT / "experiments" / "configs" / "example_echo_system.json"


def _write_config(path: Path, **overrides):
    base = {
        "schema_version": EXPERIMENT_CONFIG_SCHEMA_VERSION,
        "experiment_id": "cli-exp",
        "seed": 5,
        "system_id": "echo",
        "dataset_id": "synthetic",
        "task_family": "cli_test",
        "episode_limit": 1,
    }
    base.update(overrides)
    path.write_text(json.dumps(base), encoding="utf-8")


# --- CLI ---------------------------------------------------------------------


def test_cli_validate_ok(capsys):
    assert cli.main(["experiment", "validate", str(EXAMPLE_CONFIG)]) == 0
    out = capsys.readouterr().out
    assert "OK: example-echo-system" in out


def test_cli_validate_rejects_invalid_config(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    _write_config(bad, unknown_field=True)
    assert cli.main(["experiment", "validate", str(bad)]) == 2
    assert "ERROR" in capsys.readouterr().err


def test_cli_validate_rejects_missing_file(tmp_path, capsys):
    assert cli.main(["experiment", "validate", str(tmp_path / "missing.json")]) == 2
    assert "ERROR" in capsys.readouterr().err


def test_cli_dry_run_produces_artifacts_offline(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["experiment", "dry-run", str(EXAMPLE_CONFIG)]) == 0
    out = capsys.readouterr().out
    assert "OK: dry-run example-echo-system" in out
    directory = tmp_path / "artifacts" / "experiments" / "example-echo-system" / "example-echo-system-ep0001"
    for name in ("config.json", "events.jsonl", "result.json", "telemetry.json", "provenance.json"):
        assert (directory / name).is_file()
    result = json.loads((directory / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == "SUCCEEDED"


def test_cli_dry_run_unknown_system_fails_closed(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    config = tmp_path / "unknown.json"
    _write_config(config, system_id="S9-unknown")  # no implementation exists
    assert cli.main(["experiment", "dry-run", str(config)]) == 2
    assert "ERROR" in capsys.readouterr().err


# --- architecture neutrality (§8 hard criterion) ------------------------------


def test_neutrality_harness_code_has_no_aby_frame_references():
    sources = [
        REPO_ROOT / "aby" / "experiments" / "config.py",
        REPO_ROOT / "aby" / "experiments" / "system.py",
        REPO_ROOT / "aby" / "experiments" / "harness.py",
        REPO_ROOT / "aby" / "experiments" / "artifacts.py",
        REPO_ROOT / "aby" / "experiments" / "provenance.py",
        REPO_ROOT / "aby" / "runner" / "__init__.py",
        REPO_ROOT / "aby" / "telemetry" / "__init__.py",
    ]
    for path in sources:
        text = path.read_text(encoding="utf-8")
        for frame in ("MacroFrame", "ActionFrame", "DissipationFrame", "ResolveDecision"):
            assert frame not in text, f"{frame} referenced in {path.name}"


def test_neutrality_config_has_no_aby_specific_fields():
    fields = set(ExperimentConfig.model_fields)
    assert not fields.intersection({"qA", "qB", "qY", "A_raw", "B_raw", "W_raw", "frame", "lane"})


def test_neutrality_event_log_supports_generic_system_ids():
    log = EventLog()
    log.append(Event(episode_id="e1", kind="tool_call", payload={"system_id": "generic-custom"}))
    assert log.replay("e1")[0].payload["system_id"] == "generic-custom"


def test_neutrality_provenance_identifies_arbitrary_system(tmp_path):
    config = ExperimentConfig(
        schema_version=EXPERIMENT_CONFIG_SCHEMA_VERSION,
        experiment_id="neutral-exp",
        seed=3,
        system_id="S9-generic-label",
        dataset_id="synthetic",
        task_family="neutrality_test",
        episode_limit=1,
    )
    summary = run_experiment(config, EchoSystem(), artifacts_root=tmp_path)
    directory = summary.artifact_dirs[0]
    provenance = json.loads((directory / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["system_id"] == "S9-generic-label"


def test_neutrality_deterministic_dry_run_for_generic_label(tmp_path):
    config = ExperimentConfig(
        schema_version=EXPERIMENT_CONFIG_SCHEMA_VERSION,
        experiment_id="neutral-dry",
        seed=21,
        system_id="S9-generic-label",
        dataset_id="synthetic",
        task_family="neutrality_test",
        episode_limit=2,
    )
    summary = run_experiment(config, EchoSystem(), artifacts_root=tmp_path)
    assert len(summary.artifact_dirs) == 2
    assert all(status == "COMPLETED" for status in summary.episode_statuses.values())


# --- P0 frozen invariant -----------------------------------------------------


def test_p0_frozen_document_hash_invariant():
    digest = hashlib.sha256(P0_FROZEN_DOC.read_bytes()).hexdigest()
    assert digest == EXPECTED_P0_FROZEN_SHA256
