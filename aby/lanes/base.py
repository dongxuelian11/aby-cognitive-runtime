"""Shared P1.6 lane mechanics: one provider call, strict parse, local evidence."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from ..contracts.frames import ActionFrame, DissipationFrame, MacroFrame
from ..providers.base import LLMMessage, LLMProvider, LLMRequest, LLMResponse, ProviderError
from ..runtime._canonical import canonical_sha256
from ..runtime.bundle import LaneFailure, LaneGenerationConfig
from ..runtime.lane_events import LaneEvent, LaneEventBuffer, LaneName
from ..runtime.snapshot import RuntimeSnapshot, project_snapshot
from ..runtime.structured_output import (
    LANE_STRUCTURED_OUTPUT_PROTOCOL,
    StructuredOutputError,
    parse_lane_frame,
)

A_LANE_PROMPT_VERSION = "a-lane-v0.1"
B_LANE_PROMPT_VERSION = "b-lane-v0.1"
Y_LANE_PROMPT_VERSION = "y-lane-v0.1"

A_LANE_PROMPT = """You are ABY lane A: Macro Boundary / Continuity.
Use only the accepted immutable snapshot projection. Produce MacroFrame semantics only: global goals, constraints, accepted facts/state, history, continuity risks, and candidate macro interpretations. Do not primarily answer the user, propose executable actions, or invent missing authority. Do not provide chain-of-thought.
Return only one strict JSON object with exactly these keys and no markdown fence: macro_state, relevant_history, active_constraints, long_term_goals, continuity_risks, candidate_interpretations, confidence, evidence_refs. Every list value must be an array of strings and confidence must be a number in [0,1]."""

B_LANE_PROMPT = """You are ABY lane B: Micro Direction / Action.
Use only the accepted immutable snapshot projection. Produce ActionFrame semantics only: current intent, local plan, candidate action intents, tool requests as non-executable intents, expected result, and local uncertainties. Do not redefine long-term goals or execute tools. Do not provide chain-of-thought.
Return only one strict JSON object with exactly these keys and no markdown fence: current_intent, local_plan, candidate_actions, tool_requests, expected_result, local_uncertainties, confidence, evidence_refs. String fields must be strings, list fields must be arrays of strings, and confidence must be a number in [0,1]."""

Y_LANE_PROMPT = """You are ABY lane Y: Dissipation Field.
Use only the accepted immutable snapshot projection. You are not a third answer generator. You do not propose executable actions. recommended_resolution_targets identify where dissipation should be examined, not actions to execute. estimated_y is a prediction, not observed y. Identify only conflicts, uncertainties, goal drift, memory/factual mismatch, redundancy, rework risk, context drift, unresolved tension, predicted estimated_y, and examination targets. Do not provide chain-of-thought.
Return only one strict JSON object with exactly these keys and no markdown fence: conflicts, uncertainties, goal_drift, memory_mismatch, factual_mismatch, redundancy, rework_risk, context_drift, unresolved_tension, estimated_y, confidence, recommended_resolution_targets. Every list value must be an array of strings; estimated_y and confidence must be numbers in [0,1]."""


def prompt_sha256(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


A_LANE_PROMPT_SHA256 = prompt_sha256(A_LANE_PROMPT)
B_LANE_PROMPT_SHA256 = prompt_sha256(B_LANE_PROMPT)
Y_LANE_PROMPT_SHA256 = prompt_sha256(Y_LANE_PROMPT)


@dataclass(frozen=True)
class RawLaneExecution:
    lane: LaneName
    provider_name: str
    requested_model: str
    frame: MacroFrame | ActionFrame | DissipationFrame | None
    response: LLMResponse | None
    failure: LaneFailure | None
    events: tuple[LaneEvent, ...]
    raw_content_sha256: str | None
    raw_content_chars: int | None
    transport_retries: int


class BaseLiveLane:
    lane: LaneName
    prompt: str
    prompt_version: str
    prompt_hash: str

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    def _execute(
        self, snapshot: RuntimeSnapshot, generation: LaneGenerationConfig
    ) -> RawLaneExecution:
        buffer = LaneEventBuffer(self.lane)
        response: LLMResponse | None = None
        provider_name = str(getattr(self.provider, "name", "unknown")) or "unknown"
        projection = project_snapshot(snapshot, self.lane.value)
        request = LLMRequest(
            model=generation.model,
            messages=[
                LLMMessage(role="system", content=self.prompt),
                LLMMessage(role="user", content=projection.canonical_json()),
            ],
            temperature=generation.temperature,
            max_output_tokens=generation.max_output_tokens,
            timeout_seconds=generation.timeout_seconds,
            seed=generation.seed,
            metadata={
                "lane": self.lane.value,
                "snapshot_id": snapshot.snapshot_id,
                "snapshot_schema_version": snapshot.snapshot_schema_version,
                "prompt_version": self.prompt_version,
                "prompt_sha256": self.prompt_hash,
                "structured_output_protocol": LANE_STRUCTURED_OUTPUT_PROTOCOL,
                "native_provider_schema_enforcement": False,
            },
        )
        try:
            # Exactly one logical model call. Provider-internal transport retries
            # remain inside this call and are reported separately.
            response = self.provider.generate(request, event_sink=buffer.emit)
            raw_hash = hashlib.sha256(response.content.encode("utf-8")).hexdigest()
            frame = parse_lane_frame(self.lane.value, response.content)
            return RawLaneExecution(
                lane=self.lane,
                provider_name=response.provider,
                requested_model=generation.model,
                frame=frame,
                response=response,
                failure=None,
                events=buffer.events,
                raw_content_sha256=raw_hash,
                raw_content_chars=len(response.content),
                transport_retries=response.transport_retries,
            )
        except StructuredOutputError as exc:
            return RawLaneExecution(
                lane=self.lane,
                provider_name=response.provider if response else provider_name,
                requested_model=generation.model,
                frame=None,
                response=response,
                failure=LaneFailure(
                    error_category=exc.code.value,
                    parser_protocol=exc.protocol,
                    raw_content_sha256=exc.raw_content_sha256,
                    raw_content_chars=exc.raw_content_chars,
                ),
                events=buffer.events,
                raw_content_sha256=exc.raw_content_sha256,
                raw_content_chars=exc.raw_content_chars,
                transport_retries=response.transport_retries if response else 0,
            )
        except ProviderError as exc:
            return RawLaneExecution(
                lane=self.lane,
                provider_name=provider_name,
                requested_model=generation.model,
                frame=None,
                response=None,
                failure=LaneFailure(error_category=exc.kind.value),
                events=buffer.events,
                raw_content_sha256=None,
                raw_content_chars=None,
                transport_retries=exc.transport_retries,
            )
        except Exception:
            return RawLaneExecution(
                lane=self.lane,
                provider_name=provider_name,
                requested_model=generation.model,
                frame=None,
                response=response,
                failure=LaneFailure(error_category="UNEXPECTED_PROVIDER_OR_LANE_ERROR"),
                events=buffer.events,
                raw_content_sha256=None,
                raw_content_chars=None,
                transport_retries=response.transport_retries if response else 0,
            )


def proposal_common(
    raw: RawLaneExecution,
    *,
    snapshot: RuntimeSnapshot,
    generation: LaneGenerationConfig,
    prompt_version: str,
    prompt_hash: str,
) -> dict[str, object]:
    if raw.response is None or raw.frame is None or raw.failure is not None:
        raise ValueError("successful proposal construction requires parsed response evidence")
    stable_payload = {
        "lane": raw.lane.value,
        "snapshot_id": snapshot.snapshot_id,
        "provider": raw.response.provider,
        "model": raw.response.model,
        "prompt_version": prompt_version,
        "prompt_sha256": prompt_hash,
        "structured_output_protocol": LANE_STRUCTURED_OUTPUT_PROTOCOL,
        "native_provider_schema_enforcement": False,
        "generation_config": generation.model_dump(mode="json"),
        "frame": raw.frame.model_dump(mode="json"),
    }
    return {
        "snapshot_id": snapshot.snapshot_id,
        "provider": raw.response.provider,
        "model": raw.response.model,
        "prompt_version": prompt_version,
        "prompt_sha256": prompt_hash,
        "raw_content_sha256": raw.raw_content_sha256,
        "raw_content_chars": raw.raw_content_chars,
        "usage_available": raw.response.usage_available,
        "input_tokens": raw.response.input_tokens,
        "output_tokens": raw.response.output_tokens,
        "total_tokens": raw.response.total_tokens,
        "provider_latency_ms": raw.response.latency_ms,
        "transport_retries": raw.response.transport_retries,
        "generation_config": generation,
        "proposal_fingerprint": canonical_sha256(stable_payload),
    }


def result_usage(raw: RawLaneExecution) -> dict[str, object]:
    response = raw.response
    return {
        "provider": raw.provider_name,
        "requested_model": raw.requested_model,
        "usage_available": response.usage_available if response else False,
        "input_tokens": response.input_tokens if response else 0,
        "output_tokens": response.output_tokens if response else 0,
        "total_tokens": response.total_tokens if response else 0,
        "transport_retries": raw.transport_retries,
        "events": raw.events,
    }


__all__ = [
    "A_LANE_PROMPT_VERSION",
    "B_LANE_PROMPT_VERSION",
    "Y_LANE_PROMPT_VERSION",
    "A_LANE_PROMPT",
    "B_LANE_PROMPT",
    "Y_LANE_PROMPT",
    "A_LANE_PROMPT_SHA256",
    "B_LANE_PROMPT_SHA256",
    "Y_LANE_PROMPT_SHA256",
    "BaseLiveLane",
    "RawLaneExecution",
    "proposal_common",
    "result_usage",
]
