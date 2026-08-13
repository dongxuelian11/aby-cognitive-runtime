"""OpenAI-compatible HTTP chat/completions provider (P1.2).

One real provider style, deliberately vendor-neutral: the same adapter works
against any compatible hosted or local endpoint. Uses only the Python
standard library (urllib) — no vendor SDK, no LLM framework.

Secret handling: the API key is read from the environment variable named by
``api_key_env`` at execution time only. Keys never appear in requests'
metadata, responses, events, errors, or artifacts. There is no silent
fallback to the fake provider.

Transport retries: at most ``max_retries`` retries, only for transient
``NETWORK_ERROR`` / ``PROVIDER_TIMEOUT`` failures, counted as
``transport_retries``. Retries never produce multiple successful candidate
answers — the first success wins and counts as exactly one logical call.
"""

import json
import os
import socket
import time
import urllib.error
import urllib.request

from .base import (
    LLMProvider,
    LLMRequest,
    LLMResponse,
    ProviderError,
    ProviderErrorKind,
    emit,
)

_TRANSIENT_KINDS = frozenset(
    {ProviderErrorKind.NETWORK_ERROR, ProviderErrorKind.PROVIDER_TIMEOUT}
)


class OpenAICompatProvider(LLMProvider):
    name = "openai_compat"

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key_env: str = "ABY_LLM_API_KEY",
        timeout_seconds: float = 30.0,
        temperature: float = 0.0,
        max_output_tokens: int = 1024,
        seed: int | None = None,
        max_retries: int = 1,
    ) -> None:
        if not base_url:
            raise ValueError("openai_compat provider requires a non-empty base_url")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key_env = api_key_env
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.seed = seed
        self.max_retries = max_retries

    # -- secret resolution ----------------------------------------------------

    def _resolve_api_key(self) -> str:
        value = os.environ.get(self.api_key_env)
        if not value:
            raise ProviderError(
                ProviderErrorKind.AUTHENTICATION_ERROR,
                f"environment variable {self.api_key_env} is not set",
            )
        return value

    # -- inference ------------------------------------------------------------

    def generate(self, request: LLMRequest, *, event_sink=None) -> LLMResponse:
        api_key = self._resolve_api_key()  # execution-time only; never stored
        payload = self._build_payload(request)
        attempts = 0
        while True:
            attempts += 1
            emit(
                event_sink,
                "model_request_started",
                {"provider": self.name, "model": self.model, "attempt": attempts},
            )
            try:
                # The request timeout is the single HTTP transport authority.
                # S0 normalizes provider config into this request field; the
                # outer EpisodeRunner timeout remains a separate bound.
                response = self._post(payload, api_key, request.timeout_seconds)
                response.transport_retries = attempts - 1
                emit(
                    event_sink,
                    "model_request_completed",
                    {
                        "provider": self.name,
                        "model": self.model,
                        "input_tokens": response.input_tokens,
                        "output_tokens": response.output_tokens,
                        "usage_available": response.usage_available,
                        "transport_retries": response.transport_retries,
                    },
                )
                return response
            except ProviderError as exc:
                retryable = exc.kind in _TRANSIENT_KINDS and attempts - 1 < self.max_retries
                emit(
                    event_sink,
                    "model_request_failed",
                    {
                        "provider": self.name,
                        "model": self.model,
                        "error_kind": exc.kind.value,
                        "attempt": attempts,
                        "will_retry": retryable,
                    },
                )
                if retryable:
                    continue
                exc.transport_retries = attempts - 1
                raise

    # -- wire format ----------------------------------------------------------

    def _build_payload(self, request: LLMRequest) -> dict:
        payload = {
            "model": request.model,
            "messages": [
                {"role": m.role, "content": m.content} for m in request.messages
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_output_tokens,
        }
        if request.seed is not None:
            payload["seed"] = request.seed
        return payload

    def _post(self, payload: dict, api_key: str, timeout_seconds: float) -> LLMResponse:
        url = f"{self.base_url}/chat/completions"
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        started = time.monotonic()
        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except (socket.timeout, TimeoutError) as exc:
            raise ProviderError(
                ProviderErrorKind.PROVIDER_TIMEOUT, f"provider timed out after {timeout_seconds}s"
            ) from exc
        except urllib.error.HTTPError as exc:
            raise ProviderError(
                _map_http_error(exc.code), f"HTTP {exc.code} {exc.reason}"
            ) from exc
        except urllib.error.URLError as exc:
            raise ProviderError(
                ProviderErrorKind.NETWORK_ERROR, f"network error: {exc.reason}"
            ) from exc

        latency_ms = int((time.monotonic() - started) * 1000)
        data = self._parse_response(raw)
        return LLMResponse(
            content=data["content"],
            provider=self.name,
            model=data.get("model", self.model),
            finish_reason=data.get("finish_reason", ""),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            usage_available=data.get("usage_available", False),
            provider_request_id=data.get("provider_request_id", ""),
            latency_ms=latency_ms,
            raw_metadata=data.get("raw_metadata", {}),
        )

    @staticmethod
    def _parse_response(raw: str) -> dict:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderError(
                ProviderErrorKind.INVALID_PROVIDER_RESPONSE,
                "response is not valid JSON",
            ) from exc
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ProviderError(
                ProviderErrorKind.INVALID_PROVIDER_RESPONSE,
                "response has no choices",
            )
        message = choices[0].get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise ProviderError(
                ProviderErrorKind.INVALID_PROVIDER_RESPONSE,
                "response message content missing",
            )
        usage = data.get("usage")
        usage_available = (
            isinstance(usage, dict)
            and "prompt_tokens" in usage
            and "completion_tokens" in usage
        )
        normalized_usage = usage if usage_available else {}
        input_tokens = _as_int(normalized_usage.get("prompt_tokens"))
        output_tokens = _as_int(normalized_usage.get("completion_tokens"))
        return {
            "content": message["content"],
            "model": data.get("model", ""),
            "finish_reason": choices[0].get("finish_reason", ""),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": _as_int(
                normalized_usage.get("total_tokens", input_tokens + output_tokens)
            ),
            "usage_available": usage_available,
            "provider_request_id": data.get("id", ""),
            "raw_metadata": {"id": data.get("id", ""), "object": data.get("object", "")},
        }


def _map_http_error(code: int) -> ProviderErrorKind:
    if code in (401, 403):
        return ProviderErrorKind.AUTHENTICATION_ERROR
    if code == 429:
        return ProviderErrorKind.RATE_LIMITED
    return ProviderErrorKind.PROVIDER_ERROR


def _as_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
