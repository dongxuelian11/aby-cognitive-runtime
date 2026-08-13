"""P1.4 S2 config matrix, construction, and transport-timeout tests."""

import json
import urllib.request

import pytest

from aby.baselines.s2 import build_s2, validate_s2_config
from aby.experiments import EXPERIMENT_CONFIG_SCHEMA_VERSION, EpisodeInput, ExperimentConfig


def _config(proposers, aggregator, proposer_count=None):
    moa = {
        "proposers": [{"provider": provider} for provider in proposers],
        "aggregator": {"provider": aggregator},
        "proposal_execution": "sequential_v0",
    }
    moa["proposer_count"] = len(proposers) if proposer_count is None else proposer_count
    return ExperimentConfig(
        schema_version=EXPERIMENT_CONFIG_SCHEMA_VERSION,
        experiment_id="s2-provider-matrix",
        seed=1,
        system_id="S2",
        dataset_id="synthetic",
        task_family="matrix",
        metadata={"moa": moa},
    )


def _input():
    return EpisodeInput(
        episode_id="s2-provider-matrix-ep0001",
        dataset_id="synthetic",
        task_family="matrix",
        input={"task": "matrix task"},
        seed=1,
    )


def test_homogeneous_and_heterogeneous_fake_provider_configs_build():
    homogeneous = _config(
        [{"type": "fake", "model": "same"}] * 3,
        {"type": "fake", "model": "same"},
    )
    hetero = _config(
        [
            {"type": "fake", "model": "p0"},
            {"type": "fake", "model": "p1"},
            {"type": "fake", "model": "p2"},
        ],
        {"type": "fake", "model": "agg"},
    )
    assert [spec.provider.model for spec in build_s2(homogeneous).proposers] == [
        "same",
        "same",
        "same",
    ]
    assert [spec.provider.model for spec in build_s2(hetero).proposers] == [
        "p0",
        "p1",
        "p2",
    ]


def test_omitted_proposer_count_defaults_to_three():
    config = _config(
        [{"type": "fake", "model": f"p{i}"} for i in range(3)],
        {"type": "fake", "model": "agg"},
    )
    del config.metadata["moa"]["proposer_count"]
    assert validate_s2_config(config)["proposer_count"] == 3


def test_s2_validation_rejects_wrong_system_id():
    config = _config(
        [{"type": "fake", "model": f"p{i}"} for i in range(3)],
        {"type": "fake", "model": "agg"},
    )
    config.system_id = "S0"
    with pytest.raises(ValueError, match="requires system_id"):
        validate_s2_config(config)


@pytest.mark.parametrize("count", [2, 3, 8])
def test_valid_proposer_count_bounds(count):
    config = _config(
        [{"type": "fake", "model": f"p{i}"} for i in range(count)],
        {"type": "fake", "model": "agg"},
        proposer_count=count,
    )
    assert validate_s2_config(config)["proposer_count"] == count


@pytest.mark.parametrize("count", [0, 1, 9, True])
def test_invalid_proposer_count_fails_closed(count):
    proposer_len = 2 if count in (0, 1, True) else count
    config = _config(
        [{"type": "fake", "model": f"p{i}"} for i in range(proposer_len)],
        {"type": "fake", "model": "agg"},
        proposer_count=count,
    )
    with pytest.raises(ValueError, match="proposer_count"):
        validate_s2_config(config)


def test_proposer_count_must_match_slot_count():
    config = _config(
        [{"type": "fake", "model": "p0"}, {"type": "fake", "model": "p1"}],
        {"type": "fake", "model": "agg"},
        proposer_count=3,
    )
    with pytest.raises(ValueError, match="must equal"):
        validate_s2_config(config)


@pytest.mark.parametrize("role", ["proposer", "aggregator"])
def test_unknown_provider_in_any_role_fails_closed(role):
    proposers = [
        {"type": "fake", "model": "p0"},
        {"type": "fake", "model": "p1"},
    ]
    aggregator = {"type": "fake", "model": "agg"}
    if role == "proposer":
        proposers[1] = {"type": "mystery", "model": "bad"}
    else:
        aggregator = {"type": "mystery", "model": "bad"}
    with pytest.raises(ValueError, match=r"unknown S2 .+\.provider type"):
        validate_s2_config(_config(proposers, aggregator))


def test_secret_value_and_unknown_fields_are_rejected():
    with pytest.raises(ValueError, match="forbidden secret fields"):
        validate_s2_config(
            _config(
                [
                    {"type": "fake", "model": "p0", "api_key": "forbidden"},
                    {"type": "fake", "model": "p1"},
                ],
                {"type": "fake", "model": "agg"},
            )
        )
    with pytest.raises(ValueError, match="unknown S2"):
        validate_s2_config(
            _config(
                [{"type": "fake", "model": "p0"}, {"type": "fake", "model": "p1"}],
                {"type": "fake", "model": "agg", "typo": 1},
            )
        )


class _HTTPResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


def test_proposer_and_aggregator_timeouts_reach_exact_http_transport(monkeypatch):
    timeouts = []

    def fake_urlopen(request, timeout=None):
        timeouts.append(timeout)
        return _HTTPResponse(
            json.dumps(
                {
                    "id": f"req-{len(timeouts)}",
                    "model": "wire-model",
                    "choices": [{"finish_reason": "stop", "message": {"content": "ok"}}],
                    "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3},
                }
            ).encode("utf-8")
        )

    def real(model, env_name, timeout):
        return {
            "type": "openai_compat",
            "base_url": "http://example.test/v1",
            "model": model,
            "api_key_env": env_name,
            "timeout_seconds": timeout,
            "max_retries": 0,
        }

    monkeypatch.setenv("S2_KEY", "test-only")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    config = _config(
        [real("p0", "S2_KEY", 3.0), real("p1", "S2_KEY", 4.0), real("p2", "S2_KEY", 5.0)],
        real("agg", "S2_KEY", 6.0),
    )
    result = build_s2(config).run_episode(_input())
    assert result.status == "SUCCEEDED"
    assert timeouts == [3.0, 4.0, 5.0, 6.0]
