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
