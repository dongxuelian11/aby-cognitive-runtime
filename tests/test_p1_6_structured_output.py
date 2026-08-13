import json

import pytest

from aby.contracts.frames import ActionFrame, DissipationFrame, MacroFrame
from aby.runtime.structured_output import (
    LANE_STRUCTURED_OUTPUT_PROTOCOL,
    StructuredOutputError,
    StructuredOutputErrorCode,
    parse_lane_frame,
)
from tests.p1_6_support import VALID_FRAMES


@pytest.mark.parametrize(
    ("lane", "frame_type"),
    [("A", MacroFrame), ("B", ActionFrame), ("Y", DissipationFrame)],
)
def test_valid_exact_json_object_parses_to_frozen_p0_contract(lane, frame_type):
    frame = parse_lane_frame(lane, json.dumps(VALID_FRAMES[lane]))
    assert type(frame) is frame_type


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        ("not json", StructuredOutputErrorCode.INVALID_JSON),
        ("```json\n{}\n```", StructuredOutputErrorCode.INVALID_JSON),
        ("[]", StructuredOutputErrorCode.TOP_LEVEL_NOT_OBJECT),
        ("NaN", StructuredOutputErrorCode.INVALID_JSON),
    ],
)
def test_invalid_json_shapes_fail_closed_without_repair(raw, code):
    with pytest.raises(StructuredOutputError) as caught:
        parse_lane_frame("A", raw)
    assert caught.value.code is code
    assert caught.value.protocol == LANE_STRUCTURED_OUTPUT_PROTOCOL
    assert raw not in str(caught.value)


@pytest.mark.parametrize("mutation", ["missing", "extra", "wrong_type", "bounds"])
def test_missing_extra_wrong_type_and_bounds_are_rejected(mutation):
    payload = dict(VALID_FRAMES["Y"])
    expected = StructuredOutputErrorCode.SCHEMA_VALIDATION_FAILED
    if mutation == "missing":
        payload.pop("conflicts")
        expected = StructuredOutputErrorCode.FIELD_SET_MISMATCH
    elif mutation == "extra":
        payload["unexpected"] = True
        expected = StructuredOutputErrorCode.FIELD_SET_MISMATCH
    elif mutation == "wrong_type":
        payload["conflicts"] = "not-a-list"
    else:
        payload["estimated_y"] = 1.1
    raw = json.dumps(payload)
    with pytest.raises(StructuredOutputError) as caught:
        parse_lane_frame("Y", raw)
    assert caught.value.code is expected
    assert caught.value.raw_content_chars == len(raw)
    assert len(caught.value.raw_content_sha256) == 64
    assert raw not in repr(caught.value)
