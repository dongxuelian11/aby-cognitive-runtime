# ABY Cognitive Runtime — P0 Theory Freeze & Experimental Architecture V0.1

**Status:** DRAFT-FOR-FREEZE  
**Project:** ABY Cognitive Runtime  
**Phase:** P0 — Theory Freeze + Experimental Architecture  
**Purpose:** Freeze the minimum falsifiable theory, system boundaries, lane contracts, telemetry, baselines, and P1 entry gate before implementation.

---

## 1. Project Thesis

ABY Cognitive Runtime tests whether a long-running LLM system benefits from separating cognition into three heterogeneous lanes:

- **A / Macro Continuity Lane** — maintains long-horizon continuity, world state, constraints, identity, history, and cross-episode structure.
- **B / Micro Action Lane** — handles immediate perception, local reasoning, execution, tools, and task progress.
- **Y / Dissipation Observer Lane** — observes unresolved mismatch, conflict, drift, redundancy, rework risk, and uncertainty between macro state, micro action, evidence, and world events.

The core hypothesis is that system quality depends not only on model capability, but on the balance between effective macro constraint, effective micro action, and unresolved dissipation.

The project explicitly does **not** assume that three LLMs are inherently superior to one LLM. The architecture must beat strong baselines under controlled budgets to justify itself.

---

## 2. Theory Core

### 2.1 Normalized state

Let:

- `a` = effective macro-order / continuity contribution
- `b` = effective micro-action / local emergence contribution
- `y` = unresolved dissipation / mismatch / waste

with:

```text
a >= 0
b >= 0
y >= 0
a + b + y = 1
```

Define:

```text
r = a / b
```

Current central hypothesis:

```text
r* ≈ 2
```

This value is a **testable hypothesis**, not a law.

The generalized form is:

```text
r* = k(task_family, difficulty, risk, system_state, environment)
```

The project must permit data to show that `k != 2`.

---

## 3. Hypothesized Phase Zones

The following zones are experimental labels only:

```text
1.8 <= r <= 2.2  : OPTIMAL_HYPOTHESIS
1.5 <= r < 1.8   : HEALTHY_LOW
2.2 <  r <= 2.5  : HEALTHY_HIGH
1.0 <= r < 1.5   : TURBULENT_HYPOTHESIS
r < 1.0          : LOW_SIDE_INSTABILITY_HYPOTHESIS
2.5 < r <= 3.0   : GLASSY_HYPOTHESIS
r > 3.0          : HIGH_SIDE_FREEZE_HYPOTHESIS
```

No production behavior may be gated by these labels during P0–P4.

---

## 4. Critical Distinction: Lanes vs State Variables

### 4.1 Uppercase A/B/Y

`A-Layer`, `B-Layer`, and `Y-Layer` are software/runtime components.

They may consume LLM calls, tools, memory, deterministic logic, or other compute.

### 4.2 Lowercase a/b/y

`a`, `b`, and `y` are measured or estimated system-state variables.

They are **not** equal to compute allocation.

For example:

```text
Y-Layer uses 20% of tokens
```

does **not** imply:

```text
y = 0.20
```

### 4.3 Compute allocation

Define a separate compute vector:

```text
qA + qB + qY = 1
```

where:

- `qA` = compute budget assigned to A-Layer
- `qB` = compute budget assigned to B-Layer
- `qY` = compute budget assigned to Y-Layer

A major later-stage research question is:

```text
(qA, qB, qY)
    -> (a, b, y)
    -> performance
```

P0 freezes this distinction permanently.

---

## 5. Lane Semantics

## 5.1 A-Layer — Macro Continuity

### Mission

Maintain the long-horizon state needed for continuity without directly solving the current task unless required for macro interpretation.

### Typical inputs

- current event
- long-term memory
- persistent facts
- previous accepted state
- long-term goals
- constraints
- relationship history
- world timeline
- prior commitments
- selected evidence

### Output contract: `MacroFrame`

Minimum fields:

```json
{
  "macro_state": [],
  "relevant_history": [],
  "active_constraints": [],
  "long_term_goals": [],
  "continuity_risks": [],
  "candidate_interpretations": [],
  "confidence": 0.0,
  "evidence_refs": []
}
```

### Forbidden behavior

- Must not emit the final user-facing answer as its primary function.
- Must not receive the full B scratch context by default.
- Must not invent long-term state when evidence is missing.
- Must not silently overwrite persistent memory.

---

## 5.2 B-Layer — Micro Action

### Mission

Solve the immediate task using current input, local context, tools, and only the minimum macro constraints required.

### Typical inputs

- current user request or event
- current task
- available tools
- local working context
- selected constraints from A
- relevant evidence

### Output contract: `ActionFrame`

Minimum fields:

```json
{
  "current_intent": "",
  "local_plan": [],
  "candidate_actions": [],
  "tool_requests": [],
  "expected_result": "",
  "local_uncertainties": [],
  "confidence": 0.0,
  "evidence_refs": []
}
```

### Forbidden behavior

- Must not load all historical memory by default.
- Must not autonomously redefine long-term goals.
- Must not treat stale memory as current authority.
- Must not use A's uncertainty as permission to fabricate.

---

## 5.3 Y-Layer — Dissipation Observer

### Mission

Detect unresolved inconsistency and waste across A, B, memory, tools, evidence, and previous state.

Y is not a third answer generator.

### Typical inputs

- `MacroFrame`
- `ActionFrame`
- current event
- memory evidence
- tool evidence
- prior episode state
- execution trace

### Output contract: `DissipationFrame`

Minimum fields:

```json
{
  "conflicts": [],
  "uncertainties": [],
  "goal_drift": [],
  "memory_mismatch": [],
  "factual_mismatch": [],
  "redundancy": [],
  "rework_risk": [],
  "context_drift": [],
  "unresolved_tension": [],
  "estimated_y": 0.0,
  "confidence": 0.0,
  "recommended_resolution_targets": []
}
```

### Forbidden behavior

- Must not directly block execution.
- Must not own final control authority.
- Must not inflate `y` merely because information is incomplete.
- Must distinguish normal uncertainty from harmful unresolved mismatch.
- Must not recursively request unlimited verification.

---

## 6. Resolver

### 6.1 P0/P1 design

The initial `ABY Resolver` must be deterministic or rule-based.

It is not a fourth master LLM.

### 6.2 Inputs

- `MacroFrame`
- `ActionFrame`
- `DissipationFrame`
- current evidence
- runtime telemetry

### 6.3 Output contract: `ResolveDecision`

```json
{
  "decision": "EXECUTE_B",
  "macro_constraints_applied": [],
  "unresolved_conflicts": [],
  "requires_more_evidence": false,
  "requested_evidence": [],
  "memory_write_candidates": [],
  "reason_codes": []
}
```

### 6.4 Allowed initial decisions

```text
EXECUTE_B
REQUEST_EVIDENCE
REQUEST_A_REFRESH
REQUEST_B_REPLAN
DEFER
RETURN_UNCERTAINTY
```

No recursive loop may run without a bounded retry limit.

---

## 7. Measurement Model

P0 does not claim access to hidden model reasoning or true internal compute.

The first measurement system uses observable runtime events.

### 7.1 Raw observable measures

Use:

- `A_raw` = observable macro-maintenance / global-coherence activity
- `B_raw` = observable task-progress / local-action activity
- `W_raw` = observable waste / rework / failed-action activity

Then:

```text
T = A_raw + B_raw + W_raw

a = A_raw / T
b = B_raw / T
y = W_raw / T

r = A_raw / B_raw
```

### 7.2 Initial event weighting

#### A_raw

```text
necessary authority/context read       +1
task decomposition/state alignment     +1
boundary/consistency check             +1
necessary verification                 +1
conflict resolution/state rebuild      +2
```

#### B_raw

```text
effective execution step               +1
effective tool call                    +1
completed explicit subgoal             +1
usable deliverable                     +2
```

#### W_raw

```text
failed/invalid call                     +1
duplicate work                          +1
scope/goal drift                        +2
rework caused by misunderstanding       +2
discarded/unusable output               +3
```

This is an instrument calibration, not a theoretical law.

Changing weights requires a new telemetry schema version.

---

## 8. Telemetry Contract

Each bounded episode produces one primary trace.

```json
{
  "schema": "ABY_RUNTIME_TELEMETRY_V0.1",
  "episode_id": "",
  "task_family": "",
  "difficulty": "",
  "risk": "",
  "model_config": {},
  "memory_config": {},
  "qA": 0.0,
  "qB": 0.0,
  "qY": 0.0,
  "A_raw": 0,
  "B_raw": 0,
  "W_raw": 0,
  "a": 0.0,
  "b": 0.0,
  "y": 0.0,
  "r": 0.0,
  "latency_ms": 0,
  "input_tokens": 0,
  "output_tokens": 0,
  "tool_calls": 0,
  "failed_tool_calls": 0,
  "rework_count": 0,
  "continuity_errors": 0,
  "factual_errors": 0,
  "user_result": null,
  "user_quality_score": null
}
```

---

## 9. Baselines

ABY must be compared against strong, controlled baselines.

### S0 — Single LLM

Same provider/model family, no long-term memory beyond ordinary context.

### S1 — Single LLM + Shared Memory/RAG

Same memory source and retrieval budget available to ABY.

### S2 — Conventional Multi-LLM / MoA

Multiple model outputs aggregated without ABY semantic lane separation.

### S3 — ABY Fixed

A/B/Y lanes with fixed compute allocation and deterministic Resolver.

### S4 — ABY Adaptive

Reserved for P5. Compute allocation changes based on validated state signals.

P0–P4 must not assume S4 is superior.

---

## 10. Fairness Rules

To make experimental results interpretable:

- Same task dataset across systems.
- Same or tightly bounded model families.
- Same external tools.
- Same memory corpus where applicable.
- Compute/token budget must be recorded.
- Latency and API cost must be recorded.
- No system may receive privileged labels unavailable to another unless the experiment explicitly tests that feature.
- User evaluation must be independent of ABY telemetry.
- ABY may not be tuned on test episodes.

---

## 11. Evaluation Dimensions

### 11.1 Task capability

- task completion
- correctness
- tool success
- user acceptance
- explicit test pass rate

### 11.2 Long-term continuity

- cross-episode factual consistency
- reference resolution
- persistent goal retention
- stale-memory error rate
- contradiction rate
- state drift

### 11.3 Efficiency

- total tokens
- cost
- latency
- tool calls
- memory reads
- retries
- rework

### 11.4 ABY-specific

- distribution of `r`
- distribution of `y`
- performance vs `r`
- performance vs `y`
- low-side failure signatures
- high-side failure signatures
- perturbation recovery time
- estimated optimum `k`

---

## 12. Falsifiable Hypotheses

### H1 — Finite optimum

Performance is not monotonic in `r`; a finite optimum exists.

### H2 — Approximate central attractor

For selected long-running information tasks, the optimum `k` is near 2.

### H3 — Dissipation independence

At similar `r`, higher `y` predicts lower performance and/or higher rework.

### H4 — Asymmetric failure

Low `r` is associated more strongly with drift, inconsistency, and turbulent behavior.

High `r` is associated more strongly with rigidity, latency, overconstraint, and glassy behavior.

### H5 — Recovery dynamics

Under perturbation, healthy systems tend to recover toward a stable `k`.

### H6 — ABY architecture benefit

Under comparable compute budgets, S3 ABY Fixed outperforms at least one strong baseline on continuity and/or rework without unacceptable loss in cost or latency.

Any of H1–H6 may fail without invalidating unrelated hypotheses.

---

## 13. Explicit Non-Claims

P0 does not claim:

- `r = 2` is a universal law.
- `a`, `b`, or `y` measure physical energy.
- the architecture models human consciousness.
- three LLMs are necessary.
- Y must always be implemented by an LLM.
- the model generalizes beyond tested systems.
- phase labels correspond literally to fluid turbulence or physical glass transitions.

Those terms are operational analogies until supported by data.

---

## 14. Memory Strategy for P1

P1 must use a deliberately simple shared memory layer to avoid confounding.

Minimum:

```text
Episode Store
Structured Facts
Keyword Retrieval
Optional Embedding Retrieval
```

Graphiti, Letta, or advanced temporal memory are deferred until the ABY skeleton is measurable.

Memory adapters must remain replaceable.

---

## 15. Runtime Principles

- Event-driven architecture.
- A/B/Y are logically parallel lanes.
- Different lanes may use different model providers.
- Different lanes may run at different frequencies.
- B is typically highest-frequency.
- Y may be lightweight and frequent.
- A may be slower and event-triggered.
- No lane owns global authority.
- Resolver remains bounded.
- Every episode is replayable from stored events and configuration.

---

## 16. P0 Acceptance Gate

P0 is complete only when the following are frozen:

- [ ] Theory variables and symbols
- [ ] Uppercase/lowercase distinction
- [ ] Compute-budget notation
- [ ] Lane semantics
- [ ] Lane I/O schemas
- [ ] Resolver decisions
- [ ] Telemetry schema
- [ ] Initial event weights
- [ ] Baseline definitions
- [ ] Experimental fairness rules
- [ ] Evaluation metrics
- [ ] Falsifiable hypotheses
- [ ] Explicit non-claims
- [ ] P1 memory boundary
- [ ] Replayability requirement

No implementation should begin before these are accepted as P0 V0.1.

---

## 17. P1 Scope After Freeze

**P1 — Experimental Harness**

Build only enough infrastructure to run and compare:

```text
S0 Single LLM
S1 Single LLM + Shared Memory
S2 Conventional Multi-LLM / MoA
S3 ABY Fixed
```

P1 must include:

- provider abstraction
- event log
- episode runner
- minimal shared memory
- A/B/Y lane stubs
- deterministic Resolver
- telemetry collector
- baseline adapters
- reproducible experiment config
- minimal CLI or developer UI

P1 explicitly excludes:

- polished product UI
- plugin marketplace
- autonomous background life
- advanced graph memory
- dynamic compute controller
- production deployment
- claims that ABY is validated

---

## 18. Decision Rule

The project advances from experimental architecture to adaptive runtime only if data shows a reproducible advantage or a reproducible novel diagnostic signal.

Possible valid outcomes include:

```text
ABY architecture advantage confirmed
Only Y has strong predictive value
A/B separation helps but r*=2 is rejected
Optimal k differs by task family
ABY has no material advantage
```

All are legitimate research outcomes.

---

## 19. Frozen North Star

> Build the smallest reproducible system that can determine whether Macro Continuity A, Micro Action B, and Dissipation Observer Y form a useful cognitive runtime architecture under controlled LLM compute budgets.

The project must optimize for **falsifiability first, product complexity later**.
