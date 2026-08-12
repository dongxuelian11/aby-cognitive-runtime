# P0 Changelog

## V0.1 — 2026-08-13 — DRAFT archived for freeze

- Archived `ABY_P0_THEORY_FREEZE_EXPERIMENTAL_ARCHITECTURE_V0_1.md` verbatim from upload.
- No edits to the frozen document are permitted.
- Acceptance is tracked in `P0_ACCEPTANCE_TRACKER.md` (15 items, all pending).

## Rules

- Any change to frozen content → new version (V0.2, V0.3, …) + changelog entry describing the delta.
- Event-weight changes (P0 §7.2) additionally require a new telemetry schema version.
- Frame/telemetry field renames are breaking changes: new version mandatory.
- "NOT FROZEN" items (e.g., frame list element schemas) may evolve during P1 without a P0 bump — see `docs/design/P1_DESIGN.md`.
