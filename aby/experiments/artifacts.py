"""Run/episode artifact writer (P1.1).

Layout (P1.1 task §7.6):

    <artifacts_root>/experiments/<experiment_id>/<episode_id>/
        config.json      — canonical experiment config
        events.jsonl     — ordered event log (one JSON object per line)
        result.json      — normalized episode result
        telemetry.json   — frozen ABY_RUNTIME_TELEMETRY_V0.1 record
        provenance.json  — exact code/config binding metadata

Generated artifacts are Git-ignored (``artifacts/``).
"""

import json
from pathlib import Path

from ..contracts.telemetry import TelemetryRecord
from ..events import Event
from ..experiments.config import ExperimentConfig
from ..experiments.provenance import build_provenance
from ..experiments.system import EpisodeResult


def episode_artifact_dir(artifacts_root: str | Path, experiment_id: str, episode_id: str) -> Path:
    return Path(artifacts_root) / "experiments" / experiment_id / episode_id


def write_episode_artifacts(
    artifacts_root: str | Path,
    *,
    config: ExperimentConfig,
    episode_id: str,
    seed: int,
    events: list[Event],
    result: EpisodeResult | None,
    telemetry: TelemetryRecord | None,
    started_at: str,
    finished_at: str,
) -> Path:
    """Write the five artifact files for one episode; returns the directory."""
    directory = episode_artifact_dir(artifacts_root, config.experiment_id, episode_id)
    directory.mkdir(parents=True, exist_ok=True)

    config_json = config.to_json()
    config_text = config_json + "\n"
    (directory / "config.json").write_text(config_text, encoding="utf-8")

    with (directory / "events.jsonl").open("w", encoding="utf-8") as handle:
        for event in events:
            line = {"event_id": event.event_id, **event.model_dump()}
            handle.write(json.dumps(line, ensure_ascii=False, sort_keys=True) + "\n")

    if result is not None:
        (directory / "result.json").write_text(result.model_dump_json(indent=2) + "\n", encoding="utf-8")
    else:
        (directory / "result.json").write_text("null\n", encoding="utf-8")

    if telemetry is not None:
        (directory / "telemetry.json").write_text(telemetry.model_dump_json(indent=2) + "\n", encoding="utf-8")
    else:
        (directory / "telemetry.json").write_text('{"telemetry_enabled": false}\n', encoding="utf-8")

    provenance = build_provenance(
        config=config,
        episode_id=episode_id,
        seed=seed,
        config_json=config_text,
        started_at=started_at,
        finished_at=finished_at,
    )
    (directory / "provenance.json").write_text(
        json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return directory
