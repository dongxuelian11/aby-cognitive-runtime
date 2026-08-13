"""Neutral LLM provider abstraction (P1.2).

- ``LLMRequest`` / ``LLMResponse`` — generic normalized contracts
- ``FakeProvider`` — deterministic offline test infrastructure
- ``OpenAICompatProvider`` — vendor-neutral OpenAI-compatible HTTP adapter

No API key may ever enter request/response metadata, events, errors, or
artifacts. Keys are read from environment variables at execution time only.
"""

from .base import (
    LLMMessage,
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderError,
    ProviderErrorKind,
    emit,
)
from .fake import FakeProvider
from .openai_compat import OpenAICompatProvider

__all__ = [
    "LLMMessage",
    "LLMProvider",
    "LLMRequest",
    "LLMResponse",
    "ProviderError",
    "ProviderErrorKind",
    "emit",
    "FakeProvider",
    "OpenAICompatProvider",
]
