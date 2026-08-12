"""B-Layer — Micro Action (P0 V0.1 §5.2)."""

from ..contracts.frames import ActionFrame


class BLayer:
    """Solves the immediate task with local context, tools, and minimum macro constraints.

    Mission (P0 §5.2): solve the immediate task using current input, local
    context, tools, and only the minimum macro constraints required.

    Typical inputs: current user request or event, current task, available
    tools, local working context, selected constraints from A, relevant evidence.

    Output contract: ActionFrame.

    Forbidden behavior (P0 §5.2):
    - Must not load all historical memory by default.
    - Must not autonomously redefine long-term goals.
    - Must not treat stale memory as current authority.
    - Must not use A's uncertainty as permission to fabricate.

    P0 §15: B is typically highest-frequency.
    """

    def produce(self, *args, **kwargs) -> ActionFrame:
        raise NotImplementedError(
            "B-Layer is P1 implementation work. Blocked until P0 V0.1 acceptance "
            "(docs/p0/P0_ACCEPTANCE_TRACKER.md)."
        )
