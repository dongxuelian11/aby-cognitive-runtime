"""A-Layer — Macro Continuity (P0 V0.1 §5.1)."""

from ..contracts.frames import MacroFrame


class ALayer:
    """Maintains long-horizon continuity without directly solving the current task.

    Mission (P0 §5.1): maintain the long-horizon state needed for continuity
    without directly solving the current task unless required for macro
    interpretation.

    Typical inputs: current event, long-term memory, persistent facts,
    previous accepted state, long-term goals, constraints, relationship
    history, world timeline, prior commitments, selected evidence.

    Output contract: MacroFrame.

    Forbidden behavior (P0 §5.1):
    - Must not emit the final user-facing answer as its primary function.
    - Must not receive the full B scratch context by default.
    - Must not invent long-term state when evidence is missing.
    - Must not silently overwrite persistent memory.

    P0 §15: A may be slower and event-triggered.
    """

    def produce(self, *args, **kwargs) -> MacroFrame:
        raise NotImplementedError(
            "A-Layer is P1 implementation work. Blocked until P0 V0.1 acceptance "
            "(docs/p0/P0_ACCEPTANCE_TRACKER.md)."
        )
