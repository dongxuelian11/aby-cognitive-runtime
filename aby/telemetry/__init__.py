"""Runtime telemetry collector (P1.1).

Populates the frozen P0 ``TelemetryRecord`` wire contract (P0 §8) strictly
from observable runner/runtime evidence. No hidden chain-of-thought
collection; no claim to measure true internal model compute (P0 §7).

P1.1 measurement convention (neutral, documented in docs/design/P1_DESIGN.md):

- ``A_raw/B_raw/W_raw`` and ``a/b/y/r`` are ABY-instrumentation measures.
  For systems without ABY instrumentation they remain at the frozen-schema
  defaults (0 / 0.0), which in P1.1 means "measurement not applicable",
  never "measured zero". This convention applies equally to every future
  baseline label and cannot bias S0/S1/S2 against S3: cross-system
  comparisons use the uniformly-collected observable counters below.
- ``qA/qB/qY`` remain 0.0 unless a system explicitly reports compute
  allocation (no system does in P1.1).
- ``rework_count`` is counted only from explicit observable "rework" events.
- ``user_result`` / ``user_quality_score`` are populated only from
  externally supplied evaluation metadata in the episode result.
"""

from datetime import datetime

from ..contracts.telemetry import TelemetryRecord
from ..events import Event
from ..experiments.config import ExperimentConfig
from ..experiments.system import EpisodeResult


class TelemetryCollector:
    """Builds one frozen TelemetryRecord per episode from real evidence."""

    def finalize(
        self,
        *,
        config: ExperimentConfig,
        episode_id: str,
        result: EpisodeResult | None,
        events: list[Event],
        started_at: str,
        finished_at: str,
    ) -> TelemetryRecord:
        tool_events = [e for e in events if e.kind == "tool_call"]
        tool_calls = len(tool_events)
        failed_tool_calls = sum(1 for e in tool_events if e.payload.get("status") == "ERROR")
        rework_count = sum(1 for e in events if e.kind == "rework")

        metadata = result.metadata if result is not None else {}
        input_tokens = _as_int(metadata.get("input_tokens"))
        output_tokens = _as_int(metadata.get("output_tokens"))
        latency_ms = _latency_ms(started_at, finished_at)

        return TelemetryRecord(
            episode_id=episode_id,
            task_family=config.task_family,
            difficulty=config.difficulty,
            risk=config.risk,
            model_config={"ref": config.model_config_ref},
            memory_config={"ref": config.memory_config_ref},
            # ABY-instrumentation fields: not applicable in P1.1 (see docstring).
            qA=0.0,
            qB=0.0,
            qY=0.0,
            A_raw=0,
            B_raw=0,
            W_raw=0,
            a=0.0,
            b=0.0,
            y=0.0,
            r=0.0,
            latency_ms=latency_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            tool_calls=tool_calls,
            failed_tool_calls=failed_tool_calls,
            rework_count=rework_count,
            continuity_errors=0,
            factual_errors=0,
            user_result=metadata.get("user_result"),
            user_quality_score=metadata.get("user_quality_score"),
        )


def _as_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _latency_ms(started_at: str, finished_at: str) -> int:
    if not started_at or not finished_at:
        return 0
    try:
        start = datetime.fromisoformat(started_at)
        finish = datetime.fromisoformat(finished_at)
        return max(0, int((finish - start).total_seconds() * 1000))
    except ValueError:
        return 0
