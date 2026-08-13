import copy
import json
import threading

import pytest

from aby.providers.base import ProviderErrorKind
from aby.runtime.bundle import ABYParallelRuntimeResult, LaneStatus, RuntimeStatus
from aby.runtime.parallel import ABYParallelRuntime
from tests.p1_6_support import (
    VALID_FRAMES,
    RoleAwareFakeProvider,
    build_runtime,
    runtime_config,
    runtime_providers,
    sample_snapshot,
)


def test_barrier_proves_all_three_lane_calls_are_in_flight_concurrently():
    barrier = threading.Barrier(3)
    providers = runtime_providers(
        A={"barrier": barrier}, B={"barrier": barrier}, Y={"barrier": barrier}
    )
    result = build_runtime(providers).run(sample_snapshot(), runtime_config())
    assert result.status is RuntimeStatus.SUCCEEDED
    assert result.logical_model_calls_total == 3
    assert [providers[lane].call_count for lane in ("A", "B", "Y")] == [1, 1, 1]
    assert [result.a_lane.status, result.b_lane.status, result.y_lane.status] == [
        LaneStatus.SUCCEEDED
    ] * 3


def test_y_request_comes_only_from_snapshot_and_never_fresh_a_b_outputs():
    a_payload = copy.deepcopy(VALID_FRAMES["A"])
    b_payload = copy.deepcopy(VALID_FRAMES["B"])
    a_payload["macro_state"].append("FRESH_A_SENTINEL")
    b_payload["candidate_actions"].append("FRESH_B_SENTINEL")
    providers = runtime_providers(
        A={"content": json.dumps(a_payload)},
        B={"content": json.dumps(b_payload)},
    )
    snapshot = sample_snapshot()
    result = build_runtime(providers).run(snapshot, runtime_config())
    assert result.status is RuntimeStatus.SUCCEEDED
    y_request = providers["Y"].requests[0]
    serialized_request = "\n".join(message.content for message in y_request.messages)
    assert y_request.metadata["snapshot_id"] == snapshot.snapshot_id
    assert "FRESH_A_SENTINEL" not in serialized_request
    assert "FRESH_B_SENTINEL" not in serialized_request


@pytest.mark.parametrize("failed_lane", ["A", "B", "Y"])
def test_any_lane_provider_failure_fails_closed_without_fallback_or_geometry(failed_lane):
    providers = runtime_providers(
        **{failed_lane: {"fail_with": ProviderErrorKind.NETWORK_ERROR}}
    )
    result = build_runtime(providers).run(sample_snapshot(), runtime_config(geometry=False))
    assert result.status is RuntimeStatus.FAILED
    assert result.semantic_geometry_bundle is None
    assert getattr(result, f"{failed_lane.lower()}_lane").status is LaneStatus.FAILED
    assert [providers[lane].call_count for lane in ("A", "B", "Y")] == [1, 1, 1]
    assert result.logical_model_calls_total == 3


@pytest.mark.parametrize("failed_lane", ["A", "B", "Y"])
def test_any_lane_malformed_json_counts_one_call_and_fails_without_repair(failed_lane):
    providers = runtime_providers(**{failed_lane: {"content": "not-json"}})
    result = build_runtime(providers).run(sample_snapshot(), runtime_config())
    failed = getattr(result, f"{failed_lane.lower()}_lane")
    assert result.status is RuntimeStatus.FAILED
    assert failed.failure.error_category == "INVALID_JSON"
    assert failed.failure.raw_content_sha256
    assert "not-json" not in result.model_dump_json()
    assert [providers[lane].call_count for lane in ("A", "B", "Y")] == [1, 1, 1]
    assert result.semantic_geometry_bundle is None


def test_aggregate_usage_is_truthful_when_one_lane_usage_is_unavailable():
    providers = runtime_providers(Y={"usage_available": False})
    result = build_runtime(providers).run(sample_snapshot(), runtime_config())
    assert result.status is RuntimeStatus.SUCCEEDED
    assert result.aggregate_usage_complete is False
    assert result.aggregate_input_tokens is None
    assert result.aggregate_output_tokens is None
    assert result.aggregate_total_tokens is None
    assert result.observed_token_share_by_lane is None


def test_frozen_runtime_result_is_json_round_trip_serializable():
    result = build_runtime(runtime_providers()).run(sample_snapshot(), runtime_config())
    restored = ABYParallelRuntimeResult.model_validate_json(result.model_dump_json())
    assert restored == result
    assert restored.runtime_semantic_fingerprint == result.runtime_semantic_fingerprint


def test_shared_provider_instance_is_rejected_before_concurrent_execution():
    shared = RoleAwareFakeProvider("A")
    with pytest.raises(ValueError, match="separately owned"):
        ABYParallelRuntime(a_provider=shared, b_provider=shared, y_provider=shared)
