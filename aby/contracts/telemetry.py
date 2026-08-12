"""Frozen telemetry contract — ABY P0 V0.1 §8.

One primary trace per bounded episode. Field names must match the frozen
schema exactly; renames require a new P0 version.

Note: the serialized field names "schema" and "model_config" collide with
pydantic reserved attribute names, so the Python attributes are suffixed
and mapped via aliases. The JSON wire format is exactly the frozen schema.
"""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "ABY_RUNTIME_TELEMETRY_V0.1"


class TelemetryRecord(BaseModel):
    """Primary trace of one bounded episode (P0 §8)."""

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    schema_name: str = Field(default=SCHEMA_VERSION, alias="schema")
    episode_id: str
    task_family: str = ""
    difficulty: str = ""
    risk: str = ""
    model_cfg: dict[str, Any] = Field(default_factory=dict, alias="model_config")
    memory_cfg: dict[str, Any] = Field(default_factory=dict, alias="memory_config")
    qA: float = 0.0
    qB: float = 0.0
    qY: float = 0.0
    A_raw: int = 0
    B_raw: int = 0
    W_raw: int = 0
    a: float = 0.0
    b: float = 0.0
    y: float = 0.0
    r: float = 0.0
    latency_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: int = 0
    failed_tool_calls: int = 0
    rework_count: int = 0
    continuity_errors: int = 0
    factual_errors: int = 0
    user_result: Any | None = None
    user_quality_score: float | None = None


__all__ = ["SCHEMA_VERSION", "TelemetryRecord"]
