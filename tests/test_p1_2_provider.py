"""P1.2 provider tests: fake determinism, wire format, errors, secrets, retries.

All HTTP tests are mocked locally — no public network access in unit tests.
"""

import io
import json
import socket
import urllib.error
import urllib.request

import pytest

from aby.providers import (
    FakeProvider,
    LLMMessage,
    LLMRequest,
    OpenAICompatProvider,
    ProviderError,
    ProviderErrorKind,
)

API_KEY_ENV = "ABY_LLM_API_KEY"
SECRET = "sk-test-secret-xyz"


def _req(model: str = "test-model", seed: int | None = 7) -> LLMRequest:
    return LLMRequest(
        model=model,
        messages=[
            LLMMessage(role="system", content="be helpful"),
            LLMMessage(role="user", content="hello world"),
        ],
        temperature=0.0,
        max_output_tokens=64,
        seed=seed,
    )


def _make_provider(**kwargs) -> OpenAICompatProvider:
    defaults = dict(base_url="http://example.test/v1", model="test-model", api_key_env=API_KEY_ENV)
    defaults.update(kwargs)
    return OpenAICompatProvider(**defaults)


class _FakeHTTPResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self) -> bytes:
        return self._payload


# --- fake provider -----------------------------------------------------------


def test_fake_provider_is_deterministic():
    provider = FakeProvider()
    a = provider.generate(_req())
    b = provider.generate(_req())
    assert a.content == b.content
    assert (a.input_tokens, a.output_tokens) == (b.input_tokens, b.output_tokens)


def test_fake_provider_usage_propagates():
    response = FakeProvider().generate(_req())
    assert response.input_tokens > 0
    assert response.output_tokens > 0
    assert response.total_tokens == response.input_tokens + response.output_tokens
    assert response.finish_reason == "stop"
    assert response.latency_ms >= 0


def test_fake_provider_seed_changes_content():
    provider = FakeProvider()
    assert provider.generate(_req(seed=1)).content != provider.generate(_req(seed=2)).content


def test_fake_provider_simulates_errors():
    for kind in (ProviderErrorKind.PROVIDER_ERROR, ProviderErrorKind.PROVIDER_TIMEOUT):
        with pytest.raises(ProviderError) as exc_info:
            FakeProvider(fail_with=kind).generate(_req())
        assert exc_info.value.kind is kind


def test_fake_provider_never_touches_network():
    from pathlib import Path

    source = (Path(__file__).resolve().parent.parent / "aby" / "providers" / "fake.py").read_text()
    for banned in ("urllib", "socket", "http", "requests"):
        assert banned not in source


def test_fake_provider_emits_model_events():
    events = []
    FakeProvider().generate(_req(), event_sink=lambda kind, payload: events.append(kind))
    assert events == ["model_request_started", "model_request_completed"]


# --- openai-compatible wire format -------------------------------------------


def test_real_provider_request_serialization(monkeypatch):
    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["req"] = req
        return _FakeHTTPResponse(
            json.dumps(
                {
                    "id": "req-1",
                    "model": "test-model",
                    "choices": [
                        {"finish_reason": "stop", "message": {"role": "assistant", "content": "hi"}}
                    ],
                    "usage": {"prompt_tokens": 11, "completion_tokens": 3, "total_tokens": 14},
                }
            ).encode()
        )

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv(API_KEY_ENV, SECRET)
    response = _make_provider().generate(_req())

    req = captured["req"]
    assert req.full_url == "http://example.test/v1/chat/completions"
    assert req.get_method() == "POST"
    assert req.get_header("Content-type") == "application/json"
    assert req.get_header("Authorization").startswith("Bearer ")
    body = json.loads(req.data.decode())
    assert body["model"] == "test-model"
    assert body["messages"][0]["role"] == "system"
    assert body["temperature"] == 0.0
    assert body["max_tokens"] == 64
    assert body["seed"] == 7
    assert response.content == "hi"
    assert response.input_tokens == 11 and response.output_tokens == 3
    assert response.provider_request_id == "req-1"
    assert response.latency_ms >= 0


def test_real_provider_response_parsing_without_usage(monkeypatch):
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda req, timeout=None: _FakeHTTPResponse(
            json.dumps(
                {
                    "choices": [{"finish_reason": "length", "message": {"content": "ok"}}],
                }
            ).encode()
        ),
    )
    monkeypatch.setenv(API_KEY_ENV, SECRET)
    response = _make_provider().generate(_req())
    assert response.content == "ok"
    assert response.finish_reason == "length"
    assert response.input_tokens == 0 and response.output_tokens == 0


def test_missing_credential_fails_with_authentication_error(monkeypatch):
    monkeypatch.delenv(API_KEY_ENV, raising=False)
    with pytest.raises(ProviderError) as exc_info:
        _make_provider().generate(_req())
    assert exc_info.value.kind is ProviderErrorKind.AUTHENTICATION_ERROR
    assert API_KEY_ENV in exc_info.value.message


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("http://example.test/v1", code, f"HTTP {code}", {}, io.BytesIO(b"{}"))


@pytest.mark.parametrize(
    "error,expected_kind",
    [
        (lambda: _http_error(401), ProviderErrorKind.AUTHENTICATION_ERROR),
        (lambda: _http_error(403), ProviderErrorKind.AUTHENTICATION_ERROR),
        (lambda: _http_error(429), ProviderErrorKind.RATE_LIMITED),
        (lambda: _http_error(500), ProviderErrorKind.PROVIDER_ERROR),
        (lambda: urllib.error.URLError("connection refused"), ProviderErrorKind.NETWORK_ERROR),
        (lambda: socket.timeout("timed out"), ProviderErrorKind.PROVIDER_TIMEOUT),
    ],
)
def test_error_mapping(monkeypatch, error, expected_kind):
    def raise_error(req, timeout=None):
        raise error()

    monkeypatch.setattr(urllib.request, "urlopen", raise_error)
    monkeypatch.setenv(API_KEY_ENV, SECRET)
    with pytest.raises(ProviderError) as exc_info:
        _make_provider().generate(_req())
    assert exc_info.value.kind is expected_kind


def test_invalid_response_mapping(monkeypatch):
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda req, timeout=None: _FakeHTTPResponse(b"this is not json"),
    )
    monkeypatch.setenv(API_KEY_ENV, SECRET)
    with pytest.raises(ProviderError) as exc_info:
        _make_provider().generate(_req())
    assert exc_info.value.kind is ProviderErrorKind.INVALID_PROVIDER_RESPONSE


def test_transport_retry_counts_once_and_never_duplicates_success(monkeypatch):
    calls = {"n": 0}
    events = []

    def flaky_urlopen(req, timeout=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise urllib.error.URLError("transient")
        return _FakeHTTPResponse(
            json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode()
        )

    monkeypatch.setattr(urllib.request, "urlopen", flaky_urlopen)
    monkeypatch.setenv(API_KEY_ENV, SECRET)
    response = _make_provider(max_retries=1).generate(
        _req(), event_sink=lambda kind, payload: events.append((kind, payload))
    )
    assert calls["n"] == 2
    assert response.transport_retries == 1
    kinds = [k for k, _ in events]
    assert kinds == [
        "model_request_started",
        "model_request_failed",
        "model_request_started",
        "model_request_completed",
    ]
    assert events[1][1]["will_retry"] is True


def test_secret_never_persisted_on_provider(monkeypatch):
    monkeypatch.setenv(API_KEY_ENV, SECRET)
    provider = _make_provider()
    provider._resolve_api_key()  # execution-time resolution only
    assert all(SECRET not in str(value) for value in provider.__dict__.values())
