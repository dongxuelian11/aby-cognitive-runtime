"""Provider abstraction (P1 scope, P0 §17).

P0 §15: lanes may use different model providers. The abstraction below is
minimal on purpose; its final shape is a P1 design decision
(see docs/design/P1_DESIGN.md, open question Q5).
"""

from abc import ABC, abstractmethod


class Provider(ABC):
    """Minimal LLM provider interface. Implementations are P1 work."""

    @abstractmethod
    async def complete(self, messages: list[dict[str, str]], **kwargs) -> str:
        """Return the model's text completion for the given conversation."""
        raise NotImplementedError(
            "Provider implementations are P1 work. Blocked until P0 V0.1 "
            "acceptance (docs/p0/P0_ACCEPTANCE_TRACKER.md)."
        )
