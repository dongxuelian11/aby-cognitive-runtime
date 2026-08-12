"""Runtime telemetry collector (P1 scope, P0 §17).

The frozen measurement model lives in aby/contracts/measurement.py (P0 §7)
and the frozen trace record in aby/contracts/telemetry.py (P0 §8).
This module is the runtime side: collecting raw event counts per episode
into a TelemetryRecord. Collection logic is P1 work.
"""

from ..contracts.telemetry import TelemetryRecord


class TelemetryCollector:
    """Accumulates observable events for one episode and emits a TelemetryRecord."""

    def record_event(self, episode_id: str, category: str, event_kind: str, weight: int = 1) -> None:
        """Add one weighted observable event.

        category: one of "A_raw", "B_raw", "W_raw" (P0 §7.1).
        event_kind: a key from the frozen weight tables (P0 §7.2).
        """
        raise NotImplementedError(
            "Telemetry collection is P1 implementation work. Blocked until P0 V0.1 "
            "acceptance (docs/p0/P0_ACCEPTANCE_TRACKER.md)."
        )

    def finalize(self, episode_id: str) -> TelemetryRecord:
        """Emit the primary trace for the episode (P0 §8)."""
        raise NotImplementedError(
            "Telemetry finalization is P1 implementation work. Blocked until P0 V0.1 "
            "acceptance (docs/p0/P0_ACCEPTANCE_TRACKER.md)."
        )
