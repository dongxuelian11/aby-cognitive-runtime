"""P1.4 S2 topology, purity, failure, accounting, and timeout tests."""

from __future__ import annotations

import time
from pathlib import Path

from aby.baselines.s2 import (
    PROPOSAL_EXECUTION,
    S2_AGGREGATOR_PROMPT_SHA256,
    S2_AGGREGATOR_PROMPT_VERSION,
    S2_AGGREGATOR_PROMPT_V0_1,
    S2_PROPOSER_PROMPT_SHA256,
    S2_PROPOSER_PROMPT_VERSION,
    S2_PROPOSER_PROMPT_V0_1,
    ProviderCallSpec,
    S2ConventionalMoA,
    build_s2,
)
from aby.events import EventLog
from aby.experiments import EpisodeInput, load_config, run_experiment
from aby.providers import (
    FakeProvider,
    LLMResponse,
    ProviderError,
    ProviderErrorKind,
)
from aby.runner import EpisodeRunner, EpisodeStatus

REPO_ROOT = Path(__file__).resolve().parent.parent


def _input(episode_id="s2-exp-ep0001", task="solve the shared task"):
    return EpisodeInput(
        episode_id=episode_id,
        dataset_id="synthetic",
        task_family="s2_test",
        input={"task": task},
        seed=7,
    )


class _RecordingProvider(FakeProvider):
    def __init__(
        self,
        model,
        *,
        content=None,
        usage_available=True,
        input_tokens=10,
        output_tokens=4,
        latency_ms=5,
        retries=0,
        fail_with=None,
        sleep_seconds=0.0,
        markers=None,
    ):
        super().__init__(model=model)
        self.content = content or f"answer from {model}"
        self.usage_available = usage_available
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.latency_ms = latency_ms
        self.retries = retries
        self.fail_with = fail_with
        self.sleep_seconds = sleep_seconds
        self.requests = []
        self.calls = 0
        self.markers = markers

    def generate(self, request, *, event_sink=None):
        self.calls += 1
        self.requests.append(request.model_copy(deep=True))
        if self.markers is not None:
            self.markers.append(f"start:{self.model}")
        if event_sink:
            event_sink(
                "model_request_started",
                {"provider": self.name, "model": self.model, "attempt": 1},
            )
        if self.sleep_seconds:
            time.sleep(self.sleep_seconds)
        if self.fail_with is not None:
            if event_sink:
                event_sink(
                    "model_request_failed",
                    {"provider": self.name, "model": self.model, "error_kind": self.fail_with.value},
                )
            raise ProviderError(
                self.fail_with, f"simulated {self.model} failure", transport_retries=self.retries
            )
        if self.markers is not None:
            self.markers.append(f"finish:{self.model}")
        total = self.input_tokens + self.output_tokens
        response = LLMResponse(
            content=self.content,
            provider=self.name,
            model=self.model,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            total_tokens=total,
            usage_available=self.usage_available,
            latency_ms=self.latency_ms,
            transport_retries=self.retries,
            finish_reason="stop",
            provider_request_id=f"req-{self.model}",
        )
        if event_sink:
            event_sink(
                "model_request_completed",
                {
                    "provider": self.name,
                    "model": self.model,
                    "input_tokens": self.input_tokens,
                    "output_tokens": self.output_tokens,
                    "usage_available": self.usage_available,
                    "transport_retries": self.retries,
                },
            )
        return response


def _system(proposers=None, aggregator=None):
    proposers = proposers or [
        _RecordingProvider("p0", content="candidate zero"),
        _RecordingProvider("p1", content="candidate one"),
        _RecordingProvider("p2", content="candidate two"),
    ]
    aggregator = aggregator or _RecordingProvider("agg", content="final synthesis")
    return S2ConventionalMoA(proposers, aggregator), proposers, aggregator


def _run(system, timeout=5.0):
    log = EventLog()
    record = EpisodeRunner().run(system, _input(), timeout, log)
    return record, log


def test_normal_s2_is_three_independent_proposals_plus_one_aggregation():
    system, proposers, aggregator = _system()
    record, log = _run(system)
    assert record.status == EpisodeStatus.COMPLETED
    assert [provider.calls for provider in proposers] == [1, 1, 1]
    assert aggregator.calls == 1
    meta = record.result.metadata
    assert meta["proposer_count"] == 3
    assert meta["logical_proposer_calls"] == 3
    assert meta["logical_aggregator_calls"] == 1
    assert meta["logical_model_calls"] == 4
    assert meta["model_helper_calls"] == 0
    assert meta["memory_reads"] == 0 and meta["memory_writes"] == 0
    assert meta["proposal_execution"] == PROPOSAL_EXECUTION
    assert record.result.tool_events == []
    assert record.result.output == {"answer": "final synthesis"}
    kinds = [event.kind for event in log.replay(record.episode_id)]
    assert kinds.count("model_request_started") == 4
    assert kinds[-1] == "episode_completed"


def test_proposers_only_see_original_task_and_aggregator_sees_all_in_slot_order():
    markers = []
    proposers = [
        _RecordingProvider(f"p{i}", content=f"slot-{i}-answer", markers=markers)
        for i in range(3)
    ]
    aggregator = _RecordingProvider("agg", markers=markers)
    system, _, _ = _system(proposers, aggregator)
    record, _ = _run(system)
    assert record.status == EpisodeStatus.COMPLETED
    for proposer in proposers:
        request = proposer.requests[0]
        assert request.messages[0].content == S2_PROPOSER_PROMPT_V0_1
        assert request.messages[1].content == "solve the shared task"
        assert "slot-" not in request.messages[1].content
    aggregate_request = aggregator.requests[0]
    assert aggregate_request.messages[0].content == S2_AGGREGATOR_PROMPT_V0_1
    user = aggregate_request.messages[1].content
    assert "Original task:\nsolve the shared task" in user
    positions = [user.index(f"Candidate {i}:\nslot-{i}-answer") for i in range(3)]
    assert positions == sorted(positions)
    assert markers.index("start:agg") > markers.index("finish:p2")


def test_prompt_versions_hashes_candidate_evidence_and_stable_models():
    system, _, _ = _system()
    record, _ = _run(system)
    meta = record.result.metadata
    assert meta["proposer_prompt_version"] == S2_PROPOSER_PROMPT_VERSION
    assert meta["proposer_prompt_sha256"] == S2_PROPOSER_PROMPT_SHA256
    assert meta["aggregator_prompt_version"] == S2_AGGREGATOR_PROMPT_VERSION
    assert meta["aggregator_prompt_sha256"] == S2_AGGREGATOR_PROMPT_SHA256
    assert meta["proposer_models"] == ["p0", "p1", "p2"]
    assert meta["aggregator_model"] == "agg"
    assert [item["slot"] for item in meta["candidate_evidence"]] == [0, 1, 2]
    assert all(len(item["content_sha256"]) == 64 for item in meta["candidate_evidence"])


def test_proposer_failure_fails_closed_and_never_calls_later_roles():
    proposers = [
        _RecordingProvider("p0"),
        _RecordingProvider("p1", fail_with=ProviderErrorKind.RATE_LIMITED, retries=2),
        _RecordingProvider("p2"),
    ]
    aggregator = _RecordingProvider("agg")
    record, log = _run(S2ConventionalMoA(proposers, aggregator))
    assert record.status == EpisodeStatus.FAILED
    assert [provider.calls for provider in proposers] == [1, 1, 0]
    assert aggregator.calls == 0
    meta = record.result.metadata
    assert meta["logical_proposer_calls"] == 2
    assert meta["logical_aggregator_calls"] == 0
    assert meta["logical_model_calls"] == 2
    assert meta["failure_role"] == "proposer" and meta["failure_slot"] == 1
    assert meta["provider_error_kind"] == "RATE_LIMITED"
    assert meta["transport_retries"] == 2
    assert "PROPOSER[1] RATE_LIMITED" in record.error
    assert log.replay(record.episode_id)[-1].kind == "episode_failed"


def test_aggregator_failure_fails_episode_after_all_proposals():
    aggregator = _RecordingProvider(
        "agg", fail_with=ProviderErrorKind.PROVIDER_ERROR, retries=1
    )
    system, proposers, _ = _system(aggregator=aggregator)
    record, _ = _run(system)
    assert record.status == EpisodeStatus.FAILED
    assert [provider.calls for provider in proposers] == [1, 1, 1]
    assert aggregator.calls == 1
    meta = record.result.metadata
    assert meta["logical_proposer_calls"] == 3
    assert meta["logical_aggregator_calls"] == 1
    assert meta["logical_model_calls"] == 4
    assert meta["failure_role"] == "aggregator"
    assert meta["provider_error_kind"] == "PROVIDER_ERROR"


def test_complete_usage_latency_and_retry_aggregation_is_exact():
    proposers = [
        _RecordingProvider("p0", input_tokens=1, output_tokens=2, latency_ms=3, retries=0),
        _RecordingProvider("p1", input_tokens=4, output_tokens=5, latency_ms=6, retries=1),
        _RecordingProvider("p2", input_tokens=7, output_tokens=8, latency_ms=9, retries=2),
    ]
    aggregator = _RecordingProvider(
        "agg", input_tokens=10, output_tokens=11, latency_ms=12, retries=3
    )
    record, _ = _run(S2ConventionalMoA(proposers, aggregator))
    meta = record.result.metadata
    assert meta["aggregate_usage_complete"] is True
    assert (meta["input_tokens"], meta["output_tokens"], meta["total_tokens"]) == (
        22,
        26,
        48,
    )
    assert meta["aggregate_provider_latency_ms"] == 30
    assert meta["aggregate_provider_latency_complete"] is True
    assert meta["transport_retries_per_call"] == [0, 1, 2, 3]
    assert meta["transport_retries"] == 6


def test_unavailable_usage_is_distinct_from_measured_zero_usage():
    proposers = [
        _RecordingProvider("p0", input_tokens=0, output_tokens=0, usage_available=True),
        _RecordingProvider("p1", input_tokens=0, output_tokens=0, usage_available=False),
        _RecordingProvider("p2", input_tokens=2, output_tokens=3, usage_available=True),
    ]
    record, _ = _run(S2ConventionalMoA(proposers, _RecordingProvider("agg")))
    calls = record.result.metadata["per_call_evidence"]
    assert calls[0]["usage_available"] is True and calls[0]["total_tokens"] == 0
    assert calls[1]["usage_available"] is False and calls[1]["total_tokens"] == 0
    assert record.result.metadata["aggregate_usage_complete"] is False
    assert record.result.metadata["usage_available"] is False


def test_role_specific_request_timeouts_and_outer_timeout_are_independent():
    proposers = [
        ProviderCallSpec(_RecordingProvider("p0"), timeout_seconds=3.0),
        ProviderCallSpec(_RecordingProvider("p1"), timeout_seconds=4.0),
        ProviderCallSpec(_RecordingProvider("p2"), timeout_seconds=5.0),
    ]
    aggregator = ProviderCallSpec(_RecordingProvider("agg"), timeout_seconds=6.0)
    system = S2ConventionalMoA(proposers, aggregator)
    record, _ = _run(system, timeout=0.5)
    assert record.status == EpisodeStatus.COMPLETED
    assert [spec.provider.requests[0].timeout_seconds for spec in proposers] == [3.0, 4.0, 5.0]
    assert aggregator.provider.requests[0].timeout_seconds == 6.0
    assert record.timeout_seconds == 0.5


def test_outer_timeout_discards_late_s2_result_and_buffered_events():
    slow = _RecordingProvider("slow", sleep_seconds=0.3)
    system = S2ConventionalMoA(
        [slow, _RecordingProvider("p1"), _RecordingProvider("p2")],
        _RecordingProvider("agg"),
    )
    log = EventLog()
    record = EpisodeRunner().run(system, _input(), 0.04, log)
    assert record.status == EpisodeStatus.TIMED_OUT and record.result is None
    before = [event.model_dump() for event in log.replay(record.episode_id)]
    assert [event["kind"] for event in before] == [
        "episode_created",
        "episode_started",
        "episode_timed_out",
    ]
    time.sleep(0.4)
    assert record.result is None and record.status == EpisodeStatus.TIMED_OUT
    assert [event.model_dump() for event in log.replay(record.episode_id)] == before


def test_fake_harness_is_deterministic_with_stable_event_ids_and_neutral_telemetry(
    tmp_path,
):
    config = load_config(
        REPO_ROOT / "experiments" / "configs" / "example_s2_fake_provider.json"
    )
    first = run_experiment(config, build_s2(config), tmp_path / "first")
    second = run_experiment(config, build_s2(config), tmp_path / "second")

    normalized = []
    for summary in (first, second):
        per_run = []
        for directory in summary.artifact_dirs:
            import json

            result = json.loads((directory / "result.json").read_text(encoding="utf-8"))
            meta = result["metadata"]
            per_run.append(
                {
                    "output": result["output"],
                    "logical_model_calls": meta["logical_model_calls"],
                    "candidate_evidence": meta["candidate_evidence"],
                    "proposer_models": meta["proposer_models"],
                    "aggregator_model": meta["aggregator_model"],
                    "input_tokens": meta["input_tokens"],
                    "output_tokens": meta["output_tokens"],
                    "transport_retries": meta["transport_retries"],
                }
            )
            events = [
                json.loads(line)
                for line in (directory / "events.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            event_ids = [event["event_id"] for event in events]
            assert len(event_ids) == len(set(event_ids))
            assert [item["slot"] for item in meta["candidate_evidence"]] == [0, 1, 2]
            telemetry = json.loads((directory / "telemetry.json").read_text(encoding="utf-8"))
            assert telemetry["tool_calls"] == 0
            assert telemetry["A_raw"] == 0 and telemetry["B_raw"] == 0
            assert telemetry["a"] == 0.0 and telemetry["b"] == 0.0 and telemetry["y"] == 0.0
        normalized.append(per_run)
    assert normalized[0] == normalized[1]


def test_s2_source_has_no_forbidden_runtime_imports_or_prompt_instructions():
    source = (REPO_ROOT / "aby" / "baselines" / "s2.py").read_text(encoding="utf-8")
    for runtime_ref in (
        "from ..memory",
        "import aby.memory",
        "from ..lanes",
        "from ..resolver",
        "MacroFrame",
        "ActionFrame",
        "FieldFrame",
    ):
        assert runtime_ref not in source
    prompts = (S2_PROPOSER_PROMPT_V0_1 + S2_AGGREGATOR_PROMPT_V0_1).lower()
    for forbidden in (
        "macro",
        "micro",
        "dissipation",
        "manifold",
        "geodesic",
        "critic",
        "judge",
        "vote",
        "self-reflection",
        "chain-of-thought",
    ):
        assert forbidden not in prompts
