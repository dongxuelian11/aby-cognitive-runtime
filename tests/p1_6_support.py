"""Role-aware deterministic fake providers for P1.6 tests only."""

from __future__ import annotations

import json
import threading
from typing import Literal

from aby.providers.base import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderError,
    ProviderErrorKind,
    emit,
)
from aby.runtime.bundle import (
    ABYParallelRuntimeConfig,
    LaneGenerationConfig,
    SemanticGeometryRuntimeConfig,
)
from aby.runtime.parallel import ABYParallelRuntime
from aby.runtime.snapshot import RuntimeSnapshot


VALID_FRAMES = {
    "A": {
        "macro_state": ["accepted fact", "stable identity"],
        "relevant_history": ["prior accepted event"],
        "active_constraints": ["remain within P1.6"],
        "long_term_goals": ["preserve falsifiability"],
        "continuity_risks": ["authority drift"],
        "candidate_interpretations": ["bounded runtime proposal"],
        "confidence": 0.8,
        "evidence_refs": ["evidence-a"],
    },
    "B": {
        "current_intent": "produce one bounded proposal",
        "local_plan": ["read snapshot", "return action frame"],
        "candidate_actions": ["propose next bounded step"],
        "tool_requests": ["tool intent only"],
        "expected_result": "auditable action proposal",
        "local_uncertainties": ["provider variation"],
        "confidence": 0.7,
        "evidence_refs": ["evidence-b"],
    },
    "Y": {
        "conflicts": ["candidate conflict"],
        "uncertainties": ["prediction uncertainty"],
        "goal_drift": ["possible goal drift"],
        "memory_mismatch": ["possible memory mismatch"],
        "factual_mismatch": ["possible factual mismatch"],
        "redundancy": ["possible duplicate work"],
        "rework_risk": ["possible rework"],
        "context_drift": ["possible context drift"],
        "unresolved_tension": ["unresolved boundary"],
        "estimated_y": 0.4,
        "confidence": 0.6,
        "recommended_resolution_targets": ["inspect authority boundary"],
    },
}


class RoleAwareFakeProvider(LLMProvider):
    name = "p1_6_role_fake"

    def __init__(
        self,
        lane: Literal["A", "B", "Y"],
        *,
        content: str | None = None,
        barrier: threading.Barrier | None = None,
        wait_for: threading.Event | None = None,
        signal: threading.Event | None = None,
        fail_with: ProviderErrorKind | None = None,
        usage_available: bool = True,
        transport_retries: int = 0,
    ) -> None:
        self.lane = lane
        self.model = f"fake-{lane.lower()}"
        self.content = content or json.dumps(
            VALID_FRAMES[lane], ensure_ascii=False, sort_keys=True
        )
        self.barrier = barrier
        self.wait_for = wait_for
        self.signal = signal
        self.fail_with = fail_with
        self.usage_available = usage_available
        self.configured_transport_retries = transport_retries
        self.call_count = 0
        self.requests: list[LLMRequest] = []

    def generate(self, request: LLMRequest, *, event_sink=None) -> LLMResponse:
        self.call_count += 1
        self.requests.append(request.model_copy(deep=True))
        emit(event_sink, "fake_started", {"slot": self.lane, "attempt": 1})
        if self.barrier is not None:
            try:
                self.barrier.wait(timeout=3)
            except threading.BrokenBarrierError as exc:
                raise ProviderError(
                    ProviderErrorKind.PROVIDER_TIMEOUT,
                    "synchronization barrier not reached by all lanes",
                ) from exc
        if self.wait_for is not None and not self.wait_for.wait(timeout=3):
            raise ProviderError(
                ProviderErrorKind.PROVIDER_TIMEOUT,
                "deterministic completion gate timed out",
            )
        if self.fail_with is not None:
            emit(
                event_sink,
                "fake_failed",
                {"slot": self.lane, "error_kind": self.fail_with.value},
            )
            if self.signal is not None:
                self.signal.set()
            raise ProviderError(
                self.fail_with,
                "simulated bounded provider failure",
                transport_retries=self.configured_transport_retries,
            )

        token_base = {"A": 10, "B": 20, "Y": 30}[self.lane]
        emit(event_sink, "fake_completed", {"slot": self.lane, "usage_available": self.usage_available})
        if self.signal is not None:
            self.signal.set()
        return LLMResponse(
            content=self.content,
            provider=self.name,
            model=self.model,
            finish_reason="stop",
            input_tokens=token_base if self.usage_available else 0,
            output_tokens=5 if self.usage_available else 0,
            total_tokens=token_base + 5 if self.usage_available else 0,
            usage_available=self.usage_available,
            latency_ms={"A": 30, "B": 10, "Y": 20}[self.lane],
            transport_retries=self.configured_transport_retries,
        )


def runtime_providers(**overrides):
    return {
        lane: RoleAwareFakeProvider(lane, **overrides.get(lane, {}))
        for lane in ("A", "B", "Y")
    }


def sample_snapshot(**changes) -> RuntimeSnapshot:
    payload = {
        "episode_id": "p1-6-episode",
        "current_event": "current accepted event",
        "current_task": "produce bounded parallel proposals",
        "accepted_facts": ("fact-one", "fact-two"),
        "selected_evidence": ("evidence-one",),
        "active_constraints": ("no authority mutation",),
        "long_term_goals": ("preserve falsifiability",),
        "relevant_history": ("accepted historical item",),
        "local_context": ("local bounded context",),
        "available_tools": ("read-only-tool-description",),
    }
    payload.update(changes)
    return RuntimeSnapshot.create(**payload)


def runtime_config(*, geometry: bool = False) -> ABYParallelRuntimeConfig:
    return ABYParallelRuntimeConfig(
        a_lane=LaneGenerationConfig(model="requested-a", seed=11),
        b_lane=LaneGenerationConfig(model="requested-b", seed=12),
        y_lane=LaneGenerationConfig(model="requested-y", seed=13),
        semantic_geometry=SemanticGeometryRuntimeConfig(
            enabled=geometry, atlas_k=3, matches_per_source=2
        ),
    )


def build_runtime(providers, *, encoder=None) -> ABYParallelRuntime:
    return ABYParallelRuntime(
        a_provider=providers["A"],
        b_provider=providers["B"],
        y_provider=providers["Y"],
        encoder=encoder,
    )


__all__ = [
    "VALID_FRAMES",
    "RoleAwareFakeProvider",
    "runtime_providers",
    "sample_snapshot",
    "runtime_config",
    "build_runtime",
]
