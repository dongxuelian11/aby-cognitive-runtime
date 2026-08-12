# ABY Cognitive Runtime

**Falsifiability-first experimental architecture for long-running LLM systems.**

ABY tests whether separating cognition into three heterogeneous lanes — **A** (Macro Continuity), **B** (Micro Action), **Y** (Dissipation Observer) — improves long-running LLM system quality under controlled compute budgets.

> **Frozen north star (P0 §19):** *Build the smallest reproducible system that can determine whether Macro Continuity A, Micro Action B, and Dissipation Observer Y form a useful cognitive runtime architecture under controlled LLM compute budgets.*

## Phase status

| Phase | Content | Status |
| ----- | ------- | ------ |
| P0 | Theory freeze V0.1 | Archived 2026-08-13 · acceptance pending |
| P1 | Experimental harness | Skeleton only · blocked on P0 acceptance |
| P2–P5 | (to be defined later) | — |

## Key concepts

- `a / b / y` — normalized state variables (order / action / dissipation), `a + b + y = 1`.
- `r = a / b` — testable balance ratio. Hypothesis `r* ≈ 2`, not a law (P0 §2).
- `A / B / Y` (uppercase) — runtime lanes; distinct from the state variables (P0 §4).
- `qA + qB + qY = 1` — compute allocation, a separate vector (P0 §4.3).
- The architecture must beat strong baselines (S0–S2) under controlled budgets to justify itself (P0 §1, §9).

## Repository layout

```text
aby/                  Python package (P1 skeleton)
  contracts/          FROZEN P0 schemas: lane frames, ResolveDecision,
                      telemetry record, measurement model
  lanes/              A/B/Y lane stubs
  resolver/           deterministic Resolver stub
  events/             append-only event log (replayability)
  memory/             minimal shared memory interface (P0 §14)
  providers/          LLM provider abstraction
  telemetry/          runtime telemetry collector stub
  baselines/          S0–S4 definitions + adapter stub
  runner/             episode runner stub
  cli.py              minimal CLI
docs/
  p0/                 frozen doc, acceptance tracker, changelog
  design/             P1 design draft + open questions
  research/           research log
experiments/
  configs/            experiment configs (schema not yet frozen)
  datasets/           task datasets
tests/                contract-level tests (test the freeze, not the implementation)
```

## Quickstart

```bash
pip install -e ".[dev]"
pytest
aby status
```

## Rules of the game

- No implementation before P0 acceptance (P0 §16). The acceptance tracker lives in `docs/p0/P0_ACCEPTANCE_TRACKER.md`.
- Frozen contracts live in `aby/contracts/`; changes require a new P0 version + changelog entry.
- Event-weight changes require a new telemetry schema version (P0 §7.2).
- Every episode must be replayable from stored events and configuration (P0 §15).
- Falsifiability first, product complexity later (P0 §19).

## Docs

- P0 frozen document, acceptance tracker, changelog: `docs/p0/`
- P1 design draft with open questions: `docs/design/P1_DESIGN.md`
- Research log: `docs/research/RESEARCH_LOG.md`

License: TBD (all rights reserved until chosen).
