"""S0 Single-LLM baseline (P1.2).

Purity definition (P1.2 task §10, §11):

- exactly ONE logical model inference per normal successful episode;
- one fixed, versioned prompt (``S0_PROMPT_V0_1``) that only asks the model
  to answer the supplied task — no theory, no memory instructions, no
  self-reflection, no chain-of-thought requests, no scoring criteria;
- no long-term memory, no RAG, no MoA aggregation, no A/B/Y lane frames,
  no tools, no second judge/verifier call, no best-of selection;
- prior-episode history is used only if the dataset input itself carries it.

Transport retries (provider level, bounded, transient-only) are counted
separately and never increase the logical inference count.
"""

import hashlib
import json
import math
from typing import Any

from ..events import Event, EventLog
from ..experiments.config import ExperimentConfig
from ..experiments.system import EpisodeInput, EpisodeResult
from ..providers import (
    LLMMessage,
    LLMProvider,
    LLMRequest,
    ProviderError,
)

S0_SYSTEM_ID = "S0"
S0_PROMPT_VERSION = "S0_PROMPT_V0_1"

S0_PROMPT_V0_1 = "Answer the supplied task directly and correctly."
S0_PROMPT_SHA256 = hashlib.sha256(S0_PROMPT_V0_1.encode("utf-8")).hexdigest()


def _extract_task(episode_input_data: Any) -> str:
    if isinstance(episode_input_data, dict):
        task = episode_input_data.get("task")
        if isinstance(task, str) and task:
            return task
        return json.dumps(episode_input_data, ensure_ascii=False)
    return str(episode_input_data)


class S0SingleLLM:
    """Concrete generic SystemUnderTest: one provider inference per episode."""

    SYSTEM_ID = S0_SYSTEM_ID
    PROMPT_VERSION = S0_PROMPT_VERSION

    def __init__(
        self,
        provider: LLMProvider,
        *,
        temperature: float = 0.0,
        max_output_tokens: int = 1024,
        provider_timeout_seconds: float | None = None,
        seed: int | None = None,
    ) -> None:
        self.provider = provider
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.provider_timeout_seconds = float(
            provider_timeout_seconds
            if provider_timeout_seconds is not None
            else getattr(provider, "timeout_seconds", 30.0)
        )
        self.seed = seed

    def run_episode(self, episode_input: EpisodeInput) -> EpisodeResult:
        task = _extract_task(episode_input.input)
        event_log = episode_input.metadata.get("event_log")

        def sink(kind: str, payload: dict[str, Any]) -> None:
            if isinstance(event_log, EventLog):
                event_log.append(
                    Event(episode_id=episode_input.episode_id, kind=kind, payload=payload)
                )

        request = LLMRequest(
            model=getattr(self.provider, "model", "unknown"),
            messages=[
                LLMMessage(role="system", content=S0_PROMPT_V0_1),
                LLMMessage(role="user", content=task),
            ],
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
            # This is the provider/HTTP timeout. EpisodeRunner applies the
            # separate outer episode timeout from ExperimentConfig.
            timeout_seconds=self.provider_timeout_seconds,
            seed=self.seed,
        )

        base_metadata: dict[str, Any] = {
            "system_id": S0_SYSTEM_ID,
            "provider": getattr(self.provider, "name", "unknown"),
            "model": request.model,
            "prompt_version": S0_PROMPT_VERSION,
            "prompt_sha256": S0_PROMPT_SHA256,
            "temperature": self.temperature,
            "max_output_tokens": self.max_output_tokens,
            "provider_timeout_seconds": self.provider_timeout_seconds,
            "seed": self.seed,
            "logical_model_calls": 1,
        }

        try:
            response = self.provider.generate(request, event_sink=sink)
        except ProviderError as exc:
            return EpisodeResult(
                output=None,
                status="FAILED",
                error=f"{exc.kind.value}: {exc.message}",
                metadata={
                    **base_metadata,
                    "provider_error_kind": exc.kind.value,
                    "transport_retries": exc.transport_retries,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "usage_available": False,
                },
            )

        return EpisodeResult(
            output={"answer": response.content},
            status="SUCCEEDED",
            tool_events=[],  # S0 uses no tools; stays 0 (P1.2 §10)
            metadata={
                **base_metadata,
                "finish_reason": response.finish_reason,
                "provider_request_id": response.provider_request_id,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "total_tokens": response.total_tokens,
                "usage_available": response.usage_available,
                "provider_latency_ms": response.latency_ms,
                "transport_retries": response.transport_retries,
            },
        )


def _require_nonempty_string(spec: dict[str, Any], field: str, *, default=None) -> str:
    value = spec.get(field, default)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"S0 provider field {field!r} must be a non-empty string")
    return value


def _finite_number(
    spec: dict[str, Any], field: str, default: float, *, strictly_positive: bool = False
) -> float:
    value = spec.get(field, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"S0 provider field {field!r} must be numeric")
    normalized = float(value)
    if not math.isfinite(normalized):
        raise ValueError(f"S0 provider field {field!r} must be finite")
    if strictly_positive and normalized <= 0:
        raise ValueError(f"S0 provider field {field!r} must be > 0")
    if not strictly_positive and normalized < 0:
        raise ValueError(f"S0 provider field {field!r} must be >= 0")
    return normalized


def _integer(
    spec: dict[str, Any], field: str, default: int, *, minimum: int
) -> int:
    value = spec.get(field, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"S0 provider field {field!r} must be an integer >= {minimum}")
    return value


def validate_s0_provider_config(config: ExperimentConfig) -> dict[str, Any]:
    """Validate and normalize S0 provider semantics without I/O.

    This function never resolves credentials and never performs network
    transport, so it is safe for ``aby experiment validate``.
    """
    raw_spec = (config.metadata or {}).get("provider")
    if raw_spec is None:
        raw_spec = {"type": "fake"}
    if not isinstance(raw_spec, dict):
        raise ValueError("S0 config metadata.provider must be an object")
    spec = dict(raw_spec)
    provider_type = _require_nonempty_string(spec, "type", default="fake")
    if provider_type not in {"fake", "openai_compat"}:
        raise ValueError(
            f"unknown S0 provider type {provider_type!r} "
            "(expected 'fake' or 'openai_compat')"
        )

    normalized = dict(spec)
    normalized["type"] = provider_type
    normalized["model"] = _require_nonempty_string(
        spec, "model", default="fake-s0" if provider_type == "fake" else None
    )
    normalized["temperature"] = _finite_number(spec, "temperature", 0.0)
    normalized["max_output_tokens"] = _integer(
        spec, "max_output_tokens", 1024, minimum=1
    )
    seed = spec.get("seed")
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        raise ValueError("S0 provider field 'seed' must be an integer or null")
    normalized["seed"] = seed

    if provider_type == "openai_compat":
        normalized["base_url"] = _require_nonempty_string(spec, "base_url")
        normalized["api_key_env"] = _require_nonempty_string(
            spec, "api_key_env", default="ABY_LLM_API_KEY"
        )
        normalized["timeout_seconds"] = _finite_number(
            spec, "timeout_seconds", 30.0, strictly_positive=True
        )
        normalized["max_retries"] = _integer(spec, "max_retries", 1, minimum=0)
    else:
        normalized["timeout_seconds"] = 30.0
        normalized["max_retries"] = 0

    return normalized


def build_s0(config: ExperimentConfig) -> S0SingleLLM:
    """Build an S0 system from the neutral provider spec in config metadata.

    Provider spec shape (``config.metadata["provider"]``):

    - fake: ``{"type": "fake", "model": "fake-s0"}``
    - real: ``{"type": "openai_compat", "base_url": ..., "model": ...,
      "api_key_env": "ABY_LLM_API_KEY", ...}``

    Only the environment variable NAME is ever stored; the secret itself is
    resolved at execution time by the provider.
    """
    from ..providers import FakeProvider, OpenAICompatProvider

    spec = validate_s0_provider_config(config)
    provider_type = spec["type"]

    if provider_type == "fake":
        provider = FakeProvider(model=spec["model"])
    elif provider_type == "openai_compat":
        provider = OpenAICompatProvider(
            base_url=spec["base_url"],
            model=spec["model"],
            api_key_env=spec["api_key_env"],
            timeout_seconds=spec["timeout_seconds"],
            temperature=spec["temperature"],
            max_output_tokens=spec["max_output_tokens"],
            seed=spec["seed"],
            max_retries=spec["max_retries"],
        )

    return S0SingleLLM(
        provider,
        temperature=spec["temperature"],
        max_output_tokens=spec["max_output_tokens"],
        provider_timeout_seconds=spec["timeout_seconds"],
        seed=spec["seed"],
    )


def s0_requires_missing_credential(config: ExperimentConfig) -> str | None:
    """Return the env-var name S0 needs but is unset, else None.

    Used by the CLI to fail clearly (non-zero) before running a real
    provider without credentials. Never resolves or exposes the secret.
    """
    import os

    spec = validate_s0_provider_config(config)
    if spec["type"] != "openai_compat":
        return None
    env_name = spec["api_key_env"]
    if not os.environ.get(env_name):
        return env_name
    return None
