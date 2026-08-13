# Experiment configs

Directory for reproducible experiment definitions (P1 in-scope item: "reproducible experiment config", P0 §17).

- `example_s0_*.json` are the accepted S0 fake/real-provider examples.
- `example_s1_fake_provider.json` is the offline two-episode committed-memory demonstration.
- `example_s1_openai_compat.json` validates offline but executes only through explicit `aby run`.
- `example_s2_fake_provider.json` is the offline deterministic 3-proposer + 1-aggregator demonstration.
- `example_s2_mixed_openai_compat.json` validates offline, rejects dry-run before credentials/network, and executes only through explicit `aby run` with all configured credentials present.
- `example_s3_aby_fixed.yaml` remains an illustrative skeleton only; S3 is not implemented by P1.4.
- **The config schema is NOT frozen** — see `docs/design/P1_DESIGN.md`.
- Every run records the config hash and Git revision in provenance artifacts.
- Fairness rules (P0 §10) must hold across all baselines in a comparison.
