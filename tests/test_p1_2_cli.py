"""P1.2 CLI tests: offline dry-run, semantic validation, explicit S0 run."""

import json
import urllib.request
from pathlib import Path

import pytest

from aby import cli
from aby.providers import OpenAICompatProvider

REPO_ROOT = Path(__file__).resolve().parent.parent
FAKE_CONFIG = REPO_ROOT / "experiments" / "configs" / "example_s0_fake_provider.json"
REAL_CONFIG = REPO_ROOT / "experiments" / "configs" / "example_s0_openai_compat.json"


def _write_provider_config(tmp_path, provider, *, experiment_id="cli-provider-test"):
    data = json.loads(FAKE_CONFIG.read_text(encoding="utf-8"))
    data["experiment_id"] = experiment_id
    data["episode_limit"] = 1
    data["metadata"]["provider"] = provider
    path = tmp_path / f"{experiment_id}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


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


def test_real_provider_config_validates_without_credentials_or_network(monkeypatch, capsys):
    calls = {"credential": 0, "network": 0}

    def forbidden_credential(*args, **kwargs):
        calls["credential"] += 1
        raise AssertionError("credential resolution must not run during validate")

    def forbidden_network(*args, **kwargs):
        calls["network"] += 1
        raise AssertionError("network must not run during validate")

    monkeypatch.delenv("ABY_LLM_API_KEY", raising=False)
    monkeypatch.setattr(OpenAICompatProvider, "_resolve_api_key", forbidden_credential)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden_network)
    assert cli.main(["experiment", "validate", str(REAL_CONFIG)]) == 0
    assert "OK: example-s0-openai-compat" in capsys.readouterr().out
    assert calls == {"credential": 0, "network": 0}


def test_real_provider_dry_run_is_offline_only_even_with_credential(
    tmp_path, monkeypatch, capsys
):
    calls = {"credential": 0, "network": 0}

    def forbidden_credential(*args, **kwargs):
        calls["credential"] += 1
        raise AssertionError("credential resolution must not run during dry-run")

    def forbidden_network(*args, **kwargs):
        calls["network"] += 1
        raise AssertionError("network must not run during dry-run")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ABY_LLM_API_KEY", "present-but-must-not-be-read")
    monkeypatch.setattr(OpenAICompatProvider, "_resolve_api_key", forbidden_credential)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden_network)
    assert cli.main(["experiment", "dry-run", str(REAL_CONFIG)]) == 2
    err = capsys.readouterr().err
    assert "offline-only" in err
    assert "aby run --config" in err
    assert calls == {"credential": 0, "network": 0}


def test_real_provider_explicit_run_without_credential_fails_clearly(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ABY_LLM_API_KEY", raising=False)
    assert cli.main(["run", "--config", str(REAL_CONFIG)]) == 2
    err = capsys.readouterr().err
    assert "ABY_LLM_API_KEY" in err
    assert "ERROR" in err


def test_explicit_s0_fake_run_uses_non_dry_run_path(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["run", "--config", str(FAKE_CONFIG)]) == 0
    assert "OK: run example-s0-fake" in capsys.readouterr().out


@pytest.mark.parametrize(
    "provider",
    [
        {"type": "mystery", "model": "x"},
        {"type": "openai_compat", "model": "x"},
        {"type": "openai_compat", "base_url": "http://example.test/v1"},
        {
            "type": "openai_compat",
            "base_url": "http://example.test/v1",
            "model": "x",
            "timeout_seconds": 0,
        },
        {
            "type": "openai_compat",
            "base_url": "http://example.test/v1",
            "model": "x",
            "max_retries": -1,
        },
        {
            "type": "openai_compat",
            "base_url": "http://example.test/v1",
            "model": "x",
            "max_output_tokens": 0,
        },
    ],
)
def test_invalid_s0_provider_semantics_fail_at_validate_time(
    tmp_path, provider, capsys
):
    path = _write_provider_config(tmp_path, provider)
    assert cli.main(["experiment", "validate", str(path)]) == 2
    assert "invalid experiment config semantics" in capsys.readouterr().err
