# P0 Changelog

## 2026-08-13 — P0 V0.1 formal acceptance closure

- Independent exact-source semantic review: `ABY_P0_EXACT_SOURCE_SEMANTIC_REVIEW_PASS`
  (baseline `e3eeae345e5e86cf5bcec6349991bd4c1fbb04ed`).
- P0 freeze items: 15 / 15 ACCEPTED (`docs/p0/P0_ACCEPTANCE_TRACKER.md`).
- Open-source licensing established: Apache License 2.0 (canonical text in `LICENSE`).
- P1 Experimental Harness becomes AUTHORIZED only after this closure PR is merged.
- Existing minimal EventLog append/replay implementation (`aby/events/`) accepted as:
  - `PRE_ACCEPTANCE_MINIMAL_REPLAY_SCAFFOLD_EXCEPTION`
  - `NON_SEMANTIC`
  - `NON_BLOCKING`
- No rollback or corrective lineage is required for that EventLog exception.
- No speculative theory changes in this closure.

## V0.1 — 2026-08-13 — DRAFT archived for freeze

- Archived `ABY_P0_THEORY_FREEZE_EXPERIMENTAL_ARCHITECTURE_V0_1.md` verbatim from upload.
- No edits to the frozen document are permitted.
- Acceptance is tracked in `P0_ACCEPTANCE_TRACKER.md` (15 items; accepted 2026-08-13,
  see closure entry above).

## Rules

- Any change to frozen content → new version (V0.2, V0.3, …) + changelog entry describing the delta.
- Event-weight changes (P0 §7.2) additionally require a new telemetry schema version.
- Frame/telemetry field renames are breaking changes: new version mandatory.
- "NOT FROZEN" items (e.g., frame list element schemas) may evolve during P1 without a P0 bump — see `docs/design/P1_DESIGN.md`.
