"""P1.1 experiment harness foundation.

Architecture-neutral: the same config, runner, event log, telemetry collector,
artifact writer and provenance metadata must serve all future candidate
architectures (S0/S1/S2/S3) without favoring any of them.

This package deliberately does NOT import ABY lane frames or resolver
contracts. Nothing here answers "is ABY better?" — it only answers
"can multiple architectures run through exactly the same pipeline?".
"""

from .config import EXPERIMENT_CONFIG_SCHEMA_VERSION, ExperimentConfig, load_config
from .harness import ExperimentRunSummary, run_experiment
from .system import (
    OFFLINE_SYSTEMS,
    EchoSystem,
    EpisodeInput,
    EpisodeResult,
    FixtureSystem,
    NullSystem,
    SystemUnderTest,
    ToolEvent,
    input_digest,
)

__all__ = [
    "EXPERIMENT_CONFIG_SCHEMA_VERSION",
    "ExperimentConfig",
    "load_config",
    "ExperimentRunSummary",
    "run_experiment",
    "OFFLINE_SYSTEMS",
    "EchoSystem",
    "EpisodeInput",
    "EpisodeResult",
    "FixtureSystem",
    "NullSystem",
    "SystemUnderTest",
    "ToolEvent",
    "input_digest",
]
