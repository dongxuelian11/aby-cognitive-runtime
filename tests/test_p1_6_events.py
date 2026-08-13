import threading

from aby.events import EventLog
from aby.runtime.lane_events import LaneName, lane_event_order_fingerprint
from tests.p1_6_support import (
    build_runtime,
    runtime_config,
    runtime_providers,
    sample_snapshot,
)


def _b_then_y_then_a_providers():
    b_done = threading.Event()
    y_done = threading.Event()
    return runtime_providers(
        B={"signal": b_done},
        Y={"wait_for": b_done, "signal": y_done},
        A={"wait_for": y_done},
    )


def test_staggered_b_y_a_completion_still_merges_events_a_then_b_then_y_repeatedly():
    fingerprints = set()
    order_fingerprints = set()
    for _ in range(5):
        providers = _b_then_y_then_a_providers()
        result = build_runtime(providers).run(sample_snapshot(), runtime_config())
        events = result.canonical_lane_events
        assert [event.lane for event in events] == [
            LaneName.A, LaneName.A, LaneName.B, LaneName.B, LaneName.Y, LaneName.Y
        ]
        for lane in (LaneName.A, LaneName.B, LaneName.Y):
            assert [event.local_ordinal for event in events if event.lane is lane] == [0, 1]
        fingerprints.add(result.runtime_semantic_fingerprint)
        order_fingerprints.add(lane_event_order_fingerprint(events))
    assert len(fingerprints) == 1
    assert len(order_fingerprints) == 1


def test_workers_never_write_shared_eventlog(monkeypatch):
    calls = []

    def forbidden_append(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("worker attempted shared EventLog mutation")

    monkeypatch.setattr(EventLog, "append", forbidden_append)
    result = build_runtime(runtime_providers()).run(sample_snapshot(), runtime_config())
    assert result.status.value == "SUCCEEDED"
    assert calls == []
