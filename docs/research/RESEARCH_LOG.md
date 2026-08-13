# Research Log

Template per entry:

```text
Date: YYYY-MM-DD
Hypothesis: H# (or "exploratory")
Experiment: name + baseline(s)
Config: experiments/configs/<file>
Result: key numbers (r, y, scores) + trace refs
Decision: accept / reject / continue / modify
```

---

## 2026-08-13 — Project established

- P0 V0.1 archived for freeze; acceptance pending (`docs/p0/P0_ACCEPTANCE_TRACKER.md`).
- P1 skeleton created (frozen contracts only); no experiments run yet.

## 2026-08-13 — Baseline foundation closed; P1 hypothesis made repo-native

- P1.1–P1.4 baseline foundation accepted; S0/S1/S2 now form the controlled
  baseline set.
- The latest geodesic coordination architecture was promoted to repository-level
  P1 experimental-hypothesis authority under `docs/authority/`.
- This promotion is not scientific validation and does not modify frozen P0.

## 2026-08-13 — P1.5 shared semantic geometry foundation implemented candidate

- PRE-P1.5 repository-authority lock and S1 publication/finalization atomicity
  hardening are accepted. P1.5 is an `IMPLEMENTED_CANDIDATE`, not accepted.
- Added Semantic Atom / IR `p1.5-v0.1`, deterministic P0-frame atomization, a
  provider-neutral shared encoder protocol, normalized spherical points,
  directed local kNN atlas, bounded cross-lane match candidates, and dedicated
  deterministic geometry evidence artifacts.
- The offline `reference_hashing/p1.5-v0.1` encoder is explicitly
  `REFERENCE_ONLY_NOT_SEMANTIC_QUALITY_EVIDENCE`; it supports infrastructure
  replay tests and makes no semantic-quality or scientific-validity claim.
- No Y-conditioned geometry, edge penalty, geodesic resolver, live A/B/Y lane,
  P1.6, S3, or Commit Barrier is implemented. The frozen P0 documents and
  contracts remain outside the write set.
- Scientific result: `NOT_RUN`. This candidate creates a coordinate/evidence
  substrate only; it does not test ABY effectiveness or superiority.

## 2026-08-13 — P1.5 PR #8 bounded semantic/locality correction candidate

- Corrected Y `recommended_resolution_targets` to the non-executable
  `DISSIPATION_TARGET` atom type. Y emits no `INTENT` or `ACTION`; frozen P0
  fields remain unchanged and `estimated_y` remains outside geometry.
- Corrected cross-lane matching to require a forward or reverse directed local
  kNN atlas edge. Reverse-only adjacency is eligible; absence of both directions
  yields no candidate and no global fallback.
- Bound `frame-atomizer-v0.1`, `atlas-local-cross-lane-v0.1`, and
  `matches_per_source` into bundle fingerprints and artifact manifests.
- Added relational integrity validation distinct from self-hashing: atom/point
  identities, encoder provenance, canonical atlas evidence, endpoint lanes, and
  atlas-local matches must be internally consistent.
- This is an engineering correction to an unaccepted candidate, not scientific
  validation. Y costs, geodesic resolution, live lanes, P1.6, and S3 remain
  unimplemented.

## 2026-08-13 — P1.5 accepted; P1.6 parallel runtime implemented candidate

- P1.5 Shared Semantic Geometry Foundation is independently accepted.
- P1.6 advances to `IMPLEMENTED_CANDIDATE` for bounded implementation and
  review. P1.7 Y Dissipation Geometry, P1.8 geodesic resolution, and S3 remain
  `NOT_STARTED`.
- This phase transition is engineering authority only. It is not scientific
  validation of ABY, semantic quality, Y prediction, or geodesic coordination.
- Candidate implementation uses one immutable content-addressed accepted
  snapshot, role-bounded A/B/Y projections, one strict JSON-text inference per
  lane, deterministic no-repair P0-frame parsing, three-worker logical
  concurrency, lane-local provider evidence, and canonical A-then-B-then-Y
  merge independent of completion order.
- Any provider/JSON/schema failure fails the runtime closed with no geometry.
  Successful lanes may enter only the already accepted P1.5 semantic-geometry
  builder. There is no shared EventLog/memory/world/tool mutation from workers.
- P1.7 Y geometry, P1.8 geodesic resolution, S3, `ResolveDecision`, and Commit
  Barrier remain unimplemented. Scientific result: `NOT_RUN`; the candidate
  establishes engineering controls only.
