"""Minimal CLI (P1 scope, P0 §17; P1.1 experiment tooling).

Commands:
- ``aby status``                        — P0/P1 authority status
- ``aby experiment validate <config>``  — offline config validation
- ``aby experiment dry-run <config>``   — offline deterministic dry-run + artifacts
- ``aby run --config <config>``         — explicit S0/S1/S2 execution path
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
    # Preserve the accepted P1.2 status line for existing consumers, while
    # recording the subsequent repository authority explicitly.
    print("P1.2 S0 Single-LLM Baseline: IMPLEMENTED_CANDIDATE (P1 not complete)")
    print("P1.2 S0 Review State: ACCEPTED / MERGED")
    print("P1.3 S1 Shared-Memory/RAG Baseline: IMPLEMENTED_CANDIDATE (P1 not complete)")
    print("P1.3 S1 Review State: ACCEPTED / MERGED")
    print("P1.4 S2 Conventional MoA Baseline: IMPLEMENTED_CANDIDATE (P1 not complete)")
    return 0


def _load_config(path: str):
    from .experiments.config import load_config

    return load_config(Path(path))


def _validate_config_semantics(config):
    """Validate system-specific semantics without credentials or network I/O."""
    if config.system_id == "S0":
        from .baselines.s0 import validate_s0_provider_config

        return validate_s0_provider_config(config)
    if config.system_id == "S1":
        from .baselines.s1 import validate_s1_config

        return validate_s1_config(config)
    if config.system_id == "S2":
        from .baselines.s2 import validate_s2_config

        return validate_s2_config(config)
    return None


def _cmd_experiment(args: argparse.Namespace) -> int:
    try:
        config = _load_config(args.config)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except ValidationError as exc:
        print(f"ERROR: invalid experiment config: {exc}", file=sys.stderr)
        return 2
    try:
        provider_spec = _validate_config_semantics(config)
    except ValueError as exc:
        print(f"ERROR: invalid experiment config semantics: {exc}", file=sys.stderr)
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

        if config.system_id in {"S0", "S1", "S2"}:
            from .baselines.s0 import build_s0
            from .baselines.s1 import build_s1
            from .baselines.s2 import build_s2, s2_all_providers_fake

            if config.system_id == "S0":
                offline_only = provider_spec["type"] == "fake"
            elif config.system_id == "S1":
                offline_only = provider_spec["provider"]["type"] == "fake"
            else:
                offline_only = s2_all_providers_fake(config)
            if not offline_only:
                print(
                    "ERROR: 'aby experiment dry-run' is offline-only; "
                    f"network-capable {config.system_id} providers are forbidden regardless of "
                    "credential availability. Use 'aby run --config <config>' "
                    "for explicit real-provider execution.",
                    file=sys.stderr,
                )
                return 2
            try:
                builders = {"S0": build_s0, "S1": build_s1, "S2": build_s2}
                system = builders[config.system_id](config)
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


def _cmd_run(args: argparse.Namespace) -> int:
    """Run S0, S1, or S2 explicitly; later systems remain reserved."""
    try:
        config = _load_config(args.config)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    except ValidationError as exc:
        print(f"ERROR: invalid experiment config: {exc}", file=sys.stderr)
        return 2

    try:
        _validate_config_semantics(config)
    except ValueError as exc:
        print(f"ERROR: invalid experiment config semantics: {exc}", file=sys.stderr)
        return 2

    if config.system_id not in {"S0", "S1", "S2"}:
        print(
            "ERROR: 'aby run' currently supports only S0, S1, and S2; S3 remains "
            "reserved and are not implemented.",
            file=sys.stderr,
        )
        return 2

    from .experiments.harness import run_experiment

    if config.system_id == "S0":
        from .baselines.s0 import build_s0, s0_requires_missing_credential

        missing_env = s0_requires_missing_credential(config)
        builder = build_s0
    elif config.system_id == "S1":
        from .baselines.s1 import build_s1, s1_requires_missing_credential

        missing_env = s1_requires_missing_credential(config)
        builder = build_s1
    else:
        from .baselines.s2 import build_s2, s2_missing_credentials

        missing_env = s2_missing_credentials(config)
        builder = build_s2
    if missing_env:
        missing_names = (
            ", ".join(missing_env) if isinstance(missing_env, list) else missing_env
        )
        print(
            f"ERROR: {config.system_id} real provider requires environment variable(s) "
            f"{missing_names} (not set).",
            file=sys.stderr,
        )
        return 2
    try:
        system = builder(config)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    summary = run_experiment(config, system)
    failed = [
        episode_id
        for episode_id, status in summary.episode_statuses.items()
        if status != "COMPLETED"
    ]
    stream = sys.stderr if failed else sys.stdout
    prefix = "ERROR" if failed else "OK"
    print(
        f"{prefix}: run {summary.experiment_id} — "
        f"{len(summary.artifact_dirs)} episode(s)",
        file=stream,
    )
    for status_id, status in summary.episode_statuses.items():
        print(f"  {status_id}: {status}", file=stream)
    for directory in summary.artifact_dirs:
        print(f"  artifacts: {directory}", file=stream)
    return 2 if failed else 0


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

    run_parser = sub.add_parser("run", help="run an explicit S0, S1, or S2 experiment")
    run_parser.add_argument("--config", required=True, help="experiment config JSON")

    args = parser.parse_args(argv)

    if args.command == "status":
        return _cmd_status()

    if args.command == "experiment":
        return _cmd_experiment(args)

    if args.command == "run":
        return _cmd_run(args)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
