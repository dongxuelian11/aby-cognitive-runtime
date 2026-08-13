"""Neutral LLM provider contracts (P1.2).

Architecture-neutral: the same request/response types serve every future
system (S0/S1/S2/S3). No ABY lane frames involved, no vendor hard-coding,
and no secret material ever enters requests, responses, errors, or
metadata.

Provider errors use a small generic taxonomy (P1.2 task §13) so baseline
comparisons see identical failure semantics across providers.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Literal

from pydantic import BaseModel, Field

# Optional sink for generic model-request events. Payloads must stay
# bounded and secret-free (P1.2 task §15).
EventSink = Callable[[str, dict[str, Any]], None]


class LLMMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class LLMRequest(BaseModel):
    """Generic minimum needed by any candidate system."""

    model: str
    messages: list[LLMMessage]
    temperature: float = 0.0
    max_output_tokens: int = Field(default=1024, ge=1)
    timeout_seconds: float = Field(default=30.0, gt=0.0)
    seed: int | None = None  # requested provider seed; not a determinism claim
    metadata: dict[str, Any] = Field(default_factory=dict)  # bounded, secret-free


class LLMResponse(BaseModel):
    """Normalized provider response, truthful about what the provider supplied."""

    content: str
    provider: str
    model: str
    finish_reason: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    provider_request_id: str = ""
    latency_ms: int = 0
    transport_retries: int = 0  # transport retries only; never extra logical calls
    raw_metadata: dict[str, Any] = Field(default_factory=dict)  # bounded, secret-free


class ProviderErrorKind(str, Enum):
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    RATE_LIMITED = "RATE_LIMITED"
    PROVIDER_TIMEOUT = "PROVIDER_TIMEOUT"
    NETWORK_ERROR = "NETWORK_ERROR"
    INVALID_PROVIDER_RESPONSE = "INVALID_PROVIDER_RESPONSE"
    PROVIDER_ERROR = "PROVIDER_ERROR"


class ProviderError(Exception):
    """Normalized provider failure. Never carries secret-bearing data."""

    def __init__(
        self,
        kind: ProviderErrorKind,
        message: str,
        *,
        transport_retries: int = 0,
    ) -> None:
        super().__init__(f"{kind.value}: {message}")
        self.kind = kind
        self.message = message
        self.transport_retries = transport_retries


class LLMProvider(ABC):
    """Neutral provider interface: one request in, one normalized response out."""

    name: str = "abstract"
    model: str = "unknown"

    @abstractmethod
    def generate(
        self,
        request: LLMRequest,
        *,
        event_sink: EventSink | None = None,
    ) -> LLMResponse:
        """Perform one logical inference and return a normalized response."""
        raise NotImplementedError


def emit(event_sink: EventSink | None, kind: str, payload: dict[str, Any]) -> None:
    """Fire a generic model-request event into the optional sink."""
    if event_sink is not None:
        event_sink(kind, payload)
