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
from .s0 import (
    S0_PROMPT_SHA256,
    S0_PROMPT_VERSION,
    S0_PROMPT_V0_1,
    S0_SYSTEM_ID,
    S0SingleLLM,
    build_s0,
    s0_requires_missing_credential,
)
from .s1 import (
    S1_PROMPT_SHA256,
    S1_PROMPT_VERSION,
    S1_SYSTEM_ID,
    S1_SYSTEM_PROMPT_V0_1,
    S1SingleLLM,
    build_s1,
    s1_requires_missing_credential,
    validate_s1_config,
)
from .s2 import (
    DEFAULT_PROPOSER_COUNT,
    PROPOSAL_EXECUTION,
    S2_AGGREGATOR_PROMPT_SHA256,
    S2_AGGREGATOR_PROMPT_VERSION,
    S2_AGGREGATOR_PROMPT_V0_1,
    S2_PROPOSER_PROMPT_SHA256,
    S2_PROPOSER_PROMPT_VERSION,
    S2_PROPOSER_PROMPT_V0_1,
    S2_SYSTEM_ID,
    ProviderCallSpec,
    S2ConventionalMoA,
    build_s2,
    s2_all_providers_fake,
    s2_missing_credentials,
    validate_s2_config,
)


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


__all__ = [
    "Baseline",
    "BASELINE_DESCRIPTIONS",
    "BaselineAdapter",
    "S0_PROMPT_SHA256",
    "S0_PROMPT_VERSION",
    "S0_PROMPT_V0_1",
    "S0_SYSTEM_ID",
    "S0SingleLLM",
    "build_s0",
    "s0_requires_missing_credential",
    "S1_PROMPT_SHA256",
    "S1_PROMPT_VERSION",
    "S1_SYSTEM_ID",
    "S1_SYSTEM_PROMPT_V0_1",
    "S1SingleLLM",
    "build_s1",
    "s1_requires_missing_credential",
    "validate_s1_config",
    "PROPOSAL_EXECUTION",
    "DEFAULT_PROPOSER_COUNT",
    "S2_AGGREGATOR_PROMPT_SHA256",
    "S2_AGGREGATOR_PROMPT_VERSION",
    "S2_AGGREGATOR_PROMPT_V0_1",
    "S2_PROPOSER_PROMPT_SHA256",
    "S2_PROPOSER_PROMPT_VERSION",
    "S2_PROPOSER_PROMPT_V0_1",
    "S2_SYSTEM_ID",
    "ProviderCallSpec",
    "S2ConventionalMoA",
    "build_s2",
    "s2_all_providers_fake",
    "s2_missing_credentials",
    "validate_s2_config",
]
