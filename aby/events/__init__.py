"""Event log — the replayability backbone (P0 V0.1 §15, §16).

Every episode must be replayable from stored events and configuration.
P0 §15: event-driven architecture; every episode is replayable from stored
events and configuration.

P1.1 extensions (minimal, per P1.1 task §7.4):
- stable per-episode event IDs (``<episode_id>#<seq>``);
- replay returns deep copies so historical events cannot be mutated;
- append returns the stored event.

The in-memory implementation remains skeletal but functional; a durable
backend stays a later design decision (docs/design/P1_DESIGN.md).
"""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class Event(BaseModel):
    """One event in an episode's append-only log."""

    episode_id: str
    seq: int = 0
    ts: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    kind: str
    payload: dict[str, Any] = Field(default_factory=dict)

    @property
    def event_id(self) -> str:
        """Stable event identity within the episode."""
        return f"{self.episode_id}#{self.seq:06d}"


class EventLog:
    """Append-only event log, replayable per episode."""

    def __init__(self) -> None:
        self._episodes: dict[str, list[Event]] = {}

    def append(self, event: Event) -> Event:
        """Append an event, assigning the next sequence number for its episode."""
        per_episode = self._episodes.setdefault(event.episode_id, [])
        event.seq = len(per_episode) + 1
        per_episode.append(event)
        return event

    def replay(self, episode_id: str) -> list[Event]:
        """Return the events of one episode in order (P0 §15).

        Returns deep copies: historical events can never be mutated
        through replay handles.
        """
        return [e.model_copy(deep=True) for e in self._episodes.get(episode_id, [])]

    def to_json(self) -> list[dict[str, Any]]:
        """Serialize all episodes to a JSON-compatible list for persistence."""
        return [e.model_dump() for events in self._episodes.values() for e in events]

    @classmethod
    def from_json(cls, data: list[dict[str, Any]]) -> "EventLog":
        log = cls()
        for raw in data:
            log.append(Event.model_validate(raw))
        return log
