"""Deterministic offline fake provider (P1.2 test infrastructure).

Never touches the network. Same request in → same normalized response out.
Can simulate provider errors and timeouts for repeatable tests.

This is NOT a baseline and NOT a scientific stand-in for a real model.
"""

import hashlib
import time

from .base import LLMProvider, LLMRequest, LLMResponse, ProviderError, ProviderErrorKind, emit


class FakeProvider(LLMProvider):
    name = "fake"
    model = "fake-s0"

    def __init__(
        self,
        *,
        model: str = "fake-s0",
        fail_with: ProviderErrorKind | None = None,
        sleep_seconds: float = 0.0,
        latency_ms: int = 7,
    ) -> None:
        self.model = model
        self._fail_with = fail_with
        self._sleep_seconds = sleep_seconds
        self._latency_ms = latency_ms

    def generate(self, request: LLMRequest, *, event_sink=None) -> LLMResponse:
        emit(
            event_sink,
            "model_request_started",
            {"provider": self.name, "model": self.model, "attempt": 1},
        )
        started = time.monotonic()
        if self._sleep_seconds > 0:
            time.sleep(self._sleep_seconds)

        if self._fail_with is not None:
            emit(
                event_sink,
                "model_request_failed",
                {"provider": self.name, "model": self.model, "error_kind": self._fail_with.value},
            )
            raise ProviderError(self._fail_with, "simulated provider failure (fake)")

        last_user = next(
            (m.content for m in reversed(request.messages) if m.role == "user"), ""
        )
        digest = hashlib.sha256(
            f"{self.model}|{request.seed}|{last_user}".encode("utf-8")
        ).hexdigest()[:16]
        content = f"[fake {self.model}] seed={request.seed} digest={digest} answer=ok"
        # Deterministic usage accounting (no tokenizer; synthetic but stable).
        input_tokens = 5 + len(last_user) // 4
        output_tokens = 3 + len(content) // 4
        latency_ms = self._latency_ms + int((time.monotonic() - started) * 1000)

        response = LLMResponse(
            content=content,
            provider=self.name,
            model=self.model,
            finish_reason="stop",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            usage_available=True,
            provider_request_id=f"fake-{digest}",
            latency_ms=latency_ms,
            transport_retries=0,
        )
        emit(
            event_sink,
            "model_request_completed",
            {
                "provider": self.name,
                "model": self.model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "usage_available": True,
            },
        )
        return response
