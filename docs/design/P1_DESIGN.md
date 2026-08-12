# P1 — Experimental Harness Design (DRAFT)

Status: **DRAFT** — nothing in this file is frozen. Decisions are deferred until P0 acceptance.
Scope source: P0 §17.

## Goal

Run S0 / S1 / S2 / S3 on the same task dataset under controlled, recorded compute budgets and produce one `ABY_RUNTIME_TELEMETRY_V0.1` trace per bounded episode.

## Module map (skeleton in place)

| Path | Responsibility | P0 § |
| ---- | -------------- | ---- |
| `aby/contracts/` | frozen lane frames, ResolveDecision, telemetry record, measurement model | 5, 6, 7, 8 |
| `aby/providers/` | provider abstraction (lanes may use different providers) | 15, 17 |
| `aby/events/` | append-only event log; replayability | 15, 16 |
| `aby/memory/` | episode store, structured facts, keyword retrieval | 14 |
| `aby/lanes/` | A/B/Y lane stubs | 5 |
| `aby/resolver/` | deterministic rule-based resolver, bounded retries | 6 |
| `aby/telemetry/` | runtime telemetry collector | 7, 8 |
| `aby/baselines/` | S0–S4 definitions + adapter stubs | 9 |
| `aby/runner/` | episode runner | 17 |
| `aby/cli.py` | minimal CLI | 17 |

## Open design questions (decide in P1, not now)

1. **Frame list elements.** P0 freezes field names and `[]` structure, not element schemas. What object goes inside `macro_state`, `conflicts`, `tool_requests`, …?
2. **Episode definition.** What is one "bounded episode" for each target task family?
3. **Event taxonomy.** Which event kinds are required to compute A_raw / B_raw / W_raw unambiguously from the event log?
4. **Compute budget enforcement.** How are qA / qB / qY measured and capped (tokens? cost? calls?)? P0 §4.3 records allocation but does not define enforcement.
5. **Provider API.** Sync vs async; how tool calls are represented; per-lane model config.
6. **Resolver rules.** The deterministic decision table mapping (frames, y, retry count) → `ResolveDecisionKind`.
7. **MoA baseline (S2).** Aggregation scheme for a conventional multi-LLM baseline without ABY lane semantics.
8. **User signal.** How `user_result` / `user_quality_score` are collected independently of ABY telemetry (fairness, P0 §10).
9. **Replay determinism.** Handling of nondeterministic LLM sampling during replay (P0 §15).
10. **Task families.** Initial dataset(s) for long-running information tasks (H2, P0 §12).

## Out of scope for P1 (P0 §17)

- polished product UI
- plugin marketplace
- autonomous background life
- advanced graph memory
- dynamic compute controller
- production deployment
- claims that ABY is validated
