"""Minimal shared memory — P0 V0.1 §14.

P1 must use a deliberately simple shared memory layer to avoid confounding:

- Episode Store
- Structured Facts
- Keyword Retrieval
- Optional Embedding Retrieval (deferred)

Graphiti, Letta, and advanced temporal memory are deferred until the ABY
skeleton is measurable. Memory adapters must remain replaceable (P0 §14).

Also relevant: B-Layer must not load all historical memory by default;
stale memory is not current authority (P0 §5.2).
"""


class SharedMemory:
    """Deliberately simple shared memory facade. Backends are P1 work."""

    def store_episode(self, episode_id: str, events) -> None:
        """Persist one bounded episode (Episode Store, P0 §14)."""
        raise NotImplementedError(
            "Memory backends are P1 implementation work. Blocked until P0 V0.1 "
            "acceptance (docs/p0/P0_ACCEPTANCE_TRACKER.md)."
        )

    def load_episode(self, episode_id: str):
        raise NotImplementedError("P1 implementation work; see store_episode.")

    def upsert_fact(self, key: str, value, evidence_refs=None) -> None:
        """Write a structured fact; never silently overwrite (P0 §5.1)."""
        raise NotImplementedError("P1 implementation work; see store_episode.")

    def get_fact(self, key: str):
        raise NotImplementedError("P1 implementation work; see store_episode.")

    def search(self, query: str, k: int = 5) -> list[str]:
        """Keyword retrieval (P0 §14). Embedding retrieval is optional/deferred."""
        raise NotImplementedError("P1 implementation work; see store_episode.")
