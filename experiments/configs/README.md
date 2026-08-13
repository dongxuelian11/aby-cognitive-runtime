# Experiment configs

Directory for reproducible experiment definitions (P1 in-scope item: "reproducible experiment config", P0 §17).

- `example_s0_*.json` are the accepted S0 fake/real-provider examples.
- `example_s1_fake_provider.json` is the offline two-episode committed-memory demonstration.
- `example_s1_openai_compat.json` validates offline but executes only through explicit `aby run`.
- `example_s3_aby_fixed.yaml` remains an illustrative skeleton only; S2/S3 are not implemented by P1.3.
- **The config schema is NOT frozen** — see `docs/design/P1_DESIGN.md`.
- Every run records the config hash and Git revision in provenance artifacts.
- Fairness rules (P0 §10) must hold across all baselines in a comparison.
