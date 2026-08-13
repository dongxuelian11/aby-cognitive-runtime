"""Frozen, serializable P1.6 lane evidence and parallel runtime result models."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..contracts.frames import ActionFrame, DissipationFrame, MacroFrame
from ..semantic.atlas import MAX_ATLAS_K
from ..semantic.bundle import SemanticGeometryBundle
from ..semantic.matcher import MAX_MATCHES_PER_SOURCE
from ._canonical import canonical_sha256
from .lane_events import LaneEvent, LaneName, merge_lane_events
from .structured_output import LANE_STRUCTURED_OUTPUT_PROTOCOL

ABY_PARALLEL_RUNTIME_SCHEMA_VERSION = "p1.6-parallel-runtime-v0.1"


class RuntimeStatus(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class LaneStatus(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class LaneGenerationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model: str = Field(min_length=1)
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    max_output_tokens: int = Field(default=1024, ge=1)
    timeout_seconds: float = Field(default=30.0, gt=0.0)
    seed: int | None = None


class SemanticGeometryRuntimeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: bool = False
    atlas_k: int = Field(default=3, ge=1, le=MAX_ATLAS_K)
    matches_per_source: int = Field(default=2, ge=1, le=MAX_MATCHES_PER_SOURCE)


class ABYParallelRuntimeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    runtime_schema_version: Literal[
        "p1.6-parallel-runtime-v0.1"
    ] = ABY_PARALLEL_RUNTIME_SCHEMA_VERSION
    a_lane: LaneGenerationConfig
    b_lane: LaneGenerationConfig
    y_lane: LaneGenerationConfig
    semantic_geometry: SemanticGeometryRuntimeConfig = SemanticGeometryRuntimeConfig()


class LaneFailure(BaseModel):
    """Normalized, bounded failure evidence; never carries raw model output."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    error_category: str = Field(min_length=1, max_length=128)
    parser_protocol: str | None = None
    raw_content_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    raw_content_chars: int | None = Field(default=None, ge=0)


class _LaneProposalBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshot_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    prompt_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    structured_output_protocol: Literal[
        "strict-json-text-v0.1"
    ] = LANE_STRUCTURED_OUTPUT_PROTOCOL
    structured_output_mode: Literal[
        "strict-json-text-v0.1"
    ] = LANE_STRUCTURED_OUTPUT_PROTOCOL
    native_provider_schema_enforcement: Literal[False] = False
    raw_content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_content_chars: int = Field(ge=0)
    logical_model_calls: Literal[1] = 1
    usage_available: bool
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)
    provider_latency_ms: int = Field(ge=0)
    transport_retries: int = Field(ge=0)
    generation_config: LaneGenerationConfig
    proposal_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    def fingerprint_payload(self) -> dict[str, object]:
        return {
            "lane": self.lane,
            "snapshot_id": self.snapshot_id,
            "provider": self.provider,
            "model": self.model,
            "prompt_version": self.prompt_version,
            "prompt_sha256": self.prompt_sha256,
            "structured_output_protocol": self.structured_output_protocol,
            "native_provider_schema_enforcement": self.native_provider_schema_enforcement,
            "generation_config": self.generation_config.model_dump(mode="json"),
            "frame": self.frame.model_dump(mode="json"),
        }

    @model_validator(mode="after")
    def _fingerprint_must_match(self):
        if self.proposal_fingerprint != canonical_sha256(self.fingerprint_payload()):
            raise ValueError("proposal_fingerprint does not match stable proposal content")
        return self


class AProposal(_LaneProposalBase):
    lane: Literal["A"] = "A"
    frame: MacroFrame


class BProposal(_LaneProposalBase):
    lane: Literal["B"] = "B"
    frame: ActionFrame


class YProposal(_LaneProposalBase):
    lane: Literal["Y"] = "Y"
    frame: DissipationFrame


class _LaneExecutionResultBase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: LaneStatus
    provider: str = Field(min_length=1)
    requested_model: str = Field(min_length=1)
    logical_model_calls: Literal[1] = 1
    usage_available: bool = False
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    transport_retries: int = Field(default=0, ge=0)
    events: tuple[LaneEvent, ...] = ()
    failure: LaneFailure | None = None

    @model_validator(mode="after")
    def _event_lane_must_match(self):
        if any(event.lane.value != self.lane for event in self.events):
            raise ValueError("lane result contains cross-lane event evidence")
        return self


class ALaneExecutionResult(_LaneExecutionResultBase):
    lane: Literal["A"] = "A"
    proposal: AProposal | None = None

    @model_validator(mode="after")
    def _status_payload_consistency(self):
        _validate_lane_status(self)
        return self


class BLaneExecutionResult(_LaneExecutionResultBase):
    lane: Literal["B"] = "B"
    proposal: BProposal | None = None

    @model_validator(mode="after")
    def _status_payload_consistency(self):
        _validate_lane_status(self)
        return self


class YLaneExecutionResult(_LaneExecutionResultBase):
    lane: Literal["Y"] = "Y"
    proposal: YProposal | None = None

    @model_validator(mode="after")
    def _status_payload_consistency(self):
        _validate_lane_status(self)
        return self


def _validate_lane_status(result) -> None:
    if result.status is LaneStatus.SUCCEEDED and (
        result.proposal is None or result.failure is not None
    ):
        raise ValueError("successful lane requires one proposal and no failure")
    if result.status is LaneStatus.FAILED and (
        result.proposal is not None or result.failure is None
    ):
        raise ValueError("failed lane requires one failure and no proposal")
    if result.proposal is not None:
        proposal = result.proposal
        if result.provider != proposal.provider:
            raise ValueError("lane provider identity must match proposal evidence")
        if result.requested_model != proposal.generation_config.model:
            raise ValueError("lane requested model must match proposal generation config")
        if (
            result.usage_available,
            result.input_tokens,
            result.output_tokens,
            result.total_tokens,
            result.transport_retries,
        ) != (
            proposal.usage_available,
            proposal.input_tokens,
            proposal.output_tokens,
            proposal.total_tokens,
            proposal.transport_retries,
        ):
            raise ValueError("lane usage/retry evidence must match successful proposal")


class CoordinatorFailure(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    error_category: str = Field(min_length=1, max_length=128)


class ObservedTokenShareByLane(BaseModel):
    """Compute evidence only; these fields are not measured lowercase a/b/y."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    a_lane: float = Field(ge=0.0, le=1.0)
    b_lane: float = Field(ge=0.0, le=1.0)
    y_lane: float = Field(ge=0.0, le=1.0)


def runtime_fingerprint_payload(
    *,
    snapshot_id: str,
    status: RuntimeStatus,
    config: ABYParallelRuntimeConfig,
    a_lane: ALaneExecutionResult,
    b_lane: BLaneExecutionResult,
    y_lane: YLaneExecutionResult,
    coordinator_failure: CoordinatorFailure | None,
    semantic_geometry_bundle: SemanticGeometryBundle | None,
) -> dict[str, object]:
    return {
        "runtime_schema_version": ABY_PARALLEL_RUNTIME_SCHEMA_VERSION,
        "snapshot_id": snapshot_id,
        "status": status.value,
        "config": config.model_dump(mode="json"),
        "lanes": {
            result.lane: {
                "provider": result.provider,
                "requested_model": result.requested_model,
                "proposal_fingerprint": (
                    result.proposal.proposal_fingerprint if result.proposal else None
                ),
                "failure_category": (
                    result.failure.error_category if result.failure else None
                ),
            }
            for result in (a_lane, b_lane, y_lane)
        },
        "coordinator_failure": (
            coordinator_failure.error_category if coordinator_failure else None
        ),
        "semantic_geometry_bundle_fingerprint": (
            semantic_geometry_bundle.bundle_fingerprint
            if semantic_geometry_bundle
            else None
        ),
    }


class ABYParallelRuntimeResult(BaseModel):
    """No authority mutation or Resolver output exists in this P1.6 bundle."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    runtime_schema_version: Literal[
        "p1.6-parallel-runtime-v0.1"
    ] = ABY_PARALLEL_RUNTIME_SCHEMA_VERSION
    snapshot_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: RuntimeStatus
    config: ABYParallelRuntimeConfig
    a_lane: ALaneExecutionResult
    b_lane: BLaneExecutionResult
    y_lane: YLaneExecutionResult
    logical_model_calls_total: Literal[3] = 3
    aggregate_usage_complete: bool
    aggregate_input_tokens: int | None = Field(default=None, ge=0)
    aggregate_output_tokens: int | None = Field(default=None, ge=0)
    aggregate_total_tokens: int | None = Field(default=None, ge=0)
    observed_token_share_by_lane: ObservedTokenShareByLane | None = None
    transport_retries_total: int = Field(ge=0)
    canonical_lane_events: tuple[LaneEvent, ...]
    first_stage_wall_elapsed_ms: int = Field(ge=0)
    coordinator_failure: CoordinatorFailure | None = None
    runtime_semantic_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    semantic_geometry_bundle: SemanticGeometryBundle | None = None

    def fingerprint_payload(self) -> dict[str, object]:
        return runtime_fingerprint_payload(
            snapshot_id=self.snapshot_id,
            status=self.status,
            config=self.config,
            a_lane=self.a_lane,
            b_lane=self.b_lane,
            y_lane=self.y_lane,
            coordinator_failure=self.coordinator_failure,
            semantic_geometry_bundle=self.semantic_geometry_bundle,
        )

    @model_validator(mode="after")
    def _integrity_must_hold(self):
        lanes = (self.a_lane, self.b_lane, self.y_lane)
        for result, generation in zip(
            lanes,
            (self.config.a_lane, self.config.b_lane, self.config.y_lane),
            strict=True,
        ):
            if result.requested_model != generation.model:
                raise ValueError("lane requested model must match runtime config")
            if result.proposal is not None:
                if result.proposal.snapshot_id != self.snapshot_id:
                    raise ValueError("every lane proposal must bind the runtime snapshot")
                if result.proposal.generation_config != generation:
                    raise ValueError("proposal generation controls must match runtime config")
        expected_events = merge_lane_events(*(result.events for result in lanes))
        if self.canonical_lane_events != expected_events:
            raise ValueError("canonical events must be deterministic A-then-B-then-Y merge")
        if self.transport_retries_total != sum(
            result.transport_retries for result in lanes
        ):
            raise ValueError("transport retry aggregate does not match lane evidence")

        usage_complete = all(result.usage_available for result in lanes)
        if self.aggregate_usage_complete != usage_complete:
            raise ValueError("aggregate_usage_complete must reflect all lane usage")
        totals = (
            sum(result.input_tokens for result in lanes),
            sum(result.output_tokens for result in lanes),
            sum(result.total_tokens for result in lanes),
        )
        aggregate_values = (
            self.aggregate_input_tokens,
            self.aggregate_output_tokens,
            self.aggregate_total_tokens,
        )
        if usage_complete and aggregate_values != totals:
            raise ValueError("complete aggregate token totals must equal lane totals")
        if not usage_complete and any(value is not None for value in aggregate_values):
            raise ValueError("incomplete usage must not fabricate aggregate token totals")
        if not usage_complete and self.observed_token_share_by_lane is not None:
            raise ValueError("incomplete usage must not expose observed token shares")
        if usage_complete and totals[2] == 0 and self.observed_token_share_by_lane is not None:
            raise ValueError("zero total tokens have no defined observed token shares")
        if usage_complete and totals[2] > 0:
            expected_shares = ObservedTokenShareByLane(
                a_lane=self.a_lane.total_tokens / totals[2],
                b_lane=self.b_lane.total_tokens / totals[2],
                y_lane=self.y_lane.total_tokens / totals[2],
            )
            if self.observed_token_share_by_lane != expected_shares:
                raise ValueError("observed token shares must equal complete lane evidence")

        all_succeeded = all(result.status is LaneStatus.SUCCEEDED for result in lanes)
        if self.status is RuntimeStatus.SUCCEEDED:
            if not all_succeeded or self.coordinator_failure is not None:
                raise ValueError("successful runtime requires all lanes and coordinator success")
            if self.config.semantic_geometry.enabled != (
                self.semantic_geometry_bundle is not None
            ):
                raise ValueError("geometry bundle presence must follow enabled successful handoff")
            if self.semantic_geometry_bundle is not None and (
                self.semantic_geometry_bundle.k != self.config.semantic_geometry.atlas_k
                or self.semantic_geometry_bundle.matches_per_source
                != self.config.semantic_geometry.matches_per_source
            ):
                raise ValueError("geometry evidence must match runtime handoff config")
        else:
            if all_succeeded and self.coordinator_failure is None:
                raise ValueError("failed runtime requires lane or coordinator failure evidence")
            if self.semantic_geometry_bundle is not None:
                raise ValueError("failed runtime must not contain semantic geometry")

        expected_fingerprint = canonical_sha256(self.fingerprint_payload())
        if self.runtime_semantic_fingerprint != expected_fingerprint:
            raise ValueError("runtime semantic fingerprint does not match stable evidence")
        return self


def proposal_fingerprint(payload: dict[str, object]) -> str:
    return canonical_sha256(payload)


__all__ = [
    "ABY_PARALLEL_RUNTIME_SCHEMA_VERSION",
    "RuntimeStatus",
    "LaneStatus",
    "LaneGenerationConfig",
    "SemanticGeometryRuntimeConfig",
    "ABYParallelRuntimeConfig",
    "LaneFailure",
    "AProposal",
    "BProposal",
    "YProposal",
    "ALaneExecutionResult",
    "BLaneExecutionResult",
    "YLaneExecutionResult",
    "CoordinatorFailure",
    "ObservedTokenShareByLane",
    "ABYParallelRuntimeResult",
    "proposal_fingerprint",
    "runtime_fingerprint_payload",
]
