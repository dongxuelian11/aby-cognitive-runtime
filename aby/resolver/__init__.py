"""Deterministic, rule-based Resolver (P0 V0.1 §6).

The initial ABY Resolver must be deterministic or rule-based.
It is NOT a fourth master LLM (P0 §6.1). No lane owns global authority;
the Resolver remains bounded (P0 §15).

Inputs: MacroFrame, ActionFrame, DissipationFrame, current evidence,
runtime telemetry (P0 §6.2).
Output: ResolveDecision (P0 §6.3).
"""

from ..contracts.frames import ResolveDecision

# P0 §6.4: no recursive loop may run without a bounded retry limit.
MAX_RETRIES = 3


class Resolver:
    """Deterministic rule-based resolver. Decision logic is P1 work."""

    def resolve(
        self,
        macro_frame,
        action_frame,
        dissipation_frame,
        evidence=None,
        telemetry=None,
    ) -> ResolveDecision:
        raise NotImplementedError(
            "Resolver decision table is P1 implementation work. Blocked until "
            "P0 V0.1 acceptance (docs/p0/P0_ACCEPTANCE_TRACKER.md)."
        )
