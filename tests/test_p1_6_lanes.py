import hashlib

from aby.contracts.frames import ActionFrame, DissipationFrame, MacroFrame
from aby.lanes import ALayer, BLayer, YLayer
from aby.lanes.base import (
    A_LANE_PROMPT,
    A_LANE_PROMPT_SHA256,
    A_LANE_PROMPT_VERSION,
    B_LANE_PROMPT,
    B_LANE_PROMPT_SHA256,
    B_LANE_PROMPT_VERSION,
    Y_LANE_PROMPT,
    Y_LANE_PROMPT_SHA256,
    Y_LANE_PROMPT_VERSION,
)
from aby.runtime.bundle import LaneGenerationConfig, LaneStatus
from tests.p1_6_support import RoleAwareFakeProvider, sample_snapshot


def test_fixed_prompt_versions_hashes_and_role_doctrine():
    assert (A_LANE_PROMPT_VERSION, B_LANE_PROMPT_VERSION, Y_LANE_PROMPT_VERSION) == (
        "a-lane-v0.1", "b-lane-v0.1", "y-lane-v0.1"
    )
    assert A_LANE_PROMPT_SHA256 == hashlib.sha256(A_LANE_PROMPT.encode()).hexdigest()
    assert B_LANE_PROMPT_SHA256 == hashlib.sha256(B_LANE_PROMPT.encode()).hexdigest()
    assert Y_LANE_PROMPT_SHA256 == hashlib.sha256(Y_LANE_PROMPT.encode()).hexdigest()
    assert "not a third answer generator" in Y_LANE_PROMPT
    assert "do not propose executable actions" in Y_LANE_PROMPT.casefold()
    assert "prediction, not observed y" in Y_LANE_PROMPT
    assert "non-executable intents" in B_LANE_PROMPT


def test_live_lanes_make_one_call_and_return_only_their_p0_frame_types():
    snapshot = sample_snapshot()
    generation = LaneGenerationConfig(model="requested")
    providers = {lane: RoleAwareFakeProvider(lane) for lane in ("A", "B", "Y")}
    a = ALayer(providers["A"]).produce(snapshot, generation)
    b = BLayer(providers["B"]).produce(snapshot, generation)
    y = YLayer(providers["Y"]).observe(snapshot, generation)
    assert [a.status, b.status, y.status] == [LaneStatus.SUCCEEDED] * 3
    assert type(a.proposal.frame) is MacroFrame
    assert type(b.proposal.frame) is ActionFrame
    assert type(y.proposal.frame) is DissipationFrame
    assert [providers[lane].call_count for lane in ("A", "B", "Y")] == [1, 1, 1]
    assert [a.logical_model_calls, b.logical_model_calls, y.logical_model_calls] == [1, 1, 1]
    assert b.proposal.frame.tool_requests == ["tool intent only"]
    assert y.proposal.frame.estimated_y == 0.4
    for provider in providers.values():
        metadata = provider.requests[0].metadata
        assert metadata["snapshot_id"] == snapshot.snapshot_id
        assert metadata["structured_output_protocol"] == "strict-json-text-v0.1"
        assert metadata["native_provider_schema_enforcement"] is False
