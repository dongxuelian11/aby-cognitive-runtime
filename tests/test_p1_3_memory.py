"""P1.3 committed in-memory keyword backend tests."""

from dataclasses import replace

import pytest

from aby.memory import InMemoryKeywordMemory


def _store(memory, episode_id, task, answer="answer", task_family="family"):
    return memory.store_episode(
        episode_id,
        {"task_family": task_family, "task": task, "answer": answer},
    )


def test_episode_store_load_is_committed_and_caller_isolated():
    memory = InMemoryKeywordMemory()
    stored = _store(memory, "ep-1", "alpha task")
    loaded = memory.load_episode("ep-1")
    assert loaded == stored
    assert loaded is not stored
    assert loaded.committed is True
    assert memory.load_episode("missing") is None


def test_committed_episode_is_idempotent_but_cannot_be_overwritten():
    memory = InMemoryKeywordMemory()
    first = _store(memory, "ep-1", "alpha")
    again = _store(memory, "ep-1", "alpha")
    assert again.item_id == first.item_id
    assert memory.committed_episode_count == 1
    with pytest.raises(ValueError, match="cannot be overwritten"):
        _store(memory, "ep-1", "conflicting task")


def test_created_publication_receipt_rolls_back_only_its_exact_item():
    memory = InMemoryKeywordMemory()
    receipt = memory.publish_episode(
        "ep-1",
        {"task_family": "family", "task": "atomic marker", "answer": "answer"},
    )
    assert receipt.created_by_this_publication is True
    assert memory.committed_episode_count == 1

    mismatched_item = receipt.item.model_copy(
        update={"item_id": "mem-episode-mismatched"}
    )
    mismatched_receipt = replace(receipt, item=mismatched_item)
    assert memory.rollback_episode_publication(mismatched_receipt) is False
    assert memory.load_episode("ep-1") == receipt.item

    assert memory.rollback_episode_publication(receipt) is True
    assert memory.load_episode("ep-1") is None
    assert memory.rollback_episode_publication(receipt) is False


def test_idempotent_publication_receipt_cannot_delete_preexisting_item():
    memory = InMemoryKeywordMemory()
    existing = _store(memory, "ep-1", "historical marker")
    receipt = memory.publish_episode(
        "ep-1",
        {
            "task_family": existing.task_family,
            "task": existing.task,
            "answer": existing.answer,
        },
    )
    assert receipt.created_by_this_publication is False
    assert receipt.item.item_id == existing.item_id
    assert memory.rollback_episode_publication(receipt) is False
    assert memory.load_episode("ep-1") == existing
    assert memory.committed_episode_count == 1


def test_structured_fact_same_value_is_idempotent_and_conflict_is_preserved():
    memory = InMemoryKeywordMemory()
    first = memory.upsert_fact("color", {"value": "blue"}, ["ep-1"])
    same = memory.upsert_fact("color", {"value": "blue"}, ["ep-2"])
    conflicting = memory.upsert_fact("color", {"value": "green"}, ["ep-3"])
    assert same.item_id == first.item_id
    assert conflicting.item_id != first.item_id
    history = memory.get_fact("color")
    assert history is not None
    assert [v.value for v in history.versions] == [
        {"value": "blue"},
        {"value": "green"},
    ]
    # Returned nested values are detached from stored history.
    history.versions[0].value["value"] = "mutated"
    assert memory.get_fact("color").versions[0].value == {"value": "blue"}


def test_keyword_retrieval_is_deterministic_with_stable_tie_breaking():
    memory = InMemoryKeywordMemory()
    _store(memory, "ep-b", "shared token")
    _store(memory, "ep-a", "shared token")
    first = memory.search("shared", k=5)
    second = memory.search("shared", k=5)
    assert [hit.model_dump() for hit in first] == [hit.model_dump() for hit in second]
    assert [hit.score for hit in first] == [1, 1]
    assert [hit.item_id for hit in first] == sorted(hit.item_id for hit in first)


def test_keyword_retrieval_enforces_top_k_and_max_chars():
    memory = InMemoryKeywordMemory()
    for index in range(4):
        _store(memory, f"ep-{index}", f"bounded keyword task {index}", "x" * 50)
    hits = memory.search("bounded keyword", k=2, max_chars=37)
    assert len(hits) <= 2
    assert sum(len(hit.text) for hit in hits) <= 37
    with pytest.raises(ValueError):
        memory.search("x", k=0)
    with pytest.raises(ValueError):
        memory.search("x", k=101)
    with pytest.raises(ValueError):
        memory.search("x", k=1, max_chars=0)


def test_search_returns_deep_copies_and_only_positive_matches():
    memory = InMemoryKeywordMemory()
    item = _store(memory, "ep-1", "unique needle")
    hits = memory.search("needle", k=5)
    assert [hit.item_id for hit in hits] == [item.item_id]
    assert memory.search("absent", k=5) == []


def test_fresh_backend_instances_never_share_state():
    first = InMemoryKeywordMemory()
    second = InMemoryKeywordMemory()
    _store(first, "ep-1", "isolated memory")
    assert first.committed_episode_count == 1
    assert second.committed_episode_count == 0
    assert second.search("isolated", k=5) == []
