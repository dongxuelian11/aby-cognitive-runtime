"""Baseline definitions — P0 V0.1 §9.

ABY must be compared against strong, controlled baselines:

- S0 — Single LLM (no long-term memory beyond ordinary context)
- S1 — Single LLM + Shared Memory/RAG
- S2 — Conventional Multi-LLM / MoA
- S3 — ABY Fixed (frozen here; the target architecture of P1)
- S4 — ABY Adaptive (reserved for P5; P0–P4 must not assume it is superior)

Fairness rules (P0 §10) apply to all systems equally.
"""

from enum import Enum

from ..contracts.telemetry import TelemetryRecord


class Baseline(str, Enum):
    S0 = "S0"
    S1 = "S1"
    S2 = "S2"
    S3 = "S3"
    S4 = "S4"


BASELINE_DESCRIPTIONS: dict[str, str] = {
    Baseline.S0: "Single LLM, no long-term memory beyond ordinary context",
    Baseline.S1: "Single LLM + shared memory / RAG (same memory budget as ABY)",
    Baseline.S2: "Conventional multi-LLM / MoA without ABY semantic lane separation",
    Baseline.S3: "ABY Fixed: A/B/Y lanes, fixed compute allocation, deterministic Resolver",
    Baseline.S4: "ABY Adaptive: compute allocation driven by validated state signals (P5, reserved)",
}


class BaselineAdapter:
    """Adapter that runs one episode for one baseline and emits a TelemetryRecord."""

    def run(self, baseline: Baseline, config: dict) -> TelemetryRecord:
        raise NotImplementedError(
            "Baseline adapters are P1 implementation work. Blocked until P0 V0.1 "
            "acceptance (docs/p0/P0_ACCEPTANCE_TRACKER.md)."
        )
