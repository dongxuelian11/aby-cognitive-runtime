"""Reproducibility metadata (P1.1).

``provenance.json`` binds every artifact to the exact code/config that
produced it. No secret material is ever recorded.
"""

import hashlib
import platform
import subprocess
from pathlib import Path
from typing import Any

from .config import ExperimentConfig

REPO_ROOT = Path(__file__).resolve().parents[2]


def get_repo_commit() -> str:
    """Exact HEAD of the repository that produced the artifact."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return out.stdout.strip() or "unknown"
    except Exception:  # noqa: BLE001 — provenance must never crash artifact writing
        return "unknown"


def config_sha256(config_json: str) -> str:
    """SHA-256 of the canonical config JSON."""
    return hashlib.sha256(config_json.encode("utf-8")).hexdigest()


def build_provenance(
    *,
    config: ExperimentConfig,
    episode_id: str,
    seed: int,
    config_json: str,
    started_at: str,
    finished_at: str,
) -> dict[str, Any]:
    return {
        "repo_commit": get_repo_commit(),
        "experiment_schema_version": config.schema_version,
        "experiment_id": config.experiment_id,
        "episode_id": episode_id,
        "system_id": config.system_id,
        "dataset_id": config.dataset_id,
        "task_family": config.task_family,
        "seed": seed,
        "config_sha256": config_sha256(config_json),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "started_at": started_at,
        "finished_at": finished_at,
    }
