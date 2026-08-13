# ABY Target Architecture — P1 Hypothesis V0.1

```text
DOCUMENT_ID: ABY_TARGET_ARCHITECTURE_P1_HYPOTHESIS_V0_1
STATUS:
GEODESIC_COORDINATION_HYPOTHESIS
EXPERIMENTAL
NOT_P0_AUTHORITY
NOT_SCIENTIFICALLY_VALIDATED
```

This document records the current P1 research and implementation direction. It
does not rewrite frozen P0 schemas, prove the architecture, or authorize future
phases ahead of their gates.

## Target pipeline

```text
                         USER / WORLD
                              |
                              v
                     Immutable Snapshot S_n
                              |
                +-------------+-------------+
                |             |             |
                v             v             v
             A-LLM          B-LLM          Y-LLM
             Macro          Micro       Dissipation
             Boundary       Action         Field
                |             |             |
                v             v             v
           MacroFrame     ActionFrame     FieldFrame
                \             |             /
                 \            |            /
                  +-----------+-----------+
                              |
                              v
                     Semantic Atomizer
                              |
                              v
                        Semantic IR
                              |
                              v
                       Shared Encoder
                              |
                              v
              Shared Semantic Manifold / Atlas
                              |
                              v
                  Relational / Manifold Matcher
                              |
                              v
                  Y-conditioned Directed Geometry
                     (Y Dissipation Geometry)
                              |
                              v
            Minimum-Dissipation Geodesic Resolver
                              |
                              v
                       Resolved State z*
                              |
                   +----------+----------+
                   |                     |
                   v                     v
               Response              Action Intent
                                         |
                                         v
                                  Commit Barrier
                                         |
                                         v
                                        S_n+1
```

## Semantic Atomizer and Semantic IR

Long model outputs must not be embedded as single opaque vectors. The first
dedicated P1 semantic layer should atomize outputs into typed structures such as:

```text
GOAL
CONSTRAINT
FACT
CLAIM
ENTITY
RELATION
INTENT
ACTION
EVIDENCE
UNCERTAINTY
```

Expected future IR fields may include `atom_id`, `atom_type`, `content`, entity
references, relation/predicate, target references, `source_lane`,
`evidence_refs`, confidence, uncertainty, scope, temporal scope, authority, and
provenance.

This is a P1 design direction, not a P0 schema rewrite. The P0 frames remain
frozen.

## Shared semantic geometry

Three heterogeneous LLMs must not be assumed to share hidden-state coordinates.
The initial engineering direction is:

```text
structured atoms
-> independent shared external encoder
-> normalized representations
-> local neighborhoods
-> semantic graph / manifold atlas
```

Prefer auditable local relational structure to a claim of a perfect universal
global manifold. V0 may use cosine or spherical distance, local k-nearest
neighbors, and a directed weighted graph. Gromov-Wasserstein or Fused GW,
Riemannian metrics, Finsler geometry, and learned manifold metrics are later
ablations only if evidence justifies them. Do not jump directly to complex
learned manifold geometry.

## Y Dissipation Geometry

Let `d0(i,j)` denote a base semantic distance. Y modifies directional path cost.
A conceptual, explicitly versioned cost can include:

```text
C(i -> j) =
  base semantic distance
  + conflict penalty
  + uncertainty penalty
  + evidence-gap penalty
  + drift penalty
  + other versioned dissipation terms
```

Y is geometry or field information, not a hard-vote oracle.

## Directionality

The architecture permits `C(i -> j) != C(j -> i)` because semantic, causal,
evidential, and authority transitions can be asymmetric. V0 therefore prefers a
directed weighted semantic graph. The full runtime must not be prematurely
described as a proven Riemannian system.

## Minimum-Dissipation Geodesic Resolver V0

The theoretical target is a minimum-dissipation path. Engineering V0 must remain
discrete and auditable:

```text
semantic atoms = nodes
semantic/evidence/constraint/causal relations = edges
Y = directed edge penalties
Dijkstra / A* / K-shortest path = discrete geodesic candidates
```

The resolver searches from macro-coherence anchors toward viable micro-action
anchors. Recursive natural-language debate is not required, and a single cosine
score is not a geodesic.

## Commit Barrier

The future authoritative mutation path is:

```text
READ SNAPSHOT
-> lane proposals
-> semantic alignment
-> resolver
-> publication/commit plan
-> Commit Barrier
-> S_n+1
```

The Commit Barrier owns side-effect authority. The existing P1.3 memory
finalizer is not automatically the final ABY Commit Barrier.

## Parallelism and fair comparison

A/B/Y are logically parallel over the same accepted immutable snapshot. Keep
logical parallelism, API/network concurrency, and hardware/GPU parallelism
distinct. Future latency claims must control baseline concurrency; S2's current
`sequential_v0` execution must not give ABY an unfair latency advantage.

## Scientific boundary and revision

Every component remains an experimental hypothesis until controlled evidence
supports it. Material architectural changes require a new version or explicit
revision with rationale; they must not silently modify P0 or manufacture prior
validation.
