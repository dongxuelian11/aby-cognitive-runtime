# ABY repository instructions

ABY is a falsifiability-first experimental cognitive runtime, not an AGI or
consciousness claim. Before substantive work, read:

- `docs/authority/README.md`
- `docs/authority/ABY_PROJECT_DOCTRINE_V0_1.md`
- `docs/authority/ABY_TARGET_ARCHITECTURE_P1_HYPOTHESIS_V0_1.md`
- `docs/authority/ABY_PHASE_GATES_AND_ROADMAP_V0_1.md`

The frozen P0 authority remains under `docs/p0/`. P1 architecture documents
cannot silently rewrite it. Verify exact Git/GitHub state live; durable doctrine
is not permanent exact-SHA authority.

Before implementation, identify the current phase and gate, verify the bounded
task scope, and classify each relevant concept as frozen theory, implementation
hypothesis, or experimentally validated fact. Never implement a future phase
merely because it appears in the target architecture.

For long tasks, keep a persistent State Ledger whose first two fields are
`TASK_GOAL` and `TASK_PROGRESS`. Persist both before compaction. After compaction,
reread the original task, full Ledger, this file, applicable canonical authority
documents, and exact Git/GitHub state before continuing.

If the task prompt, repository authority, P0 freeze, or Git state conflict:
**FAIL CLOSED, REPORT THE CONFLICT, AND DO NOT GUESS.** Never force-push, rebase,
reset, or rewrite history unless explicitly authorized. Complete one bounded
task and stop; do not automatically begin the next phase.
