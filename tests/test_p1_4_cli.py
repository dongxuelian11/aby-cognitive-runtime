"""P1.4 S2 CLI offline and explicit execution boundary tests."""

import json
import urllib.request
from pathlib import Path

from aby import cli
from aby.providers import OpenAICompatProvider

REPO_ROOT = Path(__file__).resolve().parent.parent
FAKE_CONFIG = REPO_ROOT / "experiments" / "configs" / "example_s2_fake_provider.json"
MIXED_CONFIG = (
    REPO_ROOT / "experiments" / "configs" / "example_s2_mixed_openai_compat.json"
)


def test_status_reports_s1_accepted_and_s2_candidate(capsys):
    assert cli.main(["status"]) == 0
    out = capsys.readouterr().out
    assert "P1.3 S1 Review State: ACCEPTED / MERGED" in out
    assert "P1.4 S2 Conventional MoA Baseline: IMPLEMENTED_CANDIDATE" in out


def test_s2_fake_validate_and_dry_run_are_offline(tmp_path, monkeypatch, capsys):
    def forbidden_network(*args, **kwargs):
        raise AssertionError("network must not run")

    monkeypatch.setattr(urllib.request, "urlopen", forbidden_network)
    assert cli.main(["experiment", "validate", str(FAKE_CONFIG)]) == 0
    monkeypatch.chdir(tmp_path)
    assert cli.main(["experiment", "dry-run", str(FAKE_CONFIG)]) == 0
    result_path = (
        tmp_path
        / "artifacts"
        / "experiments"
        / "example-s2-fake"
        / "example-s2-fake-ep0001"
        / "result.json"
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["metadata"]["system_id"] == "S2"
    assert result["metadata"]["logical_proposer_calls"] == 3
    assert result["metadata"]["logical_aggregator_calls"] == 1
    assert result["metadata"]["logical_model_calls"] == 4
    assert result["metadata"]["memory_reads"] == 0
    assert result["tool_events"] == []
    assert "_s2_pending_events" not in result["metadata"]


def test_mixed_validate_is_offline_without_credentials(monkeypatch, capsys):
    calls = {"credential": 0, "network": 0}

    def forbidden_credential(*args, **kwargs):
        calls["credential"] += 1
        raise AssertionError("credential resolution touched")

    def forbidden_network(*args, **kwargs):
        calls["network"] += 1
        raise AssertionError("network touched")

    monkeypatch.delenv("ABY_S2_PROPOSER_API_KEY", raising=False)
    monkeypatch.delenv("ABY_S2_AGGREGATOR_API_KEY", raising=False)
    monkeypatch.setattr(OpenAICompatProvider, "_resolve_api_key", forbidden_credential)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden_network)
    assert cli.main(["experiment", "validate", str(MIXED_CONFIG)]) == 0
    assert calls == {"credential": 0, "network": 0}
    assert "OK: example-s2-mixed-openai-compat" in capsys.readouterr().out


def test_mixed_dry_run_rejected_before_any_credential_or_network(
    tmp_path, monkeypatch, capsys
):
    calls = {"credential": 0, "network": 0}

    def forbidden_credential(*args, **kwargs):
        calls["credential"] += 1
        raise AssertionError("credential resolution touched")

    def forbidden_network(*args, **kwargs):
        calls["network"] += 1
        raise AssertionError("network touched")

    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ABY_S2_PROPOSER_API_KEY", "present-but-forbidden")
    monkeypatch.setenv("ABY_S2_AGGREGATOR_API_KEY", "present-but-forbidden")
    monkeypatch.setattr(OpenAICompatProvider, "_resolve_api_key", forbidden_credential)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden_network)
    assert cli.main(["experiment", "dry-run", str(MIXED_CONFIG)]) == 2
    assert calls == {"credential": 0, "network": 0}
    assert "offline-only" in capsys.readouterr().err


def test_explicit_mixed_run_reports_all_missing_credentials(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ABY_S2_PROPOSER_API_KEY", raising=False)
    monkeypatch.delenv("ABY_S2_AGGREGATOR_API_KEY", raising=False)
    assert cli.main(["run", "--config", str(MIXED_CONFIG)]) == 2
    err = capsys.readouterr().err
    assert "ABY_S2_PROPOSER_API_KEY" in err
    assert "ABY_S2_AGGREGATOR_API_KEY" in err


def test_explicit_all_fake_s2_run_uses_real_execution_command(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["run", "--config", str(FAKE_CONFIG)]) == 0
    assert "OK: run example-s2-fake" in capsys.readouterr().out


def test_unknown_provider_fails_at_offline_validate(tmp_path, capsys):
    data = json.loads(FAKE_CONFIG.read_text(encoding="utf-8"))
    data["experiment_id"] = "s2-invalid-provider"
    data["metadata"]["moa"]["proposers"][1]["provider"]["type"] = "unknown"
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert cli.main(["experiment", "validate", str(path)]) == 2
    assert "invalid experiment config semantics" in capsys.readouterr().err
