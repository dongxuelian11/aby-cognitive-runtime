"""Minimal CLI (P1 scope, P0 §17)."""

import argparse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="aby",
        description="ABY Cognitive Runtime — P1 experimental harness (P0 freeze V0.1)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="show P0 freeze status")
    run_parser = sub.add_parser("run", help="run one experiment episode (not yet implemented)")
    run_parser.add_argument("--config", required=True, help="experiment config YAML")

    args = parser.parse_args(argv)

    if args.command == "status":
        print("ABY Cognitive Runtime — P0 freeze V0.1")
        print("Archived: 2026-08-13")
        print("Acceptance: ACCEPTED (15/15; independent exact-source review of e3eeae345e5e86cf5bcec6349991bd4c1fbb04ed)")
        print("THEORY_FREEZE_ACCEPTED: yes")
        print("SCIENTIFICALLY_VALIDATED: no (hypotheses H1-H6 unvalidated / experimental)")
        print("P1 Experimental Harness: authorized after closure merge; implementation not started")
        return 0

    if args.command == "run":
        raise NotImplementedError(
            "Episode execution is P1 implementation work. Blocked until P0 V0.1 "
            "acceptance (docs/p0/P0_ACCEPTANCE_TRACKER.md)."
        )

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
