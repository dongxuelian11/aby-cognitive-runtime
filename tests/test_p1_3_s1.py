"""P1.3 S1 purity, evidence, timeout, and committed-memory tests."""

import json
import time
import urllib.request
from pathlib import Path

from aby.baselines.s1 import (
    S1_PROMPT_SHA256,
    S1_PROMPT_VERSION,
    S1_SYSTEM_PROMPT_V0_1,
    S1SingleLLM,
    build_s1,
)
from aby.events import EventLog
from aby.experiments import (
    EXPERIMENT_CONFIG_SCHEMA_VERSION,
    EpisodeInput,
    ExperimentConfig,
    run_experiment,
)
from aby.experiments.artifacts import episode_artifact_dir
from aby.memory import InMemoryKeywordMemory
from aby.providers import FakeProvider, LLMResponse, ProviderErrorKind
from aby.runner import EpisodeRunner, EpisodeStatus

REPO_ROOT = Path(__file__).resolve().parent.parent


def _config(experiment_id="s1-exp", episodes=1, **provider):
    return ExperimentConfig(
        schema_version=EXPERIMENT_CONFIG_SCHEMA_VERSION,
        experiment_id=experiment_id,
        seed=11,
        system_id="S1",
        dataset_id="synthetic",
        task_family="shared topic",
        episode_limit=episodes,
        timeout_seconds=5.0,
        metadata={
            "provider": provider or {"type": "fake", "model": "fake-s1"},
            "memory": {
                "backend": "in_memory_keyword",
                "top_k": 3,
                "max_context_chars": 256,
            },
        },
    )


def _input(episode_id="s1-exp-ep0001", task="shared topic first task"):
    return EpisodeInput(
        episode_id=episode_id,
        dataset_id="synthetic",
        task_family="shared topic",
        input={"task": task},
        seed=11,
    )


class _CountingProvider(FakeProvider):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.calls = 0
        self.requests = []

    def generate(self, request, *, event_sink=None):
        self.calls += 1
        self.requests.append(request.model_copy(deep=True))
        return super().generate(request, event_sink=event_sink)


class _UsageProvider(_CountingProvider):
    def generate(self, request, *, event_sink=None):
        self.calls += 1
        self.requests.append(request.model_copy(deep=True))
        return LLMResponse(
            content="observed",
            provider=self.name,
            model=self.model,
            input_tokens=17,
            output_tokens=4,
            total_tokens=21,
            usage_available=True,
            latency_ms=23,
            transport_retries=1,
        )


class _FailOnMemoryCommitEventLog(EventLog):
    def append(self, event):
        if event.kind == "memory_commit":
            raise RuntimeError("injected memory_commit append failure")
        return super().append(event)


class _FailBeforeMemoryPublicationEventLog(EventLog):
    def append(self, event):
        if event.kind == "memory_retrieval":
            raise RuntimeError("injected pre-publication finalizer failure")
        return super().append(event)


def _run(system, episode_input, timeout=5.0):
    log = EventLog()
    record = EpisodeRunner().run(system, episode_input, timeout, log)
    return record, log


def test_finalizer_failure_after_new_publication_rolls_back_memory():
    memory = InMemoryKeywordMemory()
    provider = _UsageProvider()
    system = S1SingleLLM(provider, memory=memory)
    episode_input = _input(task="unique atomic rollback marker")
    log = _FailOnMemoryCommitEventLog()

    record = EpisodeRunner().run(system, episode_input, 5.0, log)

    assert record.status == EpisodeStatus.FAILED
    assert "outcome finalization failed" in record.error
    assert "injected memory_commit append failure" in record.error
    assert provider.calls == 1
    assert memory.committed_episode_count == 0
    assert memory.load_episode(episode_input.episode_id) is None
    assert memory.search("unique atomic rollback marker", k=5) == []
    assert "memory_commit" not in [
        event.kind for event in log.replay(episode_input.episode_id)
    ]


def test_finalizer_failure_before_publication_leaves_zero_memory():
    memory = InMemoryKeywordMemory()
    provider = _UsageProvider()
    system = S1SingleLLM(provider, memory=memory)
    episode_input = _input(task="unique pre-publication failure marker")
    log = _FailBeforeMemoryPublicationEventLog()

    record = EpisodeRunner().run(system, episode_input, 5.0, log)

    assert record.status == EpisodeStatus.FAILED
    assert "outcome finalization failed" in record.error
    assert "injected pre-publication finalizer failure" in record.error
    assert provider.calls == 1
    assert memory.committed_episode_count == 0
    assert memory.load_episode(episode_input.episode_id) is None
    assert memory.search("unique pre-publication failure marker", k=5) == []
    assert "memory_commit" not in [
        event.kind for event in log.replay(episode_input.episode_id)
    ]


def test_finalizer_failure_does_not_delete_preexisting_identical_memory():
    memory = InMemoryKeywordMemory()
    episode_input = _input(task="unique preserved history marker")
    existing = memory.store_episode(
        episode_input.episode_id,
        {
            "task_family": episode_input.task_family,
            "task": episode_input.input["task"],
            "answer": "observed",
        },
    )
    provider = _UsageProvider()
    system = S1SingleLLM(provider, memory=memory)
    log = _FailOnMemoryCommitEventLog()

    record = EpisodeRunner().run(system, episode_input, 5.0, log)

    assert record.status == EpisodeStatus.FAILED
    assert "outcome finalization failed" in record.error
    assert "injected memory_commit append failure" in record.error
    assert provider.calls == 1
    preserved = memory.load_episode(episode_input.episode_id)
    assert preserved is not None
    assert preserved.item_id == existing.item_id
    assert memory.committed_episode_count == 1
    preserved_ids = [
        hit.item_id
        for hit in memory.search("unique preserved history marker", k=5)
    ]
    assert preserved_ids == [existing.item_id]
    assert "memory_commit" not in [
        event.kind for event in log.replay(episode_input.episode_id)
    ]


def test_s1_one_model_call_fixed_prompt_and_zero_helper_calls():
    provider = _CountingProvider(model="fake-s1")
    system = S1SingleLLM(provider, memory_top_k=2, memory_max_context_chars=128)
    record, log = _run(system, _input())
    assert record.status == EpisodeStatus.COMPLETED
    assert provider.calls == 1
    assert record.result.metadata["logical_model_calls"] == 1
    assert record.result.metadata["memory_llm_calls"] == 0
    assert record.result.metadata["prompt_version"] == S1_PROMPT_VERSION
    assert record.result.metadata["prompt_sha256"] == S1_PROMPT_SHA256
    assert provider.requests[0].messages[0].content == S1_SYSTEM_PROMPT_V0_1
    assert record.result.tool_events == []
    assert [event.kind for event in log.replay(_input().episode_id)].count(
        "model_request_started"
    ) == 1


def test_episode_one_is_not_visible_to_itself_and_episode_two_retrieves_it():
    provider = _CountingProvider(model="fake-s1")
    memory = InMemoryKeywordMemory()
    system = S1SingleLLM(provider, memory=memory, memory_top_k=5)
    first, first_log = _run(system, _input())
    first_id = first.result.metadata["committed_memory_id"]
    assert first.result.metadata["memory_hits"] == 0
    assert first.result.metadata["retrieved_memory_ids"] == []
    assert first.result.metadata["memory_writes_committed"] == 1
    assert memory.committed_episode_count == 1
    assert "memory_commit" in [event.kind for event in first_log.replay(first.episode_id)]

    second, _ = _run(
        system,
        _input("s1-exp-ep0002", "shared topic followup task"),
    )
    assert second.status == EpisodeStatus.COMPLETED
    assert second.result.metadata["memory_hits"] >= 1
    assert first_id in second.result.metadata["retrieved_memory_ids"]
    assert first_id in provider.requests[1].messages[1].content
    assert provider.calls == 2


def test_failed_provider_episode_never_commits_memory():
    memory = InMemoryKeywordMemory()
    system = S1SingleLLM(
        FakeProvider(fail_with=ProviderErrorKind.PROVIDER_ERROR), memory=memory
    )
    record, log = _run(system, _input())
    assert record.status == EpisodeStatus.FAILED
    assert record.result.metadata["memory_writes_committed"] == 0
    assert memory.committed_episode_count == 0
    assert "memory_commit" not in [event.kind for event in log.replay(record.episode_id)]


def test_timed_out_late_worker_never_becomes_retrievable():
    memory = InMemoryKeywordMemory()
    slow = S1SingleLLM(FakeProvider(sleep_seconds=0.35), memory=memory)
    record, log = _run(slow, _input(task="late contamination marker"), timeout=0.04)
    assert record.status == EpisodeStatus.TIMED_OUT
    assert record.result is None
    events_at_timeout = [event.model_dump() for event in log.replay(record.episode_id)]
    time.sleep(0.45)
    assert memory.committed_episode_count == 0
    assert memory.search("contamination marker", k=5) == []
    assert [event.model_dump() for event in log.replay(record.episode_id)] == events_at_timeout

    next_system = S1SingleLLM(FakeProvider(), memory=memory)
    next_record, _ = _run(
        next_system,
        _input("s1-exp-ep0002", "contamination marker followup"),
    )
    assert next_record.result.metadata["memory_hits"] == 0
    assert next_record.result.metadata["retrieved_memory_ids"] == []


def test_memory_context_and_evidence_are_bounded_and_usage_propagates():
    memory = InMemoryKeywordMemory()
    memory.store_episode(
        "prior", {"task_family": "shared", "task": "bounded keyword", "answer": "x" * 500}
    )
    provider = _UsageProvider()
    system = S1SingleLLM(
        provider, memory=memory, memory_top_k=1, memory_max_context_chars=80,
        provider_timeout_seconds=7.25,
    )
    record, _ = _run(system, _input(task="bounded keyword"))
    meta = record.result.metadata
    assert meta["retrieved_memory_chars"] <= 80
    assert meta["memory_top_k"] == 1
    assert meta["memory_max_context_chars"] == 80
    assert meta["input_tokens"] == 17 and meta["output_tokens"] == 4
    assert meta["usage_available"] is True
    assert meta["provider_latency_ms"] == 23
    assert meta["transport_retries"] == 1
    assert provider.requests[0].timeout_seconds == 7.25


def test_build_s1_fresh_store_isolation_and_timeout_authority(monkeypatch):
    config = _config(
        type="openai_compat",
        base_url="http://example.test/v1",
        model="test-model",
        api_key_env="ABY_LLM_API_KEY",
        timeout_seconds=7.25,
        max_retries=0,
    )
    first = build_s1(config)
    second = build_s1(config)
    assert first.memory is not second.memory
    first.memory.store_episode(
        "prior", {"task_family": "x", "task": "isolation", "answer": "ok"}
    )
    assert second.memory.search("isolation", k=5) == []

    captured = {}

    class _Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self):
            return json.dumps({
                "id": "req-s1", "model": "test-model",
                "choices": [{"finish_reason": "stop", "message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 2, "completion_tokens": 1, "total_tokens": 3},
            }).encode("utf-8")

    def fake_urlopen(request, timeout=None):
        captured["timeout"] = timeout
        return _Response()

    monkeypatch.setenv("ABY_LLM_API_KEY", "test-only")
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    record, _ = _run(second, _input())
    assert record.status == EpisodeStatus.COMPLETED
    assert captured["timeout"] == 7.25
    assert record.result.metadata["provider_timeout_seconds"] == 7.25


def test_harness_two_episode_offline_evidence_and_fresh_rerun_determinism(tmp_path):
    config = _config(experiment_id="s1-deterministic", episodes=2)
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first = run_experiment(config, build_s1(config), artifacts_root=first_root)
    second = run_experiment(config, build_s1(config), artifacts_root=second_root)
    normalized = []
    for root, summary in ((first_root, first), (second_root, second)):
        results = []
        for index, directory in enumerate(summary.artifact_dirs):
            result = json.loads((directory / "result.json").read_text(encoding="utf-8"))
            result["metadata"].pop("provider_latency_ms", None)
            results.append(result)
            assert result["metadata"]["logical_model_calls"] == 1
            assert result["tool_events"] == []
            if index == 0:
                assert result["metadata"]["memory_hits"] == 0
            else:
                assert result["metadata"]["memory_hits"] >= 1
        normalized.append(results)
    assert normalized[0] == normalized[1]

    directory = episode_artifact_dir(
        first_root, config.experiment_id, "s1-deterministic-ep0002"
    )
    events = [
        json.loads(line)
        for line in (directory / "events.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [event["kind"] for event in events].index("memory_retrieval") < [
        event["kind"] for event in events
    ].index("model_request_started")
    assert events[-2]["kind"] == "memory_commit"
    assert events[-1]["kind"] == "episode_completed"


def test_s1_source_has_no_forbidden_architecture_or_tool_features():
    source = (REPO_ROOT / "aby" / "baselines" / "s1.py").read_text(encoding="utf-8")
    for forbidden in (
        "MacroFrame", "ActionFrame", "DissipationFrame", "ResolveDecision",
        "aby.lanes", "aby.resolver", "query_rewrite", "embedding", "vector database",
    ):
        assert forbidden not in source
