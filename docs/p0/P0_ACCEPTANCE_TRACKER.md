# P0 Acceptance Tracker

Source: `ABY_P0_THEORY_FREEZE_EXPERIMENTAL_ARCHITECTURE_V0_1.md` §16.

P0 is complete only when every item below is explicitly accepted.
**No implementation begins before acceptance** (P0 §16).

Status legend: `[ ]` not yet accepted · `[x]` accepted

| # | Frozen item | P0 § | Acceptance date | Status |
|---|-------------|------|-----------------|--------|
| 1 | Theory variables and symbols (a, b, y, r, normalized state) | 2 | 2026-08-13 | [x] |
| 2 | Uppercase/lowercase distinction (layers vs state variables) | 4 | 2026-08-13 | [x] |
| 3 | Compute-budget notation (qA, qB, qY) | 4.3 | 2026-08-13 | [x] |
| 4 | Lane semantics (A/B/Y missions and forbidden behavior) | 5 | 2026-08-13 | [x] |
| 5 | Lane I/O schemas (MacroFrame, ActionFrame, DissipationFrame) | 5 | 2026-08-13 | [x] |
| 6 | Resolver decisions (ResolveDecision + allowed kinds) | 6 | 2026-08-13 | [x] |
| 7 | Telemetry schema (ABY_RUNTIME_TELEMETRY_V0.1) | 8 | 2026-08-13 | [x] |
| 8 | Initial event weights (A_raw / B_raw / W_raw) | 7.2 | 2026-08-13 | [x] |
| 9 | Baseline definitions (S0–S4) | 9 | 2026-08-13 | [x] |
| 10 | Experimental fairness rules | 10 | 2026-08-13 | [x] |
| 11 | Evaluation metrics | 11 | 2026-08-13 | [x] |
| 12 | Falsifiable hypotheses (H1–H6) | 12 | 2026-08-13 | [x] |
| 13 | Explicit non-claims | 13 | 2026-08-13 | [x] |
| 14 | P1 memory boundary (episode store, facts, keyword retrieval) | 14 | 2026-08-13 | [x] |
| 15 | Replayability requirement | 15 | 2026-08-13 | [x] |

## Authority of acceptance

P0 V0.1 formally accepted following independent exact-source semantic review of baseline `e3eeae345e5e86cf5bcec6349991bd4c1fbb04ed`.

Review result: `ABY_P0_EXACT_SOURCE_SEMANTIC_REVIEW_PASS` — P0_FREEZE_ITEMS: 15 / 15 ACCEPTABLE.

Acceptance records the freeze as the project's authoritative P0 baseline.
It is **not** scientific validation of the ABY hypotheses: H1–H6 remain
untested and experimental.

## Freeze record

| Version | Date | Decision | Approver | Notes |
|---------|------|----------|----------|-------|
| V0.1 | 2026-08-13 | ACCEPTED | Independent exact-source semantic review | 15/15 items accepted; baseline e3eeae345e5e86cf5bcec6349991bd4c1fbb04ed |

## Rules after acceptance

- Any change to an accepted item requires a new version (V0.2, V0.3, …) and a `CHANGELOG.md` entry describing the delta.
- Event-weight changes additionally require a new telemetry schema version (P0 §7.2).
- Frame/telemetry field renames are breaking changes: new version mandatory.
- P1 implementation is authorized only after the P0 closure PR is merged.
