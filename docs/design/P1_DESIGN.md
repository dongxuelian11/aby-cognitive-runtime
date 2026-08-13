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

## P1.2 decisions (S0 Single-LLM baseline, PR pending review)

1. **S0 purity definition** — exactly one logical model inference per normal
   successful episode; one fixed versioned prompt `S0_PROMPT_V0_1` (task-only
   instruction, no theory/memory/reflection wording); no long-term memory, no
   RAG, no MoA aggregation, no A/B/Y lane frames, no tools, no judge/verifier
   second call, no best-of selection. Prior-episode history only if the
   dataset input itself carries it.
2. **Provider abstraction** — neutral `LLMProvider.generate(LLMRequest) ->
   LLMResponse` with generic fields (model, messages, temperature,
   max_output_tokens, timeout, optional seed, bounded secret-free metadata);
   normalized response exposes content/provider/model/finish_reason/usage/
   request id/latency. Shared by all future systems.
3. **OpenAI-compatible scope** — one vendor-neutral `chat/completions` HTTP
   adapter (stdlib urllib only; no vendor SDK). Config: base_url, model,
   api_key_env, timeout, temperature, max_output_tokens, seed.
4. **Secret handling** — credentials read from environment variables at
   execution time only; committed config stores only the env-var NAME
   (`api_key_env = "ABY_LLM_API_KEY"`); keys never enter requests' metadata,
   responses, events, errors, or artifacts; no silent fake fallback.
5. **Prompt versioning** — `S0_PROMPT_V0_1` frozen with recorded
   `prompt_version` + `prompt_sha256` in episode metadata.
6. **Generation controls** — temperature/max_output_tokens/requested seed
   recorded honestly; no determinism claim beyond what the provider
   guarantees; experiment seed is distinct from provider seed.
7. **Usage semantics** — truthful propagation: input/output/total tokens
   (when provider reports them), provider latency; frozen `TelemetryRecord`
   carries tokens + latency + tool_calls=0; `logical_model_calls` and
   `transport_retries` live in episode metadata + `model_request_*` events
   (the frozen wire schema has no such fields and must not change).
8. **Logical-call counting** — `logical_model_calls = 1` per S0 episode;
   transport retries counted separately and never produce multiple
   successful candidate answers.
9. **Retry semantics** — bounded transport retries only (default 1) for
   transient `NETWORK_ERROR` / `PROVIDER_TIMEOUT`; recorded as
   `transport_retries`; first success wins.
10. **Real-provider smoke policy** — exactly one tiny bounded episode only if
    a credential already exists in the environment; otherwise
    `NOT_RUN_NO_CREDENTIALS`; the user is never asked for secrets.
11. **Error normalization** — `AUTHENTICATION_ERROR / RATE_LIMITED /
    PROVIDER_TIMEOUT / NETWORK_ERROR / INVALID_PROVIDER_RESPONSE /
    PROVIDER_ERROR`; no secret-bearing data in error messages.

## P1.2 bounded corrections (PR #3)

1. **Offline dry-run boundary** — `aby experiment dry-run` accepts only
   deterministic offline systems. An S0 `openai_compat` config is rejected
   before credential resolution or transport, even when its credential exists.
   Explicit S0 execution uses `aby run --config <config>`; non-S0 systems remain
   reserved.
2. **Two distinct timeouts, one request authority** —
   `metadata.provider.timeout_seconds` is normalized by S0 into
   `LLMRequest.timeout_seconds`, and `OpenAICompatProvider` passes that exact
   request value to HTTP transport. Top-level `ExperimentConfig.timeout_seconds`
   remains the independent outer bound applied by `EpisodeRunner`; neither
   silently substitutes for the other.
3. **Usage availability** — provider responses and S0 result metadata carry
   `usage_available`. Missing provider usage remains numerically compatible with
   the frozen telemetry fields but is explicitly marked unavailable, never
   interpreted as measured zero usage.
4. **Prompt correction** — `S0_PROMPT_V0_1` is the stable generic system message
   `Answer the supplied task directly and correctly.` The episode task appears
   only in the user message; prompt hash evidence is computed from the corrected
   constant.
5. **Offline semantic validation** — `aby experiment validate` validates S0
   provider type, required `openai_compat` fields, and bounded numeric settings
   without reading credentials or invoking network transport.

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
