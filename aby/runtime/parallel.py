"""Bounded true-concurrent P1.6 A/B/Y fan-out and deterministic join."""

from __future__ import annotations

import time
from concurrent.futures import Future, ThreadPoolExecutor

from ..lanes.a_layer import ALayer
from ..lanes.b_layer import BLayer
from ..lanes.y_layer import YLayer
from ..providers.base import LLMProvider
from ..semantic.bundle import SemanticGeometryBundle, build_semantic_geometry_bundle
from ..semantic.encoder import SharedEncoder
from ._canonical import canonical_sha256
from .bundle import (
    ABYParallelRuntimeConfig,
    ABYParallelRuntimeResult,
    ALaneExecutionResult,
    BLaneExecutionResult,
    CoordinatorFailure,
    LaneFailure,
    LaneStatus,
    ObservedTokenShareByLane,
    RuntimeStatus,
    YLaneExecutionResult,
    runtime_fingerprint_payload,
)
from .lane_events import merge_lane_events
from .snapshot import RuntimeSnapshot


class ABYParallelRuntime:
    """Coordinator owns fan-out, collection, canonical ordering, and handoff only."""

    def __init__(
        self,
        *,
        a_provider: LLMProvider,
        b_provider: LLMProvider,
        y_provider: LLMProvider,
        encoder: SharedEncoder | None = None,
    ) -> None:
        if len({id(a_provider), id(b_provider), id(y_provider)}) != 3:
            raise ValueError("P1.6 requires one separately owned provider instance per lane")
        self.a_lane = ALayer(a_provider)
        self.b_lane = BLayer(b_provider)
        self.y_lane = YLayer(y_provider)
        self.encoder = encoder

    def run(
        self,
        snapshot: RuntimeSnapshot,
        config: ABYParallelRuntimeConfig,
    ) -> ABYParallelRuntimeResult:
        started = time.monotonic()
        # Submit every independent snapshot-derived lane before waiting for any
        # result. No future receives another lane's fresh output.
        with ThreadPoolExecutor(max_workers=3, thread_name_prefix="aby-p1-6") as executor:
            a_future = executor.submit(self.a_lane.produce, snapshot, config.a_lane)
            b_future = executor.submit(self.b_lane.produce, snapshot, config.b_lane)
            y_future = executor.submit(self.y_lane.observe, snapshot, config.y_lane)
            a_result = self._settle_a(a_future, config)
            b_result = self._settle_b(b_future, config)
            y_result = self._settle_y(y_future, config)
        first_stage_wall_elapsed_ms = int((time.monotonic() - started) * 1000)

        lanes = (a_result, b_result, y_result)
        canonical_events = merge_lane_events(*(result.events for result in lanes))
        all_lanes_succeeded = all(
            result.status is LaneStatus.SUCCEEDED for result in lanes
        )

        geometry: SemanticGeometryBundle | None = None
        coordinator_failure: CoordinatorFailure | None = None
        if all_lanes_succeeded and config.semantic_geometry.enabled:
            if self.encoder is None:
                coordinator_failure = CoordinatorFailure(
                    error_category="SEMANTIC_GEOMETRY_ENCODER_REQUIRED"
                )
            else:
                try:
                    assert a_result.proposal is not None
                    assert b_result.proposal is not None
                    assert y_result.proposal is not None
                    geometry = build_semantic_geometry_bundle(
                        a_result.proposal.frame,
                        b_result.proposal.frame,
                        y_result.proposal.frame,
                        encoder=self.encoder,
                        k=config.semantic_geometry.atlas_k,
                        matches_per_source=(
                            config.semantic_geometry.matches_per_source
                        ),
                    )
                except Exception:
                    coordinator_failure = CoordinatorFailure(
                        error_category="SEMANTIC_GEOMETRY_HANDOFF_FAILED"
                    )
                    geometry = None

        status = (
            RuntimeStatus.SUCCEEDED
            if all_lanes_succeeded and coordinator_failure is None
            else RuntimeStatus.FAILED
        )
        usage_complete = all(result.usage_available for result in lanes)
        aggregate_input = sum(result.input_tokens for result in lanes) if usage_complete else None
        aggregate_output = sum(result.output_tokens for result in lanes) if usage_complete else None
        aggregate_total = sum(result.total_tokens for result in lanes) if usage_complete else None
        token_shares = None
        if usage_complete and aggregate_total:
            token_shares = ObservedTokenShareByLane(
                a_lane=a_result.total_tokens / aggregate_total,
                b_lane=b_result.total_tokens / aggregate_total,
                y_lane=y_result.total_tokens / aggregate_total,
            )

        fingerprint_payload = runtime_fingerprint_payload(
            snapshot_id=snapshot.snapshot_id,
            status=status,
            config=config,
            a_lane=a_result,
            b_lane=b_result,
            y_lane=y_result,
            coordinator_failure=coordinator_failure,
            semantic_geometry_bundle=geometry,
        )
        return ABYParallelRuntimeResult(
            snapshot_id=snapshot.snapshot_id,
            status=status,
            config=config,
            a_lane=a_result,
            b_lane=b_result,
            y_lane=y_result,
            aggregate_usage_complete=usage_complete,
            aggregate_input_tokens=aggregate_input,
            aggregate_output_tokens=aggregate_output,
            aggregate_total_tokens=aggregate_total,
            observed_token_share_by_lane=token_shares,
            transport_retries_total=sum(
                result.transport_retries for result in lanes
            ),
            canonical_lane_events=canonical_events,
            first_stage_wall_elapsed_ms=first_stage_wall_elapsed_ms,
            coordinator_failure=coordinator_failure,
            runtime_semantic_fingerprint=canonical_sha256(fingerprint_payload),
            semantic_geometry_bundle=geometry,
        )

    def _settle_a(
        self,
        future: Future[ALaneExecutionResult],
        config: ABYParallelRuntimeConfig,
    ) -> ALaneExecutionResult:
        try:
            return future.result()
        except Exception:
            return ALaneExecutionResult(
                status=LaneStatus.FAILED,
                provider=_provider_name(self.a_lane.provider),
                requested_model=config.a_lane.model,
                failure=LaneFailure(error_category="UNEXPECTED_A_WORKER_FAILURE"),
            )

    def _settle_b(
        self,
        future: Future[BLaneExecutionResult],
        config: ABYParallelRuntimeConfig,
    ) -> BLaneExecutionResult:
        try:
            return future.result()
        except Exception:
            return BLaneExecutionResult(
                status=LaneStatus.FAILED,
                provider=_provider_name(self.b_lane.provider),
                requested_model=config.b_lane.model,
                failure=LaneFailure(error_category="UNEXPECTED_B_WORKER_FAILURE"),
            )

    def _settle_y(
        self,
        future: Future[YLaneExecutionResult],
        config: ABYParallelRuntimeConfig,
    ) -> YLaneExecutionResult:
        try:
            return future.result()
        except Exception:
            return YLaneExecutionResult(
                status=LaneStatus.FAILED,
                provider=_provider_name(self.y_lane.provider),
                requested_model=config.y_lane.model,
                failure=LaneFailure(error_category="UNEXPECTED_Y_WORKER_FAILURE"),
            )


def _provider_name(provider: LLMProvider) -> str:
    return str(getattr(provider, "name", "unknown")) or "unknown"


__all__ = ["ABYParallelRuntime"]
