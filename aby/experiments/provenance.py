"""Reproducibility metadata (P1.1) — exact source binding.

Source-binding model (P1.1 correction C):

- ``EXACT_CLEAN_COMMIT`` — git available, HEAD resolved, and the worktree is
  clean: no tracked modifications and no untracked non-ignored files.
- ``NON_EXACT_DIRTY`` — git available but the worktree is dirty (tracked
  modifications and/or untracked non-ignored files). ``tracked_diff_sha256``
  records a digest of the tracked diff for later inspection.
- ``UNAVAILABLE`` — git is missing/failed, or the directory is not a git
  repository. Artifacts are explicitly non-authoritative in this state.

Untracked-file policy (documented, conservative): any untracked file that is
NOT git-ignored makes the worktree DIRTY. Git-ignored generated artifacts
(``artifacts/``, ``.pytest_cache/``, build metadata) are declared ignorable by
the repository itself and therefore do not affect exactness.

No secret material is ever recorded.
"""

import hashlib
import platform
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import ExperimentConfig

REPO_ROOT = Path(__file__).resolve().parents[2]

BINDING_EXACT = "EXACT_CLEAN_COMMIT"
BINDING_DIRTY = "NON_EXACT_DIRTY"
BINDING_UNAVAILABLE = "UNAVAILABLE"

WORKTREE_CLEAN = "CLEAN"
WORKTREE_DIRTY = "DIRTY"
WORKTREE_UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class GitState:
    """Explicit source-binding state of the repository that produced a run."""

    repo_commit: str = ""
    worktree_state: str = WORKTREE_UNKNOWN
    source_binding: str = BINDING_UNAVAILABLE
    tracked_diff_sha256: str | None = None


def _run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=10
        )
    except Exception:  # noqa: BLE001 — git missing/failed => explicit UNAVAILABLE
        return None


def get_git_state(cwd: Path = REPO_ROOT) -> GitState:
    """Determine the exact source-binding state for ``cwd``."""
    rev = _run_git(["rev-parse", "HEAD"], cwd)
    if rev is None or rev.returncode != 0:
        return GitState()  # not a git repository, or git unavailable
    commit = rev.stdout.strip()

    status = _run_git(["status", "--porcelain"], cwd)
    if status is None or status.returncode != 0:
        return GitState(repo_commit=commit)  # commit known; cleanliness unknown

    if status.stdout.strip():
        diff_sha = None
        diff = _run_git(["diff"], cwd)
        if diff is not None and diff.returncode == 0:
            diff_sha = hashlib.sha256(diff.stdout.encode("utf-8")).hexdigest()
        return GitState(
            repo_commit=commit,
            worktree_state=WORKTREE_DIRTY,
            source_binding=BINDING_DIRTY,
            tracked_diff_sha256=diff_sha,
        )

    return GitState(
        repo_commit=commit,
        worktree_state=WORKTREE_CLEAN,
        source_binding=BINDING_EXACT,
    )


def get_repo_commit() -> str:
    """Exact HEAD of the repository (empty string when unavailable)."""
    return get_git_state().repo_commit


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
    git_state = get_git_state()
    provenance: dict[str, Any] = {
        "repo_commit": git_state.repo_commit,
        "worktree_state": git_state.worktree_state,
        "source_binding": git_state.source_binding,
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
    if git_state.tracked_diff_sha256 is not None:
        provenance["tracked_diff_sha256"] = git_state.tracked_diff_sha256
    return provenance
