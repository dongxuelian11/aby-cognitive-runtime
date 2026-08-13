"""P1.4 S2 conventional multi-provider proposal/aggregation baseline.

The topology is intentionally limited to independent proposal generation
followed by one synthesis call.  Proposal execution is ``sequential_v0`` in
this stage so call evidence and event ordering are deterministic and no false
parallel-latency claim is made.  The strategy is isolated behind the baseline
and can be replaced by a safe fan-out implementation in a separately reviewed
change.
"""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from typing import Any, Sequence

from ..events import Event, EventLog
from ..experiments.config import ExperimentConfig
from ..experiments.system import EpisodeInput, EpisodeResult
from ..providers import (
    FakeProvider,
    LLMMessage,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    OpenAICompatProvider,
    ProviderError,
)
from .s0 import _extract_task, validate_s0_provider_config

S2_SYSTEM_ID = "S2"
S2_PROPOSER_PROMPT_VERSION = "S2_PROPOSER_PROMPT_V0_1"
S2_AGGREGATOR_PROMPT_VERSION = "S2_AGGREGATOR_PROMPT_V0_1"
S2_PROPOSER_PROMPT_V0_1 = (
    "Solve the supplied task independently. Return the best direct answer you can."
)
S2_AGGREGATOR_PROMPT_V0_1 = (
    "Given the original task and the independent candidate answers, synthesize "
    "one final answer. Use the candidates as evidence; do not discuss the "
    "aggregation process unless required by the task."
)
S2_AGGREGATOR_USER_TEMPLATE_V0_1 = (
    "Original task:\n{task}\n\nIndependent candidate answers:\n{candidates}"
)
S2_PROPOSER_PROMPT_SHA256 = hashlib.sha256(
    S2_PROPOSER_PROMPT_V0_1.encode("utf-8")
).hexdigest()
S2_AGGREGATOR_PROMPT_SHA256 = hashlib.sha256(
    (
        S2_AGGREGATOR_PROMPT_V0_1
        + "\n"
        + S2_AGGREGATOR_USER_TEMPLATE_V0_1
    ).encode("utf-8")
).hexdigest()

MIN_PROPOSERS = 2
MAX_PROPOSERS = 8
DEFAULT_PROPOSER_COUNT = 3
PROPOSAL_EXECUTION = "sequential_v0"
_PENDING_EVENTS_KEY = "_s2_pending_events"

_COMMON_PROVIDER_FIELDS = {
    "type",
    "model",
    "temperature",
    "max_output_tokens",
    "seed",
}
_REAL_PROVIDER_FIELDS = _COMMON_PROVIDER_FIELDS | {
    "base_url",
    "api_key_env",
    "timeout_seconds",
    "max_retries",
}
_SECRET_VALUE_FIELDS = {"api_key", "token", "secret", "password"}


@dataclass(frozen=True)
class ProviderCallSpec:
    """One provider plus the exact neutral request controls for its role."""

    provider: LLMProvider
    temperature: float = 0.0
    max_output_tokens: int = 1024
    timeout_seconds: float = 30.0
    seed: int | None = None


def _as_call_spec(value: LLMProvider | ProviderCallSpec) -> ProviderCallSpec:
    if isinstance(value, ProviderCallSpec):
        return value
    return ProviderCallSpec(
        provider=value,
        temperature=float(getattr(value, "temperature", 0.0)),
        max_output_tokens=int(getattr(value, "max_output_tokens", 1024)),
        timeout_seconds=float(getattr(value, "timeout_seconds", 30.0)),
        seed=getattr(value, "seed", None),
    )


def _candidate_text(candidates: Sequence[str]) -> str:
    return "\n\n".join(
        f"Candidate {slot}:\n{content}" for slot, content in enumerate(candidates)
    )


def _content_evidence(slot: int, response: LLMResponse) -> dict[str, Any]:
    return {
        "slot": slot,
        "provider": response.provider,
        "model": response.model,
        "content_sha256": hashlib.sha256(response.content.encode("utf-8")).hexdigest(),
        "content_chars": len(response.content),
    }


def _successful_call_evidence(
    *,
    role: str,
    slot: int | None,
    spec: ProviderCallSpec,
    response: LLMResponse,
    observed_latency_ms: int,
) -> dict[str, Any]:
    input_tokens = response.input_tokens if response.usage_available else 0
    output_tokens = response.output_tokens if response.usage_available else 0
    total_tokens = response.total_tokens if response.usage_available else 0
    return {
        "role": role,
        "slot": slot,
        "status": "SUCCEEDED",
        "provider": response.provider,
        "model": response.model,
        "request_timeout_seconds": spec.timeout_seconds,
        "provider_latency_ms": response.latency_ms,
        "provider_latency_available": True,
        "observed_latency_ms": observed_latency_ms,
        "transport_retries": response.transport_retries,
        "usage_available": response.usage_available,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
    }


def _failed_call_evidence(
    *,
    role: str,
    slot: int | None,
    spec: ProviderCallSpec,
    error: ProviderError,
    observed_latency_ms: int,
) -> dict[str, Any]:
    return {
        "role": role,
        "slot": slot,
        "status": "FAILED",
        "provider": getattr(spec.provider, "name", "unknown"),
        "model": getattr(spec.provider, "model", "unknown"),
        "request_timeout_seconds": spec.timeout_seconds,
        "provider_latency_ms": 0,
        "provider_latency_available": False,
        "observed_latency_ms": observed_latency_ms,
        "transport_retries": error.transport_retries,
        "usage_available": False,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
        "error_kind": error.kind.value,
    }


def _aggregate_call_evidence(calls: Sequence[dict[str, Any]]) -> dict[str, Any]:
    usage_complete = bool(calls) and all(call["usage_available"] for call in calls)
    latency_complete = bool(calls) and all(
        call["provider_latency_available"] for call in calls
    )
    return {
        "per_call_evidence": [dict(call) for call in calls],
        "aggregate_usage_complete": usage_complete,
        "input_tokens": sum(int(call["input_tokens"]) for call in calls),
        "output_tokens": sum(int(call["output_tokens"]) for call in calls),
        "total_tokens": sum(int(call["total_tokens"]) for call in calls),
        "usage_available": usage_complete,
        "aggregate_provider_latency_ms": sum(
            int(call["provider_latency_ms"]) for call in calls
        ),
        "aggregate_provider_latency_complete": latency_complete,
        "provider_latency_ms": sum(
            int(call["provider_latency_ms"]) for call in calls
        ),
        "aggregate_observed_latency_ms": sum(
            int(call["observed_latency_ms"]) for call in calls
        ),
        "transport_retries_per_call": [
            int(call["transport_retries"]) for call in calls
        ],
        "transport_retries": sum(int(call["transport_retries"]) for call in calls),
    }


class S2ConventionalMoA:
    """N independent proposer calls followed by exactly one aggregator call."""

    SYSTEM_ID = S2_SYSTEM_ID

    def __init__(
        self,
        proposers: Sequence[LLMProvider | ProviderCallSpec],
        aggregator: LLMProvider | ProviderCallSpec,
        *,
        proposal_execution: str = PROPOSAL_EXECUTION,
    ) -> None:
        if not MIN_PROPOSERS <= len(proposers) <= MAX_PROPOSERS:
            raise ValueError(
                f"S2 proposer count must be in [{MIN_PROPOSERS}, {MAX_PROPOSERS}]"
            )
        if proposal_execution != PROPOSAL_EXECUTION:
            raise ValueError(f"unsupported S2 proposal_execution {proposal_execution!r}")
        self.proposers = tuple(_as_call_spec(value) for value in proposers)
        self.aggregator = _as_call_spec(aggregator)
        self.proposal_execution = proposal_execution

    def _base_metadata(
        self,
        calls: Sequence[dict[str, Any]],
        candidates: Sequence[dict[str, Any]],
        pending_events: list[dict[str, Any]],
        *,
        logical_proposer_calls: int,
        logical_aggregator_calls: int,
    ) -> dict[str, Any]:
        return {
            "system_id": S2_SYSTEM_ID,
            "proposer_count": len(self.proposers),
            "logical_proposer_calls": logical_proposer_calls,
            "logical_aggregator_calls": logical_aggregator_calls,
            "logical_model_calls": logical_proposer_calls
            + logical_aggregator_calls,
            "model_helper_calls": 0,
            "memory_reads": 0,
            "memory_writes": 0,
            "proposal_execution": self.proposal_execution,
            "proposer_providers": [
                getattr(spec.provider, "name", "unknown") for spec in self.proposers
            ],
            "proposer_models": [
                getattr(spec.provider, "model", "unknown") for spec in self.proposers
            ],
            "aggregator_provider": getattr(
                self.aggregator.provider, "name", "unknown"
            ),
            "aggregator_model": getattr(
                self.aggregator.provider, "model", "unknown"
            ),
            "proposer_prompt_version": S2_PROPOSER_PROMPT_VERSION,
            "proposer_prompt_sha256": S2_PROPOSER_PROMPT_SHA256,
            "aggregator_prompt_version": S2_AGGREGATOR_PROMPT_VERSION,
            "aggregator_prompt_sha256": S2_AGGREGATOR_PROMPT_SHA256,
            "candidate_evidence": [dict(candidate) for candidate in candidates],
            **_aggregate_call_evidence(calls),
            _PENDING_EVENTS_KEY: pending_events,
        }

    @staticmethod
    def _buffered_sink(
        pending_events: list[dict[str, Any]], role: str, slot: int | None
    ):
        def sink(kind: str, payload: dict[str, Any]) -> None:
            pending_events.append(
                {
                    "kind": kind,
                    "payload": {"s2_role": role, "proposer_slot": slot, **payload},
                }
            )

        return sink

    def run_episode(self, episode_input: EpisodeInput) -> EpisodeResult:
        task = _extract_task(episode_input.input)
        pending_events: list[dict[str, Any]] = []
        calls: list[dict[str, Any]] = []
        candidate_contents: list[str] = []
        candidates: list[dict[str, Any]] = []

        # Sequential by explicit P1.4 design.  Every proposer request contains
        # only the original task; no proposer can observe another's output.
        for slot, spec in enumerate(self.proposers):
            request = LLMRequest(
                model=getattr(spec.provider, "model", "unknown"),
                messages=[
                    LLMMessage(role="system", content=S2_PROPOSER_PROMPT_V0_1),
                    LLMMessage(role="user", content=task),
                ],
                temperature=spec.temperature,
                max_output_tokens=spec.max_output_tokens,
                timeout_seconds=spec.timeout_seconds,
                seed=spec.seed,
            )
            started = time.monotonic()
            try:
                response = spec.provider.generate(
                    request,
                    event_sink=self._buffered_sink(pending_events, "proposer", slot),
                )
            except ProviderError as exc:
                observed = int((time.monotonic() - started) * 1000)
                calls.append(
                    _failed_call_evidence(
                        role="proposer",
                        slot=slot,
                        spec=spec,
                        error=exc,
                        observed_latency_ms=observed,
                    )
                )
                pending_events.append(
                    {
                        "kind": "s2_call_failed",
                        "payload": {
                            "role": "proposer",
                            "slot": slot,
                            "error_kind": exc.kind.value,
                        },
                    }
                )
                return EpisodeResult(
                    output=None,
                    status="FAILED",
                    error=f"PROPOSER[{slot}] {exc.kind.value}: {exc.message}",
                    tool_events=[],
                    metadata={
                        **self._base_metadata(
                            calls,
                            candidates,
                            pending_events,
                            logical_proposer_calls=slot + 1,
                            logical_aggregator_calls=0,
                        ),
                        "failure_role": "proposer",
                        "failure_slot": slot,
                        "provider_error_kind": exc.kind.value,
                    },
                )

            observed = int((time.monotonic() - started) * 1000)
            calls.append(
                _successful_call_evidence(
                    role="proposer",
                    slot=slot,
                    spec=spec,
                    response=response,
                    observed_latency_ms=observed,
                )
            )
            candidate_contents.append(response.content)
            candidate = _content_evidence(slot, response)
            candidates.append(candidate)
            pending_events.append(
                {"kind": "s2_proposal_completed", "payload": dict(candidate)}
            )

        aggregator_request = LLMRequest(
            model=getattr(self.aggregator.provider, "model", "unknown"),
            messages=[
                LLMMessage(role="system", content=S2_AGGREGATOR_PROMPT_V0_1),
                LLMMessage(
                    role="user",
                    content=S2_AGGREGATOR_USER_TEMPLATE_V0_1.format(
                        task=task, candidates=_candidate_text(candidate_contents)
                    ),
                ),
            ],
            temperature=self.aggregator.temperature,
            max_output_tokens=self.aggregator.max_output_tokens,
            timeout_seconds=self.aggregator.timeout_seconds,
            seed=self.aggregator.seed,
        )
        pending_events.append(
            {
                "kind": "s2_aggregation_started",
                "payload": {"candidate_count": len(candidate_contents)},
            }
        )
        started = time.monotonic()
        try:
            aggregate_response = self.aggregator.provider.generate(
                aggregator_request,
                event_sink=self._buffered_sink(pending_events, "aggregator", None),
            )
        except ProviderError as exc:
            observed = int((time.monotonic() - started) * 1000)
            calls.append(
                _failed_call_evidence(
                    role="aggregator",
                    slot=None,
                    spec=self.aggregator,
                    error=exc,
                    observed_latency_ms=observed,
                )
            )
            pending_events.append(
                {
                    "kind": "s2_call_failed",
                    "payload": {
                        "role": "aggregator",
                        "slot": None,
                        "error_kind": exc.kind.value,
                    },
                }
            )
            return EpisodeResult(
                output=None,
                status="FAILED",
                error=f"AGGREGATOR {exc.kind.value}: {exc.message}",
                tool_events=[],
                metadata={
                    **self._base_metadata(
                        calls,
                        candidates,
                        pending_events,
                        logical_proposer_calls=len(self.proposers),
                        logical_aggregator_calls=1,
                    ),
                    "failure_role": "aggregator",
                    "failure_slot": None,
                    "provider_error_kind": exc.kind.value,
                },
            )

        observed = int((time.monotonic() - started) * 1000)
        calls.append(
            _successful_call_evidence(
                role="aggregator",
                slot=None,
                spec=self.aggregator,
                response=aggregate_response,
                observed_latency_ms=observed,
            )
        )
        final_evidence = {
            "provider": aggregate_response.provider,
            "model": aggregate_response.model,
            "content_sha256": hashlib.sha256(
                aggregate_response.content.encode("utf-8")
            ).hexdigest(),
            "content_chars": len(aggregate_response.content),
        }
        pending_events.append(
            {"kind": "s2_aggregation_completed", "payload": final_evidence}
        )
        return EpisodeResult(
            output={"answer": aggregate_response.content},
            status="SUCCEEDED",
            tool_events=[],
            metadata={
                **self._base_metadata(
                    calls,
                    candidates,
                    pending_events,
                    logical_proposer_calls=len(self.proposers),
                    logical_aggregator_calls=1,
                ),
                "finish_reason": aggregate_response.finish_reason,
                "provider_request_id": aggregate_response.provider_request_id,
                "final_answer_evidence": final_evidence,
            },
        )

    def finalize_episode_outcome(
        self,
        episode_input: EpisodeInput,
        result: EpisodeResult,
        outcome: str,
        event_log: EventLog,
    ) -> EpisodeResult:
        """Publish buffered evidence only after the outer runner accepts a result."""
        metadata = dict(result.metadata)
        pending_events = metadata.pop(_PENDING_EVENTS_KEY, [])
        for pending in pending_events:
            event_log.append(
                Event(
                    episode_id=episode_input.episode_id,
                    kind=str(pending["kind"]),
                    payload=dict(pending.get("payload", {})),
                )
            )
        result.metadata = metadata
        return result


def _normalize_provider(
    config: ExperimentConfig, raw: Any, *, location: str
) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValueError(f"S2 {location}.provider must be an object")
    forbidden = set(raw) & _SECRET_VALUE_FIELDS
    if forbidden:
        raise ValueError(
            f"S2 {location}.provider contains forbidden secret fields: {sorted(forbidden)}"
        )
    provider_type = raw.get("type", "fake")
    allowed = _REAL_PROVIDER_FIELDS if provider_type == "openai_compat" else _COMMON_PROVIDER_FIELDS
    unknown = set(raw) - allowed
    if unknown:
        raise ValueError(f"unknown S2 {location}.provider fields: {sorted(unknown)}")
    nested_config = config.model_copy(update={"metadata": {"provider": dict(raw)}})
    try:
        return validate_s0_provider_config(nested_config)
    except ValueError as exc:
        raise ValueError(str(exc).replace("S0 provider", f"S2 {location}.provider")) from exc


def validate_s2_config(config: ExperimentConfig) -> dict[str, Any]:
    """Validate all S2 roles without credentials, network, or provider creation."""
    if config.system_id != S2_SYSTEM_ID:
        raise ValueError(f"S2 validation requires system_id {S2_SYSTEM_ID!r}")
    raw_moa = (config.metadata or {}).get("moa")
    if not isinstance(raw_moa, dict):
        raise ValueError("S2 config metadata.moa must be an object")
    unknown_moa = set(raw_moa) - {
        "proposer_count",
        "proposers",
        "aggregator",
        "proposal_execution",
    }
    if unknown_moa:
        raise ValueError(f"unknown S2 metadata.moa fields: {sorted(unknown_moa)}")
    proposers = raw_moa.get("proposers")
    if not isinstance(proposers, list) or not proposers:
        raise ValueError("S2 metadata.moa.proposers must be a non-empty list")
    proposer_count = raw_moa.get("proposer_count", DEFAULT_PROPOSER_COUNT)
    if (
        isinstance(proposer_count, bool)
        or not isinstance(proposer_count, int)
        or not MIN_PROPOSERS <= proposer_count <= MAX_PROPOSERS
    ):
        raise ValueError(
            f"S2 proposer_count must be an integer in [{MIN_PROPOSERS}, {MAX_PROPOSERS}]"
        )
    if proposer_count != len(proposers):
        raise ValueError("S2 proposer_count must equal the number of proposer slots")
    execution = raw_moa.get("proposal_execution", PROPOSAL_EXECUTION)
    if execution != PROPOSAL_EXECUTION:
        raise ValueError(
            f"S2 proposal_execution must be {PROPOSAL_EXECUTION!r} in P1.4"
        )

    normalized_proposers: list[dict[str, Any]] = []
    for slot, wrapper in enumerate(proposers):
        if not isinstance(wrapper, dict) or set(wrapper) != {"provider"}:
            raise ValueError(
                f"S2 proposer slot {slot} must contain exactly one 'provider' object"
            )
        normalized_proposers.append(
            _normalize_provider(
                config, wrapper["provider"], location=f"proposer[{slot}]"
            )
        )
    aggregator = raw_moa.get("aggregator")
    if not isinstance(aggregator, dict) or set(aggregator) != {"provider"}:
        raise ValueError("S2 aggregator must contain exactly one 'provider' object")
    normalized_aggregator = _normalize_provider(
        config, aggregator["provider"], location="aggregator"
    )
    return {
        "proposer_count": proposer_count,
        "proposal_execution": execution,
        "proposers": normalized_proposers,
        "aggregator": normalized_aggregator,
    }


def _build_call_spec(spec: dict[str, Any]) -> ProviderCallSpec:
    if spec["type"] == "fake":
        provider: LLMProvider = FakeProvider(model=spec["model"])
    else:
        provider = OpenAICompatProvider(
            base_url=spec["base_url"],
            model=spec["model"],
            api_key_env=spec["api_key_env"],
            timeout_seconds=spec["timeout_seconds"],
            temperature=spec["temperature"],
            max_output_tokens=spec["max_output_tokens"],
            seed=spec["seed"],
            max_retries=spec["max_retries"],
        )
    return ProviderCallSpec(
        provider=provider,
        temperature=spec["temperature"],
        max_output_tokens=spec["max_output_tokens"],
        timeout_seconds=spec["timeout_seconds"],
        seed=spec["seed"],
    )


def build_s2(config: ExperimentConfig) -> S2ConventionalMoA:
    spec = validate_s2_config(config)
    return S2ConventionalMoA(
        [_build_call_spec(value) for value in spec["proposers"]],
        _build_call_spec(spec["aggregator"]),
        proposal_execution=spec["proposal_execution"],
    )


def s2_all_providers_fake(config: ExperimentConfig) -> bool:
    spec = validate_s2_config(config)
    return all(value["type"] == "fake" for value in spec["proposers"]) and spec[
        "aggregator"
    ]["type"] == "fake"


def s2_missing_credentials(config: ExperimentConfig) -> list[str]:
    """Return unique missing configured env-var names in stable role order."""
    spec = validate_s2_config(config)
    missing: list[str] = []
    for provider in [*spec["proposers"], spec["aggregator"]]:
        if provider["type"] != "openai_compat":
            continue
        env_name = provider["api_key_env"]
        if not os.environ.get(env_name) and env_name not in missing:
            missing.append(env_name)
    return missing


__all__ = [
    "S2_SYSTEM_ID",
    "S2_PROPOSER_PROMPT_VERSION",
    "S2_AGGREGATOR_PROMPT_VERSION",
    "S2_PROPOSER_PROMPT_V0_1",
    "S2_AGGREGATOR_PROMPT_V0_1",
    "S2_AGGREGATOR_USER_TEMPLATE_V0_1",
    "S2_PROPOSER_PROMPT_SHA256",
    "S2_AGGREGATOR_PROMPT_SHA256",
    "MIN_PROPOSERS",
    "MAX_PROPOSERS",
    "DEFAULT_PROPOSER_COUNT",
    "PROPOSAL_EXECUTION",
    "ProviderCallSpec",
    "S2ConventionalMoA",
    "validate_s2_config",
    "build_s2",
    "s2_all_providers_fake",
    "s2_missing_credentials",
]
