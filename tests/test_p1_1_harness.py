"""P1.1 harness tests: config, system interface, episode lifecycle, events."""

import json
import random
import time

import pytest
from pydantic import ValidationError

from aby.events import Event, EventLog
from aby.experiments import (
    EXPERIMENT_CONFIG_SCHEMA_VERSION,
    EchoSystem,
    EpisodeInput,
    EpisodeResult,
    ExperimentConfig,
    FixtureSystem,
    load_config,
)
from aby.runner import EpisodeRecord, EpisodeRunner, EpisodeStatus
REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent


def _make_config(**overrides) -> ExperimentConfig:
    base = dict(
        schema_version=EXPERIMENT_CONFIG_SCHEMA_VERSION,
        experiment_id="test-exp",
        seed=7,
        system_id="echo",
        dataset_id="synthetic",
        task_family="unit_test",
    )
    base.update(overrides)
    return ExperimentConfig(**base)


def _make_input(episode_id: str = "test-exp-ep0001", seed: int = 7) -> EpisodeInput:
    return EpisodeInput(
        episode_id=episode_id,
        dataset_id="synthetic",
        task_family="unit_test",
        input={"task": "hello"},
        seed=seed,
    )


# --- experiment config -------------------------------------------------------


def test_config_json_roundtrip():
    config = _make_config(episode_limit=3, timeout_seconds=1.5, metadata={"note": "x"})
    restored = ExperimentConfig.from_json(config.to_json())
    assert restored == config


def test_config_rejects_unknown_fields():
    raw = json.dumps({**_make_config().model_dump(), "surprise_field": 1})
    with pytest.raises(ValidationError):
        ExperimentConfig.from_json(raw)


def test_config_rejects_invalid_values():
    with pytest.raises(ValidationError):
        _make_config(episode_limit=0)
    with pytest.raises(ValidationError):
        _make_config(timeout_seconds=-1)


def test_example_config_loads_and_has_no_secrets():
    path = REPO_ROOT / "experiments" / "configs" / "example_echo_system.json"
    raw = path.read_text(encoding="utf-8")
    config = load_config(path)
    assert config.schema_version == EXPERIMENT_CONFIG_SCHEMA_VERSION
    assert config.system_id == "echo"
    lowered = raw.lower()
    for forbidden in ("api_key", "token", "secret", "password"):
        assert forbidden not in lowered


# --- system interface --------------------------------------------------------


def test_echo_system_is_neutral_and_normalized():
    result = EchoSystem().run_episode(_make_input())
    assert result.status == "SUCCEEDED"
    assert result.error == ""
    assert result.output["seed"] == 7
    # normalized result concepts only: output/status/error/tool_events/metadata
    assert set(EpisodeResult.model_fields) == {
        "output",
        "status",
        "error",
        "tool_events",
        "rework_events",
        "metadata",
    }


def test_fixture_system_is_deterministic_per_seed():
    result_a = FixtureSystem().run_episode(_make_input(seed=123))
    result_b = FixtureSystem().run_episode(_make_input(seed=123))
    assert result_a.output == result_b.output
    assert [t.model_dump() for t in result_a.tool_events] == [
        t.model_dump() for t in result_b.tool_events
    ]
    expected_value = random.Random(123).randint(0, 10**6)
    assert result_a.output["value"] == expected_value


# --- episode lifecycle -------------------------------------------------------


def test_episode_lifecycle_success():
    log = EventLog()
    record = EpisodeRunner().run(EchoSystem(), _make_input(), timeout_seconds=5.0, event_log=log)
    assert record.status == EpisodeStatus.COMPLETED
    assert record.error == ""
    assert record.result is not None and record.result.status == "SUCCEEDED"
    kinds = [e.kind for e in log.replay("test-exp-ep0001")]
    assert kinds == ["episode_created", "episode_started", "episode_completed"]


class _FailingSystem:
    def run_episode(self, episode_input):
        raise RuntimeError("boom")


def test_episode_lifecycle_failure_captures_exception():
    log = EventLog()
    record = EpisodeRunner().run(_FailingSystem(), _make_input(), timeout_seconds=5.0, event_log=log)
    assert record.status == EpisodeStatus.FAILED
    assert "RuntimeError" in record.error and "boom" in record.error
    assert log.replay("test-exp-ep0001")[-1].kind == "episode_failed"


class _SlowSystem:
    def run_episode(self, episode_input):
        time.sleep(0.5)
        return None


def test_episode_timeout_is_bounded():
    log = EventLog()
    record = EpisodeRunner().run(_SlowSystem(), _make_input(), timeout_seconds=0.05, event_log=log)
    assert record.status == EpisodeStatus.TIMED_OUT
    assert "timeout" in record.error
    assert log.replay("test-exp-ep0001")[-1].kind == "episode_timed_out"


def test_runner_emits_tool_and_rework_events_before_terminal():
    log = EventLog()
    EpisodeRunner().run(FixtureSystem(), _make_input(seed=9), timeout_seconds=5.0, event_log=log)
    kinds = [e.kind for e in log.replay("test-exp-ep0001")]
    assert kinds == [
        "episode_created",
        "episode_started",
        "tool_call",
        "tool_call",
        "rework",
        "episode_completed",
    ]


# --- event log ---------------------------------------------------------------


def test_event_append_replay_ordering_and_stable_ids():
    log = EventLog()
    for kind in ("a", "b", "c"):
        log.append(Event(episode_id="e1", kind=kind, ts="2026-08-13T00:00:00+00:00"))
    log.append(Event(episode_id="e2", kind="x", ts="2026-08-13T00:00:00+00:00"))
    replayed = log.replay("e1")
    assert [e.kind for e in replayed] == ["a", "b", "c"]
    assert [e.seq for e in replayed] == [1, 2, 3]
    assert [e.event_id for e in replayed] == ["e1#000001", "e1#000002", "e1#000003"]
    assert log.replay("e2")[0].seq == 1


def test_replay_cannot_mutate_historical_events():
    log = EventLog()
    log.append(Event(episode_id="e1", kind="a", payload={"n": 1}))
    mutated = log.replay("e1")
    mutated[0].payload["n"] = 999
    assert log.replay("e1")[0].payload["n"] == 1


def test_event_log_json_roundtrip_preserves_order():
    log = EventLog()
    for kind in ("created", "tool", "completed"):
        log.append(Event(episode_id="e1", kind=kind, ts="2026-08-13T00:00:00+00:00"))
    restored = EventLog.from_json(log.to_json())
    assert [e.kind for e in restored.replay("e1")] == ["created", "tool", "completed"]
