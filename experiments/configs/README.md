# Experiment configs

Directory for reproducible experiment definitions (P1 in-scope item: "reproducible experiment config", P0 §17).

- `example_s3_aby_fixed.yaml` is an illustrative skeleton only.
- **The config schema is NOT frozen** — see `docs/design/P1_DESIGN.md` open questions.
- Draft conventions: one YAML per experiment; every run records the config hash and git revision in its telemetry trace (design TBD).
- Fairness rules (P0 §10) must hold across all baselines in a comparison.
