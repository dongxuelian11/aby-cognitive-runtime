"""Lane-local provider event buffers and deterministic A-then-B-then-Y merge."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ._canonical import canonical_json, canonical_sha256

MAX_EVENT_PAYLOAD_CHARS = 4096
_FORBIDDEN_KEY_PARTS = ("api_key", "authorization", "password", "secret")


class LaneName(str, Enum):
    A = "A"
    B = "B"
    Y = "Y"


class LaneEvent(BaseModel):
    """Immutable event evidence; payload is a bounded canonical JSON object."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    lane: LaneName
    local_ordinal: int = Field(ge=0)
    kind: str = Field(min_length=1, max_length=128)
    payload: str = Field(max_length=MAX_EVENT_PAYLOAD_CHARS)


def _reject_secret_keys(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered = str(key).casefold()
            if any(part in lowered for part in _FORBIDDEN_KEY_PARTS):
                raise ValueError("lane event payload contains a forbidden secret-bearing key")
            _reject_secret_keys(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _reject_secret_keys(nested)


class LaneEventBuffer:
    """Mutable only inside its owning lane worker; never a shared EventLog."""

    def __init__(self, lane: LaneName) -> None:
        self.lane = lane
        self._events: list[LaneEvent] = []

    def emit(self, kind: str, payload: dict[str, Any]) -> None:
        _reject_secret_keys(payload)
        payload_json = canonical_json(payload)
        if len(payload_json) > MAX_EVENT_PAYLOAD_CHARS:
            raise ValueError("lane event payload exceeds bounded size")
        self._events.append(
            LaneEvent(
                lane=self.lane,
                local_ordinal=len(self._events),
                kind=kind,
                payload=payload_json,
            )
        )

    @property
    def events(self) -> tuple[LaneEvent, ...]:
        return tuple(self._events)


def merge_lane_events(
    a_events: tuple[LaneEvent, ...],
    b_events: tuple[LaneEvent, ...],
    y_events: tuple[LaneEvent, ...],
) -> tuple[LaneEvent, ...]:
    groups = ((LaneName.A, a_events), (LaneName.B, b_events), (LaneName.Y, y_events))
    merged: list[LaneEvent] = []
    for expected_lane, events in groups:
        ordered = sorted(events, key=lambda event: event.local_ordinal)
        if any(event.lane is not expected_lane for event in ordered):
            raise ValueError("lane-local event buffer contains a cross-lane event")
        if [event.local_ordinal for event in ordered] != list(range(len(ordered))):
            raise ValueError("lane-local event ordinals must be unique and contiguous")
        merged.extend(ordered)
    return tuple(merged)


def lane_event_order_fingerprint(events: tuple[LaneEvent, ...]) -> str:
    return canonical_sha256(
        [
            {"lane": event.lane.value, "local_ordinal": event.local_ordinal, "kind": event.kind}
            for event in events
        ]
    )


__all__ = [
    "LaneName",
    "LaneEvent",
    "LaneEventBuffer",
    "merge_lane_events",
    "lane_event_order_fingerprint",
]
