# ABY repository authority index

This directory is the canonical navigation layer for ABY doctrine, the current
P1 architecture hypothesis, and phase sequencing. It does not replace live Git
or GitHub state.

## Authority hierarchy

### 1. P0 frozen authority

Canonical source:
`docs/p0/ABY_P0_THEORY_FREEZE_EXPERIMENTAL_ARCHITECTURE_V0_1.md`

```text
STATUS: FROZEN
PROJECT_AUTHORITY: ACCEPTED
SCIENTIFIC_HYPOTHESES: UNVALIDATED
```

P0 is the accepted frozen project authority. Acceptance means the theory and
contracts are controlled; it does not mean their scientific hypotheses are true.

### 2. Stable project doctrine

Canonical source: `ABY_PROJECT_DOCTRINE_V0_1.md`

This document defines why ABY exists, what it is intended to test or falsify,
permanent conceptual distinctions, scientific discipline, and forbidden
conceptual shortcuts.

### 3. Current P1 target-architecture hypothesis

Canonical source: `ABY_TARGET_ARCHITECTURE_P1_HYPOTHESIS_V0_1.md`

It records the current research and implementation direction:

```text
A/B/Y parallel
-> Semantic Atomizer / Semantic IR
-> Shared Semantic Manifold / Atlas
-> relational/manifold matching
-> Y Dissipation Geometry
-> Minimum-Dissipation Geodesic Resolver
-> Commit Barrier
```

Its status is strictly:

```text
GEODESIC_COORDINATION_HYPOTHESIS
EXPERIMENTAL
NOT_P0_AUTHORITY
NOT_SCIENTIFICALLY_VALIDATED
```

### 4. Phase gates and roadmap

Canonical source: `ABY_PHASE_GATES_AND_ROADMAP_V0_1.md`

This document defines accepted sequencing, current boundaries, and the gates
that future work must not skip.

### 5. Exact runtime and development state

Exact Git/GitHub branch, commit, tree, PR, and check state must be verified live.
Do not store a self-proclaimed "current master SHA" in durable doctrine as if it
were permanently authoritative.

## Conflict and change rules

- P0 frozen authority cannot be retroactively overridden by P1 hypothesis docs.
- A task-specific bounded scope may select work within the roadmap, but may not
  silently rewrite project doctrine.
- If a new architectural discovery contradicts the current P1 target
  architecture, document it as a new hypothesis or explicit revision; do not
  silently mutate meaning.
- When the task prompt, repository authority, P0 freeze, or live Git state
  disagree, fail closed and report the conflict.

## Versioning

Current canonical versions are:

```text
ABY_PROJECT_DOCTRINE_V0_1
ABY_TARGET_ARCHITECTURE_P1_HYPOTHESIS_V0_1
ABY_PHASE_GATES_AND_ROADMAP_V0_1
```

A material change must create a new version or explicit revision, record why,
and preserve prior authority/history where useful. An experimental hypothesis
must never be silently relabeled as a validated law.
