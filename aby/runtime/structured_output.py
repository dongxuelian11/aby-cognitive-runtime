"""Strict provider-neutral JSON-text parsing into the frozen P0 frame boundary."""

from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Literal

from pydantic import ValidationError

from ..contracts.frames import ActionFrame, DissipationFrame, MacroFrame

LANE_STRUCTURED_OUTPUT_PROTOCOL = "strict-json-text-v0.1"
NATIVE_PROVIDER_SCHEMA_ENFORCEMENT = False


class StructuredOutputErrorCode(str, Enum):
    INVALID_JSON = "INVALID_JSON"
    TOP_LEVEL_NOT_OBJECT = "TOP_LEVEL_NOT_OBJECT"
    FIELD_SET_MISMATCH = "FIELD_SET_MISMATCH"
    SCHEMA_VALIDATION_FAILED = "SCHEMA_VALIDATION_FAILED"


class StructuredOutputError(Exception):
    """Bounded parse failure that never includes raw model content."""

    def __init__(self, code: StructuredOutputErrorCode, raw_content: str) -> None:
        self.code = code
        self.raw_content_sha256 = hashlib.sha256(raw_content.encode("utf-8")).hexdigest()
        self.raw_content_chars = len(raw_content)
        self.protocol = LANE_STRUCTURED_OUTPUT_PROTOCOL
        super().__init__(f"{code.value}: strict lane output rejected")


_FRAME_TYPES = {
    "A": MacroFrame,
    "B": ActionFrame,
    "Y": DissipationFrame,
}


def _reject_non_json_constant(value: str) -> None:
    raise ValueError(f"non-JSON numeric constant {value}")


def parse_lane_frame(
    lane: Literal["A", "B", "Y"], raw_content: str
) -> MacroFrame | ActionFrame | DissipationFrame:
    """Parse exactly once with no repair, retry, helper model, or fallback."""

    try:
        payload = json.loads(raw_content, parse_constant=_reject_non_json_constant)
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        raise StructuredOutputError(
            StructuredOutputErrorCode.INVALID_JSON, raw_content
        ) from exc
    if not isinstance(payload, dict):
        raise StructuredOutputError(
            StructuredOutputErrorCode.TOP_LEVEL_NOT_OBJECT, raw_content
        )

    frame_type = _FRAME_TYPES[lane]
    expected_fields = set(frame_type.model_fields)
    if set(payload) != expected_fields:
        raise StructuredOutputError(
            StructuredOutputErrorCode.FIELD_SET_MISMATCH, raw_content
        )
    try:
        return frame_type.model_validate(payload, strict=True)
    except ValidationError as exc:
        raise StructuredOutputError(
            StructuredOutputErrorCode.SCHEMA_VALIDATION_FAILED, raw_content
        ) from exc


__all__ = [
    "LANE_STRUCTURED_OUTPUT_PROTOCOL",
    "NATIVE_PROVIDER_SCHEMA_ENFORCEMENT",
    "StructuredOutputErrorCode",
    "StructuredOutputError",
    "parse_lane_frame",
]
