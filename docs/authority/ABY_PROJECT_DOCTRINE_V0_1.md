# ABY Project Doctrine V0.1

```text
DOCUMENT_ID: ABY_PROJECT_DOCTRINE_V0_1
AUTHORITY_CLASS: STABLE_PROJECT_DOCTRINE
FALSIFIABILITY: FIRST
A/B/Y != a/b/y
qA/qB/qY != a/b/y
y_hat != y_obs
```

## Project identity and purpose

ABY Cognitive Runtime exists to build the smallest reproducible, auditable
experimental runtime capable of testing whether explicit separation of macro
continuity, micro action, and dissipation-aware coordination improves
long-running LLM behavior under controlled compute, compared with strong
baselines.

ABY is explicitly not:

- a claim of AGI;
- a claim of consciousness;
- a proven cognitive law; or
- a product-first multi-agent framework.

## Falsifiability first

ABY must be designed so its hypotheses can fail. Every one of these is a valid
scientific outcome:

- ABY outperforms the controlled baselines;
- only some components help;
- A/B separation helps but the `r* approximately 2` hypothesis fails;
- Y fails to predict observed dissipation;
- semantic geometry adds no value;
- an ordinary mixture-of-agents performs equally well or better; or
- ABY has no material advantage.

Benchmarks must never be tuned to prove ABY. Engineering acceptance establishes
that an artifact meets its defined gate; it is not scientific validation.

## Permanent semantic distinctions

### Runtime roles versus measured state

```text
A / B / Y = software/runtime cognitive roles
a / b / y = measured or estimated normalized system state
```

Uppercase and lowercase semantics must never be conflated.

### Compute allocation versus measured state

```text
qA + qB + qY = 1
```

This is a compute-allocation vector. It is not the same statement as
`a + b + y = 1`, and `qY = 0.2` does not imply `y = 0.2`.

### Control ratio versus observed ratio

```text
r_c = w_A / w_B     configured control ratio
r_o = a / b         observed state ratio
```

The P0 `r* approximately 2` hypothesis is falsifiable, not a proven configured
constant. Setting `r_c = 2` does not imply that `r_o = 2` will be observed.

### Predicted versus observed dissipation

```text
y_hat = Y-Layer predicted dissipation
y_obs = post-episode observed dissipation inferred from independent evidence
```

Independent observed evidence may include rework, contradiction, failed calls,
state inconsistency, duplicate work, user correction, recovery effort, or
evidence gaps. Never set `y_obs` equal to Y's own prediction. The research
question is whether `y_hat` predicts `y_obs`; if it does not, Y must be revised
or rejected.

## A/B/Y role doctrine

### A — Macro Boundary / Continuity

A represents goals, constraints, facts, identity, history, relations, long-term
state, and invariants. It asks: **What must remain globally coherent?**

### B — Micro Direction / Action

B represents intent, action, local plans, candidates, tool intent, local facts,
and uncertainty. It asks: **What should the system do now?**

### Y — Dissipation Field

Y models likely fact conflict, constraint conflict, goal drift, memory mismatch,
causal breaks, evidence gaps, uncertainty, rework risk, and semantic mismatch. It
asks: **Where is semantic or cognitive dissipation likely to occur?**

A and B provide anchors and directions. Y shapes cost and geometry. Y is not a
third answer-voting agent and is not an unquestioned judge.

## Shared-state and authority doctrine

All future lanes follow:

```text
READ IMMUTABLE SNAPSHOT
-> PROPOSE
-> ALIGN / RESOLVE
-> COMMIT
```

A cannot directly commit memory. B cannot directly mutate authoritative world
state. Y cannot directly commit or reject authoritative state. Side effects
remain intents until a commit authority accepts them.

## Baseline discipline

The controlled baseline and ablation ladder is:

```text
S0 = Single LLM
S1 = Single LLM + Shared Memory/RAG
S2 = Conventional Multi-LLM / MoA
S3-A = ABY + non-geodesic structured resolver
S3-B = ABY + geodesic resolver
```

This separates possible gains from memory, extra model calls, multi-model
aggregation, functional lane separation, semantic geometry, dissipation
prediction, and adaptive compute. Comparisons must control compute, cost,
latency, concurrency, provider failures, and evidence quality.

## Forbidden conceptual shortcuts

None of the following may be treated as completing or proving ABY:

- three agents chatting recursively;
- majority vote among A/B/Y;
- Y acting as a third answer or an unquestioned judge;
- embedding each whole LLM output as one vector and calling it a semantic
  manifold;
- calling a single cosine-similarity score a geodesic;
- direct shared-state mutation by lanes;
- hidden LLM repair or judge calls that are not counted;
- treating `qA/qB/qY` as `a/b/y`;
- treating Y's prediction as observed `y`;
- treating `r_c` as observed `r_o`; or
- treating an accepted engineering milestone as scientific proof.

## Versioning rule

Material changes require a new doctrine version or an explicit revision with a
reason. Preserve prior authority and history where useful. Never silently turn
an experimental hypothesis into a validated law.
