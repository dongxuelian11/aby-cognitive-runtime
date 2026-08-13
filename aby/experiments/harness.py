"""Offline experiment harness (P1.1 dry-run).

Runs a bounded experiment through the exact same pipeline every future
baseline must use: EpisodeRunner -> EventLog -> TelemetryCollector ->
artifacts with provenance. The harness has no knowledge of ABY internals
and performs no network access.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .artifacts import write_episode_artifacts
from .config import ExperimentConfig
from .system import EpisodeInput, SystemUnderTest
from ..events import EventLog
from ..runner import EpisodeRunner
from ..telemetry import TelemetryCollector


@dataclass
class ExperimentRunSummary:
    experiment_id: str
    system_id: str
    episode_statuses: dict[str, str] = field(default_factory=dict)
    artifact_dirs: list[Path] = field(default_factory=list)
    started_at: str = ""
    finished_at: str = ""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_experiment(
    config: ExperimentConfig,
    system: SystemUnderTest,
    artifacts_root: str | Path = "artifacts",
) -> ExperimentRunSummary:
    """Run all episodes of a config through the neutral pipeline (offline).

    Episode seeds propagate deterministically: seed_i = config.seed + i.
    Episode IDs are immutable and deterministic: <experiment_id>-epNNNN.
    """
    runner = EpisodeRunner()
    collector = TelemetryCollector()
    summary = ExperimentRunSummary(
        experiment_id=config.experiment_id,
        system_id=config.system_id,
        started_at=_now_iso(),
    )

    for index in range(config.episode_limit):
        seed = config.seed + index
        episode_id = f"{config.experiment_id}-ep{index + 1:04d}"
        log = EventLog()
        episode_input = EpisodeInput(
            episode_id=episode_id,
            dataset_id=config.dataset_id,
            task_family=config.task_family,
            input={"task": f"{config.task_family}: synthetic episode {index + 1}"},
            seed=seed,
            # Generic event-sink hook: systems may append additional
            # evidence events into the episode log (P1.2 neutral mechanism).
            metadata={"event_log": log},
        )

        record = runner.run(system, episode_input, config.timeout_seconds, log)

        telemetry = None
        if config.telemetry_enabled:
            telemetry = collector.finalize(
                config=config,
                episode_id=episode_id,
                result=record.result,
                events=log.replay(episode_id),
                started_at=record.started_at,
                finished_at=record.finished_at,
            )

        artifact_dir = write_episode_artifacts(
            artifacts_root,
            config=config,
            episode_id=episode_id,
            seed=seed,
            events=log.replay(episode_id),
            result=record.result,
            telemetry=telemetry,
            started_at=record.started_at,
            finished_at=record.finished_at,
        )

        summary.episode_statuses[episode_id] = record.status.value
        summary.artifact_dirs.append(artifact_dir)

    summary.finished_at = _now_iso()
    return summary
