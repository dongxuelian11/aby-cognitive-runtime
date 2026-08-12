"""Episode runner (P1 scope, P0 §17).

Runs one bounded episode for a configured baseline and emits one primary
trace (TelemetryRecord, P0 §8). Orchestration logic is P1 work.
"""

from ..contracts.telemetry import TelemetryRecord


class EpisodeRunner:
    """Executes one bounded episode from an experiment config."""

    def run(self, config: dict) -> TelemetryRecord:
        raise NotImplementedError(
            "Episode runner is P1 implementation work. Blocked until P0 V0.1 "
            "acceptance (docs/p0/P0_ACCEPTANCE_TRACKER.md)."
        )
