"""Y-Layer — Dissipation Observer (P0 V0.1 §5.3)."""

from ..contracts.frames import DissipationFrame


class YLayer:
    """Detects unresolved inconsistency and waste across A, B, memory, tools, and evidence.

    Y is NOT a third answer generator (P0 §5.3).

    Typical inputs: MacroFrame, ActionFrame, current event, memory evidence,
    tool evidence, prior episode state, execution trace.

    Output contract: DissipationFrame.

    Forbidden behavior (P0 §5.3):
    - Must not directly block execution.
    - Must not own final control authority.
    - Must not inflate y merely because information is incomplete.
    - Must distinguish normal uncertainty from harmful unresolved mismatch.
    - Must not recursively request unlimited verification.

    P0 §15: Y may be lightweight and frequent.
    """

    def observe(self, *args, **kwargs) -> DissipationFrame:
        raise NotImplementedError(
            "Y-Layer is P1 implementation work. Blocked until P0 V0.1 acceptance "
            "(docs/p0/P0_ACCEPTANCE_TRACKER.md)."
        )
