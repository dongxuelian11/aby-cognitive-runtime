"""P1.2 CLI tests: offline S0 validate/run, real config validate, no-credential failure."""

import json
from pathlib import Path

from aby import cli

REPO_ROOT = Path(__file__).resolve().parent.parent
FAKE_CONFIG = REPO_ROOT / "experiments" / "configs" / "example_s0_fake_provider.json"
REAL_CONFIG = REPO_ROOT / "experiments" / "configs" / "example_s0_openai_compat.json"


def test_cli_status_reports_s0_candidate(capsys):
    assert cli.main(["status"]) == 0
    out = capsys.readouterr().out
    assert "P1.2 S0 Single-LLM Baseline: IMPLEMENTED_CANDIDATE" in out
    assert "SCIENTIFICALLY_VALIDATED: no" in out


def test_s0_offline_config_validates(capsys):
    assert cli.main(["experiment", "validate", str(FAKE_CONFIG)]) == 0
    assert "OK: example-s0-fake" in capsys.readouterr().out


def test_s0_offline_run_end_to_end(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["experiment", "dry-run", str(FAKE_CONFIG)]) == 0
    out = capsys.readouterr().out
    assert "OK: dry-run example-s0-fake" in out
    directory = tmp_path / "artifacts" / "experiments" / "example-s0-fake" / "example-s0-fake-ep0001"
    result = json.loads((directory / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == "SUCCEEDED"
    assert result["metadata"]["logical_model_calls"] == 1
    assert result["metadata"]["system_id"] == "S0"


def test_real_provider_config_validates_without_network(capsys):
    assert cli.main(["experiment", "validate", str(REAL_CONFIG)]) == 0
    assert "OK: example-s0-openai-compat" in capsys.readouterr().out


def test_real_provider_run_without_credential_fails_clearly(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ABY_LLM_API_KEY", raising=False)
    assert cli.main(["experiment", "dry-run", str(REAL_CONFIG)]) == 2
    err = capsys.readouterr().err
    assert "ABY_LLM_API_KEY" in err
    assert "ERROR" in err
