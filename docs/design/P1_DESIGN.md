# P1 — Experimental Harness Design (DRAFT)

Status: **DRAFT** — P0 frozen content remains authoritative. P1.1 decisions below
are resolved on branch `feat/p1-1-experimental-harness-foundation` (PR pending review).
Scope source: P0 §17.

## Goal

Run S0 / S1 / S2 / S3 on the same task dataset under controlled, recorded compute budgets and produce one `ABY_RUNTIME_TELEMETRY_V0.1` trace per bounded episode.

## Module map

| Path | Responsibility | P0 § / stage |
| ---- | -------------- | ------------ |
| `aby/contracts/` | frozen lane frames, ResolveDecision, telemetry record, measurement model (untouched by P1.1) | 5, 6, 7, 8 |
| `aby/experiments/config.py` | versioned experiment config `ABY_EXPERIMENT_CONFIG_V1_0` | P1.1 |
| `aby/experiments/system.py` | neutral `SystemUnderTest` interface + offline null/echo/fixture systems | P1.1 |
| `aby/experiments/harness.py` | offline dry-run orchestration (runner → log → telemetry → artifacts) | P1.1 |
| `aby/experiments/artifacts.py` | per-episode artifact writer (5 files) | P1.1 |
| `aby/experiments/provenance.py` | exact code/config binding metadata | P1.1 |
| `aby/runner/` | bounded EpisodeRunner (lifecycle, timeout, failure capture) | P1.1 |
| `aby/events/` | append-only event log with replay + stable event IDs | 15, 16; P1.1 |
| `aby/telemetry/` | evidence-based collector into the frozen `TelemetryRecord` | 7, 8; P1.1 |
| `aby/providers/` | provider abstraction (stub; lanes may use different providers) | 15, 17 |
| `aby/lanes/` | A/B/Y lane stubs | 5 (P1.2+) |
| `aby/resolver/` | deterministic rule-based resolver, bounded retries | 6 (P1.2+) |
| `aby/memory/` | episode store, structured facts, keyword retrieval | 14 (P1.2+) |
| `aby/baselines/` | S0–S4 definitions + adapter stubs | 9 (P1.2+) |
| `aby/cli.py` | status, `experiment validate`, `experiment dry-run` | P1.1 |

## P1.1 decisions (resolved)

1. **Experiment config schema** — `ABY_EXPERIMENT_CONFIG_V1_0` (pydantic v2,
   `extra="forbid"` fail-closed, JSON round-trip, explicit version, no secret
   fields, no ABY-specific fields). Example: `experiments/configs/example_echo_system.json`.
2. **System-under-test interface** — neutral `SystemUnderTest.run_episode(EpisodeInput)
   -> EpisodeResult` with normalized concepts `output/status/error/tool_events/
   rework_events/metadata`. Offline deterministic systems (null/echo/fixture) exist
   only for tests/dry-runs and are not baselines.
3. **Episode lifecycle** — CREATED → STARTED → COMPLETED | FAILED | TIMED_OUT;
   immutable deterministic episode IDs `<experiment_id>-epNNNN`; seed_i =
   config.seed + i; bounded timeout via executor future; all exceptions captured
   into FAILED records; lifecycle events always emitted. No automatic retries in P1.1.
4. **Event taxonomy** — `episode_created / episode_started / episode_completed /
   episode_failed / episode_timed_out / tool_call / rework`; append-only; stable
   event IDs `<episode_id>#<seq>`; replay returns deep copies (historical events
   immutable); in-memory + JSONL artifact output (no DB in P1.1).
5. **Artifact layout** — `artifacts/experiments/<experiment_id>/<episode_id>/`
   containing `config.json`, `events.jsonl`, `result.json`, `telemetry.json`,
   `provenance.json`; `artifacts/` is Git-ignored.
6. **Telemetry-unavailable convention** — for systems without ABY instrumentation,
   `A_raw/B_raw/W_raw` and `a/b/y/r` stay at frozen-schema defaults (0 / 0.0),
   meaning "measurement not applicable" — never "measured zero"; `qA/qB/qY` stay
   0.0. Cross-system comparisons use the uniformly collected observable counters
   (tool calls, failures, rework, latency, tokens). The convention is identical
   for every baseline label and cannot bias S0/S1/S2 against S3.
7. **Seed/reproducibility** — deterministic per-episode seed propagation;
   determinism is verified on normalized content (timestamps excluded);
   provenance binds `repo_commit`, `config_sha256`, schema version, system_id,
   seed, python/platform, start/end times.
8. **CLI** — `aby status` (authority state + P1.1 candidate status),
   `aby experiment validate <config>` (offline, non-zero on invalid),
   `aby experiment dry-run <config>` (offline deterministic only; unknown
   system_id fails closed). `aby run` remains reserved for later P1 stages.

## P1.1 corrections (PR #2, independent review round 2)

1. **Timeout cancellation model** — soft timeout with non-blocking executor
   shutdown: on timeout the episode is `TIMED_OUT` and the runner returns
   promptly; the detached worker may finish in the background but its late
   result is discarded and can never mutate the committed record, event log,
   or artifacts. Python threads cannot be hard-killed; this model is honest
   about that (no fake "hard cancellation").
2. **EventLog immutability guarantee** — strict immutable boundary:
   `append` deep-copies the incoming event and returns an independent deep
   copy; `replay` returns deep copies. Caller-owned objects, return values,
   and nested payloads can never mutate stored history.
3. **Provenance source-binding states** — `source_binding` ∈
   {`EXACT_CLEAN_COMMIT`, `NON_EXACT_DIRTY`, `UNAVAILABLE`} with explicit
   `worktree_state` ∈ {CLEAN, DIRTY, UNKNOWN}; dirty tracked worktrees also
   record `tracked_diff_sha256`. Untracked policy (conservative): any
   untracked non-ignored file ⇒ DIRTY; git-ignored generated artifacts
   (e.g. `artifacts/`, `.pytest_cache/`) do not affect exactness.
4. **Artifact identifier/path containment** — `experiment_id` and `episode_id`
   must match `[A-Za-z0-9._-]+` (never empty, `.`, or `..`); artifact
   directories are additionally containment-checked to resolve strictly
   inside `<artifacts_root>/experiments/`.

## Still open for later P1 stages

- MoA baseline (S2) aggregation scheme.
- qA/qB/qY compute-budget enforcement/measurement.
- Provider API final shape (sync vs async; tool-call representation).
- Episode definition and task datasets per task family (real data).
- User signal collection channel (`user_result`/`user_quality_score` independence, P0 §10).
- Replay determinism under nondeterministic LLM sampling.
- Retry policy (deliberately absent in P1.1; requires explicit future design).
- Resolver decision table (deterministic rules) — with S3 in P1.2+.
- Durable event-log backend (in-memory + JSONL chosen for P1.1 simplicity).

## Out of scope for P1 (P0 §17)

- polished product UI
- plugin marketplace
- autonomous background life
- advanced graph memory
- dynamic compute controller
- production deployment
- claims that ABY is validated
