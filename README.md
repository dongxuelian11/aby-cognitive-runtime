# ABY Cognitive Runtime

**Falsifiability-first experimental architecture for long-running LLM systems.**

ABY tests whether separating cognition into three heterogeneous lanes — **A** (Macro Continuity), **B** (Micro Action), **Y** (Dissipation Observer) — improves long-running LLM system quality under controlled compute budgets.

> **Frozen north star (P0 §19):** *Build the smallest reproducible system that can determine whether Macro Continuity A, Micro Action B, and Dissipation Observer Y form a useful cognitive runtime architecture under controlled LLM compute budgets.*

## Phase status

| Phase | Content | Status |
| ----- | ------- | ------ |
| P0 | Theory freeze V0.1 | Archived 2026-08-13 · ACCEPTED (15/15, independent exact-source review PASS) |
| P1 baseline foundation | Experimental harness + S0/S1/S2 controls | P1.1–P1.4 accepted/merged |
| PRE-P1.5 | Authority lock + S1 publication atomicity hardening | ACCEPTED |
| P1.5 | Shared Semantic Geometry Foundation | ACCEPTED |
| P1.6 | ABY Parallel Runtime | IMPLEMENTED_CANDIDATE (not accepted) |
| P1.7 / P1.8 / S3 | Y geometry / geodesic resolver / ABY variants | NOT_STARTED |
| P2–P5 | (to be defined later) | — |

Status distinctions:

```text
P0 Theory Freeze V0.1:      ACCEPTED (authoritative P0 baseline)
P0 scientific hypotheses:   UNVALIDATED / EXPERIMENTAL (H1–H6 untested)
P1.1–P1.4 baseline set:      ACCEPTED / CLOSED
PRE-P1.5 authority lock:      ACCEPTED
PRE-P1.5 runtime hardening:   ACCEPTED
P1.5 semantic geometry:       ACCEPTED
P1.6 parallel runtime:        IMPLEMENTED_CANDIDATE / NOT ACCEPTED
P1.7 / P1.8 / S3:             NOT_STARTED
P1 geodesic architecture:    EXPERIMENTAL HYPOTHESIS / NOT P0 AUTHORITY /
                             NOT SCIENTIFICALLY VALIDATED
License:                    Apache-2.0
```

Before substantive work, read the repository instructions in [`AGENTS.md`](AGENTS.md)
and the canonical [`docs/authority/` index](docs/authority/README.md). Exact
Git/GitHub state must still be verified live.

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
  lanes/              P1.6 live A/B/Y proposal lanes
  runtime/            immutable snapshot, strict parsing, lane-local events,
                      true-concurrent coordinator, optional P1.5 handoff
  resolver/           deterministic Resolver stub
  events/             append-only event log (replayability)
  memory/             committed in-memory episode/fact store + keyword retrieval
  providers/          LLM provider abstraction
  telemetry/          runtime telemetry collector stub
  baselines/          accepted S0/S1/S2 controls, historical S3–S4 definitions
  runner/             episode runner stub
  cli.py              minimal CLI
docs/
  p0/                 frozen doc, acceptance tracker, changelog
  authority/          canonical doctrine, P1 hypothesis, and phase gates
  design/             historical/working P1 design + open questions
  research/           research log
experiments/
  configs/            experiment configs (schema not yet frozen)
  datasets/           task datasets
tests/                contract-level tests (test the freeze, not the implementation)
```

P1.3 S1 is an accepted controlled baseline: the single-LLM provider path plus
fresh process-local committed memory and deterministic bounded keyword retrieval.
Only runner-accepted `COMPLETED` episodes are published; failed, timed-out, and
late-finishing workers cannot become retrievable. If finalization fails after a
new S1 item is published, that exact new item is rolled back without deleting
pre-existing idempotent memory. This is not the future ABY Commit Barrier.

P1.4 S2 is an accepted conventional MoA control: three independent proposer calls in the
default config, followed by exactly one aggregator call. P1.4 records truthful
per-call and aggregate usage/latency/retry evidence and uses deterministic
`sequential_v0` proposal execution. It adds no persistent retrieval, tools,
semantic lanes, geometry, or adaptive compute, and makes no superiority claim.

P1.5 is the accepted shared semantic-geometry foundation. It adapts frozen P0
frames into typed P1 semantic atoms, uses a
provider-neutral encoder contract, normalizes points onto a spherical base
geometry, builds a directed local kNN atlas, and emits bounded cross-lane match
candidates plus deterministic evidence artifacts. The offline hashing encoder
is reference-only infrastructure and is not semantic-quality or scientific
evidence. P1.5 does not implement Y-conditioned edge costs, a geodesic resolver,
live A/B/Y lanes, S3, or a Commit Barrier. P1.6 is the bounded implementation
candidate for live A/B/Y parallel proposal generation; it does not advance
P1.7, P1.8, or S3.

P1.6 is an implementation candidate for the first live ABY proposal stage. One
content-addressed immutable accepted snapshot is projected into role-bounded A,
B, and Y views. Three separately owned providers each perform exactly one
logical inference under fixed versioned prompts and the provider-neutral
`strict-json-text-v0.1` protocol. Strict parsing accepts only an exact JSON
object for the frozen P0 `MacroFrame`, `ActionFrame`, or `DissipationFrame`; it
performs no repair, parser, judge, verifier, or fallback model call.

The coordinator submits all three synchronous calls through a bounded
three-worker executor before waiting, while each provider writes only to its own
event buffer. After all futures settle, evidence is merged deterministically in
A then B then Y order independent of completion order. Any lane/provider/schema
failure returns a failed runtime with no geometry. Only three successful lanes
may reuse the accepted P1.5 pipeline through an injected `SharedEncoder`. P1.6
adds no Y edge penalties, Y dissipation geometry, geodesic search, Resolver,
tool execution, authoritative state mutation, Commit Barrier, or S3 behavior.

## Quickstart

```bash
pip install -e ".[dev]"
pytest
aby status
```

## Rules of the game

- P0 V0.1 is ACCEPTED (2026-08-13): 15/15 freeze items accepted after independent exact-source review of `e3eeae345e5e86cf5bcec6349991bd4c1fbb04ed`; the tracker lives in `docs/p0/P0_ACCEPTANCE_TRACKER.md`. The P0 closure is merged, and P1.1–P1.4 are accepted/closed.
- The P0 hypotheses (H1–H6) remain unvalidated and experimental; acceptance of the freeze is not scientific validation.
- Frozen contracts live in `aby/contracts/`; changes require a new P0 version + changelog entry.
- Event-weight changes require a new telemetry schema version (P0 §7.2).
- Every episode must be replayable from stored events and configuration (P0 §15).
- Falsifiability first, product complexity later (P0 §19).

## Docs

- Repository-wide Codex entrypoint: `AGENTS.md`
- Canonical doctrine, P1 target-architecture hypothesis, and phase gates: `docs/authority/`
- P0 frozen document, acceptance tracker, changelog: `docs/p0/`
- Historical/working P1 design and open questions: `docs/design/P1_DESIGN.md`
- Research log: `docs/research/RESEARCH_LOG.md`

License: [Apache License 2.0](LICENSE).
