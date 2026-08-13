"""P1.2 S0 Single-LLM baseline tests: purity, integration, secrets, regressions."""

import json
from pathlib import Path

import pytest

from aby.baselines.s0 import (
    S0_PROMPT_SHA256,
    S0_PROMPT_VERSION,
    S0_SYSTEM_ID,
    S0SingleLLM,
    build_s0,
)
from aby.events import EventLog
from aby.experiments import (
    EXPERIMENT_CONFIG_SCHEMA_VERSION,
    EpisodeInput,
    ExperimentConfig,
    run_experiment,
)
from aby.experiments.artifacts import episode_artifact_dir
from aby.providers import FakeProvider, ProviderError, ProviderErrorKind
from aby.runner import EpisodeRunner, EpisodeStatus

REPO_ROOT = Path(__file__).resolve().parent.parent
API_KEY_ENV = "ABY_LLM_API_KEY"
SECRET = "sk-test-secret-xyz"


def _config(experiment_id: str = "s0-exp", **provider_spec) -> ExperimentConfig:
    return ExperimentConfig(
        schema_version=EXPERIMENT_CONFIG_SCHEMA_VERSION,
        experiment_id=experiment_id,
        seed=9,
        system_id=S0_SYSTEM_ID,
        dataset_id="synthetic",
        task_family="s0_unit_test",
        episode_limit=1,
        timeout_seconds=5.0,
        metadata={"provider": provider_spec or {"type": "fake"}},
    )


def _input(episode_id: str = "s0-exp-ep0001") -> EpisodeInput:
    return EpisodeInput(
        episode_id=episode_id,
        dataset_id="synthetic",
        task_family="s0_unit_test",
        input={"task": "say hello"},
        seed=9,
    )


class _CountingProvider(FakeProvider):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.calls = 0

    def generate(self, request, *, event_sink=None):
        self.calls += 1
        return super().generate(request, event_sink=event_sink)


# --- S0 purity (§10, §11) ----------------------------------------------------


def test_s0_exactly_one_logical_inference_per_normal_episode():
    provider = _CountingProvider()
    system = S0SingleLLM(provider, temperature=0.0, max_output_tokens=64)
    log = EventLog()
    record = EpisodeRunner().run(system, _input(), timeout_seconds=5.0, event_log=log)
    assert provider.calls == 1
    assert record.status == EpisodeStatus.COMPLETED
    assert record.result is not None and record.result.status == "SUCCEEDED"


def test_s0_normalized_result_and_prompt_evidence():
    result = S0SingleLLM(FakeProvider()).run_episode(_input())
    assert result.status == "SUCCEEDED"
    assert result.output["answer"].startswith("[fake ")
    assert result.tool_events == []  # no tools
    meta = result.metadata
    assert meta["prompt_version"] == S0_PROMPT_VERSION
    assert meta["prompt_sha256"] == S0_PROMPT_SHA256
    assert meta["logical_model_calls"] == 1
    assert meta["transport_retries"] == 0
    assert meta["input_tokens"] > 0 and meta["output_tokens"] > 0
    assert meta["provider_latency_ms"] >= 0


def test_s0_failure_is_normalized_with_error_kind():
    system = S0SingleLLM(FakeProvider(fail_with=ProviderErrorKind.PROVIDER_ERROR))
    result = system.run_episode(_input())
    assert result.status == "FAILED"
    assert "PROVIDER_ERROR" in result.error
    assert result.metadata["provider_error_kind"] == "PROVIDER_ERROR"
    assert result.metadata["logical_model_calls"] == 1


def test_s0_purity_no_forbidden_dependencies():
    sources = [
        REPO_ROOT / "aby" / "baselines" / "s0.py",
        REPO_ROOT / "aby" / "providers" / "base.py",
        REPO_ROOT / "aby" / "providers" / "fake.py",
        REPO_ROOT / "aby" / "providers" / "openai_compat.py",
    ]
    for path in sources:
        text = path.read_text(encoding="utf-8")
        for frame in ("MacroFrame", "ActionFrame", "DissipationFrame", "ResolveDecision"):
            assert frame not in text, f"{frame} referenced in {path.name}"
        for module in ("aby.memory", "aby.lanes", "aby.resolver", "aby.contracts"):
            assert module not in text, f"{module} imported in {path.name}"


def test_s0_prompt_contains_only_task_instruction():
    from aby.baselines.s0 import S0_PROMPT_V0_1

    lowered = S0_PROMPT_V0_1.lower()
    for banned in ("self-reflection", "chain-of-thought", "memory", "lane", "dissipation"):
        assert banned not in lowered


# --- harness integration -----------------------------------------------------


def test_s0_runs_through_harness_with_artifacts(tmp_path):
    config = _config()
    summary = run_experiment(config, build_s0(config), artifacts_root=tmp_path)
    directory = episode_artifact_dir(tmp_path, config.experiment_id, "s0-exp-ep0001")
    assert directory == summary.artifact_dirs[0]

    result = json.loads((directory / "result.json").read_text(encoding="utf-8"))
    assert result["status"] == "SUCCEEDED"
    assert result["metadata"]["logical_model_calls"] == 1
    assert result["metadata"]["system_id"] == "S0"

    telemetry = json.loads((directory / "telemetry.json").read_text(encoding="utf-8"))
    assert telemetry["schema"] == "ABY_RUNTIME_TELEMETRY_V0.1"
    assert telemetry["tool_calls"] == 0
    assert telemetry["failed_tool_calls"] == 0
    assert telemetry["input_tokens"] > 0
    assert telemetry["output_tokens"] > 0
    assert telemetry["latency_ms"] >= 0
    # ABY-instrumentation stays not-observed (P1.1 convention preserved).
    assert telemetry["A_raw"] == 0 and telemetry["a"] == 0.0

    provenance = json.loads((directory / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["system_id"] == "S0"

    events = [
        json.loads(line)
        for line in (directory / "events.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    kinds = [e["kind"] for e in events]
    assert "model_request_started" in kinds
    assert "model_request_completed" in kinds
    assert kinds.index("model_request_started") < kinds.index("model_request_completed")


def test_s0_artifacts_never_persist_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv(API_KEY_ENV, SECRET)
    config = _config()  # fake provider: env must still never leak into artifacts
    run_experiment(config, build_s0(config), artifacts_root=tmp_path)
    directory = episode_artifact_dir(tmp_path, config.experiment_id, "s0-exp-ep0001")
    for file in directory.iterdir():
        assert SECRET not in file.read_text(encoding="utf-8"), f"secret leaked into {file.name}"


def test_s0_timeout_regression_preserved():
    system = S0SingleLLM(FakeProvider(sleep_seconds=0.6))
    log = EventLog()
    record = EpisodeRunner().run(system, _input(), timeout_seconds=0.05, event_log=log)
    assert record.status == EpisodeStatus.TIMED_OUT


def test_build_s0_unknown_provider_type_fails_closed():
    with pytest.raises(ValueError):
        build_s0(_config(type="mystery_provider"))


def test_build_s0_real_provider_requires_base_url():
    with pytest.raises(ValueError):
        build_s0(_config(type="openai_compat", model="m"))
