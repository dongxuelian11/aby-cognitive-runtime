"""Frozen measurement model — ABY P0 V0.1 §7.

Instrument calibration, not a theoretical law.
Changing weights requires a new telemetry schema version (P0 §7.2).
"""

import math
from dataclasses import dataclass

# P0 §7.2 — A_raw: observable macro-maintenance / global-coherence activity
EVENT_WEIGHTS_A_RAW: dict[str, int] = {
    "necessary_authority_or_context_read": 1,
    "task_decomposition_or_state_alignment": 1,
    "boundary_or_consistency_check": 1,
    "necessary_verification": 1,
    "conflict_resolution_or_state_rebuild": 2,
}

# P0 §7.2 — B_raw: observable task-progress / local-action activity
EVENT_WEIGHTS_B_RAW: dict[str, int] = {
    "effective_execution_step": 1,
    "effective_tool_call": 1,
    "completed_explicit_subgoal": 1,
    "usable_deliverable": 2,
}

# P0 §7.2 — W_raw: observable waste / rework / failed-action activity
EVENT_WEIGHTS_W_RAW: dict[str, int] = {
    "failed_or_invalid_call": 1,
    "duplicate_work": 1,
    "scope_or_goal_drift": 2,
    "rework_from_misunderstanding": 2,
    "discarded_or_unusable_output": 3,
}


@dataclass(frozen=True)
class NormalizedState:
    """Normalized state variables per P0 §7.1."""

    a: float
    b: float
    y: float
    r: float


def normalize(A_raw: int, B_raw: int, W_raw: int) -> NormalizedState:
    """Apply the P0 §7.1 normalization.

    T = A_raw + B_raw + W_raw
    a = A_raw / T, b = B_raw / T, y = W_raw / T, r = A_raw / B_raw

    Raises ValueError for negative raw counts or a zero total.
    r is +inf when B_raw == 0 and A_raw > 0 (high-side limit).
    """
    for name, value in (("A_raw", A_raw), ("B_raw", B_raw), ("W_raw", W_raw)):
        if value < 0:
            raise ValueError(f"{name} must be >= 0, got {value}")
    total = A_raw + B_raw + W_raw
    if total == 0:
        raise ValueError("total raw activity is zero; normalized state is undefined")
    r = (A_raw / B_raw) if B_raw else math.inf
    return NormalizedState(a=A_raw / total, b=B_raw / total, y=W_raw / total, r=r)


__all__ = [
    "EVENT_WEIGHTS_A_RAW",
    "EVENT_WEIGHTS_B_RAW",
    "EVENT_WEIGHTS_W_RAW",
    "NormalizedState",
    "normalize",
]
