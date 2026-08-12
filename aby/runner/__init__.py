"""Bounded episode runner (P1.1).

Architecture-neutral: the runner knows nothing about S0/S1/S2/S3 internals
or ABY lane cognition. It executes any ``SystemUnderTest`` under a bounded
timeout and records a complete, replayable lifecycle event sequence.

Lifecycle (P1.1 task §7.3): CREATED -> STARTED -> COMPLETED | FAILED | TIMED_OUT.

No automatic retries in P1.1; retry policy requires explicit future design.
"""

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel

from ..events import Event, EventLog
from ..experiments.system import EpisodeInput, EpisodeResult, SystemUnderTest, input_digest


class EpisodeStatus(str, Enum):
    CREATED = "CREATED"
    STARTED = "STARTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"


class EpisodeRecord(BaseModel):
    """Normalized outcome of one bounded episode."""

    episode_id: str
    status: EpisodeStatus
    started_at: str = ""
    finished_at: str = ""
    result: EpisodeResult | None = None
    error: str = ""
    timeout_seconds: float


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EpisodeRunner:
    """Runs one bounded episode and emits its lifecycle into an EventLog."""

    def run(
        self,
        system: SystemUnderTest,
        episode_input: EpisodeInput,
        timeout_seconds: float,
        event_log: EventLog,
    ) -> EpisodeRecord:
        record = EpisodeRecord(
            episode_id=episode_input.episode_id,
            status=EpisodeStatus.CREATED,
            timeout_seconds=timeout_seconds,
        )
        event_log.append(
            Event(
                episode_id=episode_input.episode_id,
                kind="episode_created",
                payload={
                    "seed": episode_input.seed,
                    "dataset_id": episode_input.dataset_id,
                    "task_family": episode_input.task_family,
                    "input_digest": input_digest(episode_input.input),
                },
            )
        )

        record.status = EpisodeStatus.STARTED
        record.started_at = _now_iso()
        event_log.append(Event(episode_id=episode_input.episode_id, kind="episode_started", payload={}))

        result: EpisodeResult | None = None
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(system.run_episode, episode_input)
            try:
                result = future.result(timeout=timeout_seconds)
            except FutureTimeoutError:
                record.status = EpisodeStatus.TIMED_OUT
                record.error = f"timeout exceeded ({timeout_seconds}s)"
            except Exception as exc:  # noqa: BLE001 — every failure becomes evidence
                record.status = EpisodeStatus.FAILED
                record.error = f"{type(exc).__name__}: {exc}"

        if record.status in (EpisodeStatus.STARTED, EpisodeStatus.CREATED):
            # The system returned normally; classify its normalized result.
            if result is None:
                record.status = EpisodeStatus.FAILED
                record.error = "system returned no EpisodeResult"
            elif result.status == "FAILED" or result.error:
                record.status = EpisodeStatus.FAILED
                record.error = result.error or "system reported FAILED"
            else:
                record.status = EpisodeStatus.COMPLETED

        # Observable evidence events, in deterministic order, before the terminal event.
        if result is not None:
            for tool in result.tool_events:
                event_log.append(
                    Event(
                        episode_id=episode_input.episode_id,
                        kind="tool_call",
                        payload={
                            "name": tool.name,
                            "status": tool.status,
                            "payload": tool.payload,
                            "error": tool.error,
                        },
                    )
                )
            for rework in result.rework_events:
                event_log.append(
                    Event(episode_id=episode_input.episode_id, kind="rework", payload=rework)
                )

        record.finished_at = _now_iso()
        terminal_kind = {
            EpisodeStatus.COMPLETED: "episode_completed",
            EpisodeStatus.FAILED: "episode_failed",
            EpisodeStatus.TIMED_OUT: "episode_timed_out",
        }[record.status]
        event_log.append(
            Event(
                episode_id=episode_input.episode_id,
                kind=terminal_kind,
                payload={"error": record.error, "status": record.status.value},
            )
        )
        record.result = result
        return record
