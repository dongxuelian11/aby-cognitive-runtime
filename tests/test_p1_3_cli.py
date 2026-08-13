"""P1.3 S1 offline validation, dry-run, and explicit-run CLI tests."""

import json
import urllib.request
from pathlib import Path

import pytest

from aby import cli
from aby.providers import OpenAICompatProvider

REPO_ROOT = Path(__file__).resolve().parent.parent
FAKE_CONFIG = REPO_ROOT / "experiments" / "configs" / "example_s1_fake_provider.json"
REAL_CONFIG = REPO_ROOT / "experiments" / "configs" / "example_s1_openai_compat.json"


def _variant(tmp_path, memory, experiment_id="s1-invalid"):
    data = json.loads(FAKE_CONFIG.read_text(encoding="utf-8"))
    data["experiment_id"] = experiment_id
    data["metadata"]["memory"] = memory
    path = tmp_path / f"{experiment_id}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_status_reports_p1_2_accepted_and_s1_candidate(capsys):
    assert cli.main(["status"]) == 0
    out = capsys.readouterr().out
    assert "P1.2 S0 Review State: ACCEPTED / MERGED" in out
    assert "P1.3 S1 Shared-Memory/RAG Baseline: IMPLEMENTED_CANDIDATE" in out


def test_s1_fake_validate_and_dry_run_are_offline(tmp_path, monkeypatch, capsys):
    def forbidden_network(*args, **kwargs):
        raise AssertionError("network must not run")

    monkeypatch.setattr(urllib.request, "urlopen", forbidden_network)
    assert cli.main(["experiment", "validate", str(FAKE_CONFIG)]) == 0
    monkeypatch.chdir(tmp_path)
    assert cli.main(["experiment", "dry-run", str(FAKE_CONFIG)]) == 0
    result_path = (
        tmp_path / "artifacts" / "experiments" / "example-s1-fake"
        / "example-s1-fake-ep0002" / "result.json"
    )
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["metadata"]["system_id"] == "S1"
    assert result["metadata"]["memory_hits"] >= 1


def test_s1_real_validate_is_offline_without_credentials(monkeypatch, capsys):
    calls = {"credential": 0, "network": 0}

    def forbidden_credential(*args, **kwargs):
        calls["credential"] += 1
        raise AssertionError("credential resolution touched")

    def forbidden_network(*args, **kwargs):
        calls["network"] += 1
        raise AssertionError("network touched")

    monkeypatch.delenv("ABY_LLM_API_KEY", raising=False)
    monkeypatch.setattr(OpenAICompatProvider, "_resolve_api_key", forbidden_credential)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden_network)
    assert cli.main(["experiment", "validate", str(REAL_CONFIG)]) == 0
    assert calls == {"credential": 0, "network": 0}
    assert "OK: example-s1-openai-compat" in capsys.readouterr().out


def test_s1_real_dry_run_rejected_before_credentials_or_network(
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
    monkeypatch.setenv("ABY_LLM_API_KEY", "present-but-forbidden")
    monkeypatch.setattr(OpenAICompatProvider, "_resolve_api_key", forbidden_credential)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden_network)
    assert cli.main(["experiment", "dry-run", str(REAL_CONFIG)]) == 2
    assert calls == {"credential": 0, "network": 0}
    assert "offline-only" in capsys.readouterr().err


def test_s1_explicit_real_run_missing_credential_fails_clearly(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("ABY_LLM_API_KEY", raising=False)
    assert cli.main(["run", "--config", str(REAL_CONFIG)]) == 2
    err = capsys.readouterr().err
    assert "S1 real provider" in err
    assert "ABY_LLM_API_KEY" in err


def test_explicit_s1_fake_run_uses_real_execution_command(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    assert cli.main(["run", "--config", str(FAKE_CONFIG)]) == 0
    assert "OK: run example-s1-fake" in capsys.readouterr().out


@pytest.mark.parametrize(
    "memory",
    [
        {"backend": "vector_db", "top_k": 5, "max_context_chars": 4000},
        {"backend": "in_memory_keyword", "top_k": 0, "max_context_chars": 4000},
        {"backend": "in_memory_keyword", "top_k": 101, "max_context_chars": 4000},
        {"backend": "in_memory_keyword", "top_k": 5, "max_context_chars": 0},
        {"backend": "in_memory_keyword", "top_k": 5, "max_context_chars": 100001},
        {"backend": "in_memory_keyword", "top_k": 5, "max_context_chars": 4000, "typo": 1},
    ],
)
def test_invalid_s1_memory_semantics_fail_offline(tmp_path, memory, capsys):
    path = _variant(tmp_path, memory)
    assert cli.main(["experiment", "validate", str(path)]) == 2
    assert "invalid experiment config semantics" in capsys.readouterr().err
