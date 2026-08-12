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
        print("Acceptance: PENDING (docs/p0/P0_ACCEPTANCE_TRACKER.md)")
        print("P1 harness: skeleton only — no implementation before acceptance.")
        return 0

    if args.command == "run":
        raise NotImplementedError(
            "Episode execution is P1 implementation work. Blocked until P0 V0.1 "
            "acceptance (docs/p0/P0_ACCEPTANCE_TRACKER.md)."
        )

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
