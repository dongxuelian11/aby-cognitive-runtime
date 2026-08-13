"""Bounded episode runner (P1.1).

Architecture-neutral: the runner knows nothing about S0/S1/S2/S3 internals
or ABY lane cognition. It executes any ``SystemUnderTest`` under a bounded
timeout and records a complete, replayable lifecycle event sequence.

Lifecycle (P1.1 task §7.3): CREATED -> STARTED -> COMPLETED | FAILED | TIMED_OUT.

Timeout model (P1.1 correction A — soft timeout, honest and bounded):
- the runner waits at most ``timeout_seconds`` for the system;
- on timeout the episode is marked ``TIMED_OUT`` and the runner returns
  promptly using non-blocking executor shutdown (it never waits for a
  non-cooperative worker to finish);
- Python threads cannot be hard-killed; the detached worker thread may
  continue in the background, but its late return value is discarded and
  can never mutate the committed episode record, event log, or artifacts;
- there is no automatic retry in P1.1; retry policy requires explicit
  future design.
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
        pool = ThreadPoolExecutor(max_workers=1)
        try:
            future = pool.submit(system.run_episode, episode_input)
            result = future.result(timeout=timeout_seconds)
        except FutureTimeoutError:
            record.status = EpisodeStatus.TIMED_OUT
            record.error = f"timeout exceeded ({timeout_seconds}s)"
        except Exception as exc:  # noqa: BLE001 — every failure becomes evidence
            record.status = EpisodeStatus.FAILED
            record.error = f"{type(exc).__name__}: {exc}"
        finally:
            # Soft-timeout model: never block on a non-cooperative worker.
            # cancel_futures affects only not-yet-started work; a running
            # worker continues detached and its late result is discarded.
            pool.shutdown(wait=False, cancel_futures=True)

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

        # Optional architecture-neutral outcome finalization.  S1 uses this
        # narrow hook to publish a worker-produced memory proposal only after
        # this runner has accepted COMPLETED.  A timed-out worker has no
        # ``result`` here, so its late return has no publication path.
        if result is not None:
            finalizer = getattr(system, "finalize_episode_outcome", None)
            if callable(finalizer):
                try:
                    result = finalizer(
                        episode_input,
                        result,
                        record.status.value,
                        event_log,
                    )
                except Exception as exc:  # noqa: BLE001 — fail closed as evidence
                    record.status = EpisodeStatus.FAILED
                    record.error = f"outcome finalization failed: {type(exc).__name__}: {exc}"

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
