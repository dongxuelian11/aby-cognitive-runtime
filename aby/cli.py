"""Minimal CLI (P1 scope, P0 §17; P1.1 experiment tooling).

Commands:
- ``aby status``                        — P0/P1 authority status
- ``aby experiment validate <config>``  — offline config validation
- ``aby experiment dry-run <config>``   — offline deterministic dry-run + artifacts
- ``aby run --config <config>``         — reserved for later P1 stages (not implemented)
"""

import argparse
import sys
from pathlib import Path

from pydantic import ValidationError


def _cmd_status() -> int:
    print("ABY Cognitive Runtime — P0 freeze V0.1")
    print("Archived: 2026-08-13")
    print("Acceptance: ACCEPTED (15/15; independent exact-source review of e3eeae345e5e86cf5bcec6349991bd4c1fbb04ed)")
    print("THEORY_FREEZE_ACCEPTED: yes")
    print("SCIENTIFICALLY_VALIDATED: no (hypotheses H1-H6 unvalidated / experimental)")
    print("P1 Experimental Harness: authorized (P0 closure merged)")
    print("P1.1 Experimental Harness Foundation: IMPLEMENTED_CANDIDATE (P1 not complete)")
    print("P1.2 S0 Single-LLM Baseline: IMPLEMENTED_CANDIDATE (P1 not complete)")
    return 0


def _load_config(path: str):
    from .experiments.config import load_config

    return load_config(Path(path))


def _cmd_experiment(args: argparse.Namespace) -> int:
    try:
        config = _load_config(args.config)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except ValidationError as exc:
        print(f"ERROR: invalid experiment config: {exc}", file=sys.stderr)
        return 2

    if args.experiment_command == "validate":
        print(
            f"OK: {config.experiment_id} "
            f"(schema {config.schema_version}, system {config.system_id}, "
            f"{config.episode_limit} episode(s))"
        )
        return 0

    if args.experiment_command == "dry-run":
        from .experiments.harness import run_experiment
        from .experiments.system import OFFLINE_SYSTEMS

        if config.system_id == "S0":
            from .baselines.s0 import build_s0, s0_requires_missing_credential

            missing_env = s0_requires_missing_credential(config)
            if missing_env is not None:
                print(
                    f"ERROR: S0 real provider requires environment variable "
                    f"{missing_env} (not set). Set it or use the offline fake "
                    f"provider config.",
                    file=sys.stderr,
                )
                return 2
            try:
                system = build_s0(config)
            except ValueError as exc:
                print(f"ERROR: {exc}", file=sys.stderr)
                return 2
        else:
            system = OFFLINE_SYSTEMS.get(config.system_id)
            if system is None:
                print(
                    f"ERROR: no offline deterministic system registered for system_id "
                    f"'{config.system_id}'. Available: {sorted(OFFLINE_SYSTEMS)}",
                    file=sys.stderr,
                )
                return 2
        summary = run_experiment(config, system)
        print(f"OK: dry-run {summary.experiment_id} — {len(summary.artifact_dirs)} episode(s)")
        for status_id, status in summary.episode_statuses.items():
            print(f"  {status_id}: {status}")
        for directory in summary.artifact_dirs:
            print(f"  artifacts: {directory}")
        return 0

    return 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="aby",
        description="ABY Cognitive Runtime — P1 experimental harness (P0 freeze V0.1)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="show P0/P1 authority status")

    experiment = sub.add_parser("experiment", help="experiment config tooling (P1.1)")
    experiment_sub = experiment.add_subparsers(dest="experiment_command", required=True)
    validate_parser = experiment_sub.add_parser(
        "validate", help="validate an experiment config (offline)"
    )
    validate_parser.add_argument("config", help="path to experiment config JSON")
    dry_run_parser = experiment_sub.add_parser(
        "dry-run", help="run an offline deterministic dry-run and write artifacts"
    )
    dry_run_parser.add_argument("config", help="path to experiment config JSON")

    run_parser = sub.add_parser(
        "run", help="run one experiment episode (reserved for later P1 stages)"
    )
    run_parser.add_argument("--config", required=True, help="experiment config JSON")

    args = parser.parse_args(argv)

    if args.command == "status":
        return _cmd_status()

    if args.command == "experiment":
        return _cmd_experiment(args)

    if args.command == "run":
        raise NotImplementedError(
            "Episode execution is reserved for later P1 stages. "
            "Use 'aby experiment dry-run' for the P1.1 offline harness."
        )

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
