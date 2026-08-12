"""Neutral system-under-test interface and deterministic offline systems (P1.1).

Architecture-neutral by design:
- no ABY lane frame contracts (the frozen Macro/Action/Dissipation frames)
  are involved anywhere in this module;
- no model calls, no network, no memory backends;
- the interface is shared by all future baselines S0/S1/S2/S3.

Offline systems registered in ``OFFLINE_SYSTEMS`` exist only to exercise the
harness deterministically in tests and dry-runs. They are NOT baselines.
"""

import hashlib
import json
import random
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field

SYSTEM_STATUS_OK = "SUCCEEDED"
SYSTEM_STATUS_FAILED = "FAILED"


class ToolEvent(BaseModel):
    """One observable tool interaction reported by a system."""

    name: str
    status: Literal["OK", "ERROR"]
    payload: dict[str, Any] = Field(default_factory=dict)
    error: str = ""


class EpisodeInput(BaseModel):
    """Bounded episode input handed to any SystemUnderTest."""

    episode_id: str
    dataset_id: str
    task_family: str
    input: Any
    seed: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class EpisodeResult(BaseModel):
    """Normalized episode output returned by any SystemUnderTest."""

    output: Any
    status: Literal["SUCCEEDED", "FAILED"]
    error: str = ""
    tool_events: list[ToolEvent] = Field(default_factory=list)
    rework_events: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SystemUnderTest(Protocol):
    """Neutral interface for any candidate architecture.

    Accepts a bounded ``EpisodeInput``, returns a normalized
    ``EpisodeResult``. Must not require ABY-specific frames.
    """

    def run_episode(self, episode_input: EpisodeInput) -> EpisodeResult:  # noqa: D102
        ...


class NullSystem:
    """Deterministic system that does nothing and succeeds. Tests only."""

    def run_episode(self, episode_input: EpisodeInput) -> EpisodeResult:
        return EpisodeResult(output=None, status=SYSTEM_STATUS_OK)


class EchoSystem:
    """Deterministic system that echoes the input. Tests and dry-runs."""

    def run_episode(self, episode_input: EpisodeInput) -> EpisodeResult:
        return EpisodeResult(
            output={"echo": episode_input.input, "seed": episode_input.seed},
            status=SYSTEM_STATUS_OK,
        )


class FixtureSystem:
    """Deterministic seeded system with observable tool/rework activity.

    Same (input, seed) always yields the same output and the same ordered
    tool/rework events. Provides synthetic token usage metadata so the
    telemetry collector can be exercised without any real model.
    """

    def run_episode(self, episode_input: EpisodeInput) -> EpisodeResult:
        rng = random.Random(episode_input.seed)
        digest = input_digest(episode_input.input)
        value = rng.randint(0, 10**6)
        return EpisodeResult(
            output={"seed": episode_input.seed, "digest": digest, "value": value},
            status=SYSTEM_STATUS_OK,
            tool_events=[
                ToolEvent(name="fixture_calc", status="OK", payload={"digest": digest}),
                ToolEvent(name="fixture_echo", status="OK", payload={"value": value}),
            ],
            rework_events=[{"reason": "synthetic_rework_fixture"}],
            metadata={"input_tokens": 12, "output_tokens": 8},
        )


OFFLINE_SYSTEMS: dict[str, SystemUnderTest] = {
    "null": NullSystem(),
    "echo": EchoSystem(),
    "fixture": FixtureSystem(),
}


def input_digest(value: Any) -> str:
    """Stable digest of an episode input (for reproducibility evidence)."""
    raw = json.dumps(value, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
