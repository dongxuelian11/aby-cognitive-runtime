# CLAUDE.md — working conventions for this repository

## Project status (load-bearing)

- P0 theory freeze V0.1 was archived on 2026-08-13 but is NOT yet accepted.
- Do not implement lane / resolver / runner / provider logic until the P0 acceptance tracker (`docs/p0/P0_ACCEPTANCE_TRACKER.md`) is checked off.
- Skeleton rule: stubs raise `NotImplementedError` and cite the relevant P0 section.

## Conventions

- Python ≥ 3.10, pydantic v2, pytest. Flat package layout (`aby/`).
- Project docs are written in English; chat with the user in Chinese.
- `aby/contracts/` is frozen content (frames, telemetry record, measurement weights). Never edit without a new P0 version + changelog entry (`docs/p0/CHANGELOG.md`).
- Changing event weights also requires a new telemetry schema version (P0 §7.2).
- Telemetry field names must match `ABY_RUNTIME_TELEMETRY_V0.1` exactly (P0 §8).
- Uppercase A/B/Y = runtime lanes; lowercase a/b/y = state variables. Never conflate (P0 §4).
- Every episode must be replayable from the event log (P0 §15).
- Baselines: S0 single LLM, S1 + shared memory, S2 MoA, S3 ABY Fixed, S4 reserved for P5 (P0 §9).
- Resolver is deterministic/rule-based, not a fourth LLM; bounded retry limit (P0 §6).
- Falsifiability first, product complexity later (P0 §19).

## Key paths

- `docs/p0/` — frozen document, acceptance tracker, changelog
- `docs/design/P1_DESIGN.md` — P1 design draft with open questions (decide here, not ad hoc)
- `aby/contracts/` — frozen schemas (executable form of the freeze)
- `experiments/configs/` — experiment configs (schema NOT yet frozen)
