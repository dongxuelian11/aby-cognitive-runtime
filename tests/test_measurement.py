"""Tests for the frozen measurement model (P0 §7) and event replay (P0 §15)."""

import math

import pytest

from aby.contracts.measurement import (
    EVENT_WEIGHTS_A_RAW,
    EVENT_WEIGHTS_B_RAW,
    EVENT_WEIGHTS_W_RAW,
    normalize,
)
from aby.events import Event, EventLog


def test_weight_tables_are_positive_integers():
    for table in (EVENT_WEIGHTS_A_RAW, EVENT_WEIGHTS_B_RAW, EVENT_WEIGHTS_W_RAW):
        assert table, "weight table must not be empty"
        assert all(isinstance(v, int) and v > 0 for v in table.values())


def test_normalization_recovers_r_star_example():
    # A_raw = 2 * B_raw -> r = 2.0 (the hypothesized central attractor, P0 §2.1)
    state = normalize(A_raw=4, B_raw=2, W_raw=1)
    assert state.a == pytest.approx(4 / 7)
    assert state.b == pytest.approx(2 / 7)
    assert state.y == pytest.approx(1 / 7)
    assert state.r == pytest.approx(2.0)
    assert state.a + state.b + state.y == pytest.approx(1.0)


def test_normalize_rejects_negative_and_zero_total():
    with pytest.raises(ValueError):
        normalize(-1, 2, 1)
    with pytest.raises(ValueError):
        normalize(0, 0, 0)


def test_normalize_high_side_limit_is_infinite():
    state = normalize(A_raw=1, B_raw=0, W_raw=0)
    assert state.r == math.inf


def test_event_log_roundtrip_is_replayable():
    # Replayability is a P0 acceptance item (§15, §16)
    log = EventLog()
    log.append(Event(episode_id="e1", kind="user_turn"))
    log.append(Event(episode_id="e1", kind="resolve"))
    log.append(Event(episode_id="e2", kind="user_turn"))

    replayed = log.replay("e1")
    assert [e.kind for e in replayed] == ["user_turn", "resolve"]
    assert [e.seq for e in replayed] == [1, 2]

    restored = EventLog.from_json(log.to_json())
    assert [e.kind for e in restored.replay("e1")] == ["user_turn", "resolve"]
