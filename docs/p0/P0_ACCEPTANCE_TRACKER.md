# P0 Acceptance Tracker

Source: `ABY_P0_THEORY_FREEZE_EXPERIMENTAL_ARCHITECTURE_V0_1.md` §16.

P0 is complete only when every item below is explicitly accepted.
**No implementation begins before acceptance** (P0 §16).

Status legend: `[ ]` not yet accepted · `[x]` accepted

| # | Frozen item | P0 § | Acceptance date | Status |
|---|-------------|------|-----------------|--------|
| 1 | Theory variables and symbols (a, b, y, r, normalized state) | 2 | | [ ] |
| 2 | Uppercase/lowercase distinction (layers vs state variables) | 4 | | [ ] |
| 3 | Compute-budget notation (qA, qB, qY) | 4.3 | | [ ] |
| 4 | Lane semantics (A/B/Y missions and forbidden behavior) | 5 | | [ ] |
| 5 | Lane I/O schemas (MacroFrame, ActionFrame, DissipationFrame) | 5 | | [ ] |
| 6 | Resolver decisions (ResolveDecision + allowed kinds) | 6 | | [ ] |
| 7 | Telemetry schema (ABY_RUNTIME_TELEMETRY_V0.1) | 8 | | [ ] |
| 8 | Initial event weights (A_raw / B_raw / W_raw) | 7.2 | | [ ] |
| 9 | Baseline definitions (S0–S4) | 9 | | [ ] |
| 10 | Experimental fairness rules | 10 | | [ ] |
| 11 | Evaluation metrics | 11 | | [ ] |
| 12 | Falsifiable hypotheses (H1–H6) | 12 | | [ ] |
| 13 | Explicit non-claims | 13 | | [ ] |
| 14 | P1 memory boundary (episode store, facts, keyword retrieval) | 14 | | [ ] |
| 15 | Replayability requirement | 15 | | [ ] |

## Freeze record

| Version | Date | Decision | Approver | Notes |
|---------|------|----------|----------|-------|
| V0.1 | 2026-08-13 | PENDING | — | Archived verbatim from upload; no edits permitted |

## How to accept

1. Review each item against the frozen document section listed.
2. Check the box and fill in the acceptance date.
3. Record approver and decision in the freeze record (PENDING → ACCEPTED).

Any change to an accepted item requires a new version (V0.2) and a `CHANGELOG.md` entry.
Event-weight changes additionally require a new telemetry schema version (P0 §7.2).
