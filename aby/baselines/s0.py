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

S0_PROMPT_V0_1 = (
    "Answer the supplied task directly and correctly.\n\n"
    "Task:\n{task}"
)
S0_PROMPT_SHA256 = hashlib.sha256(S0_PROMPT_V0_1.encode("utf-8")).hexdigest()


def _render_prompt(task: str) -> str:
    return S0_PROMPT_V0_1.format(task=task)


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
        seed: int | None = None,
    ) -> None:
        self.provider = provider
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
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
                "provider_latency_ms": response.latency_ms,
                "transport_retries": response.transport_retries,
            },
        )


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

    spec = dict((config.metadata or {}).get("provider") or {})
    provider_type = spec.get("type", "fake")

    if provider_type == "fake":
        provider = FakeProvider(model=spec.get("model", "fake-s0"))
    elif provider_type == "openai_compat":
        if not spec.get("base_url"):
            raise ValueError(
                "S0 openai_compat provider spec requires a non-empty 'base_url' "
                "in config.metadata.provider"
            )
        provider = OpenAICompatProvider(
            base_url=spec["base_url"],
            model=spec.get("model", ""),
            api_key_env=spec.get("api_key_env", "ABY_LLM_API_KEY"),
            timeout_seconds=float(spec.get("timeout_seconds", 30.0)),
            temperature=float(spec.get("temperature", 0.0)),
            max_output_tokens=int(spec.get("max_output_tokens", 1024)),
            seed=spec.get("seed"),
            max_retries=int(spec.get("max_retries", 1)),
        )
    else:
        raise ValueError(
            f"unknown S0 provider type {provider_type!r} (expected 'fake' or 'openai_compat')"
        )

    return S0SingleLLM(
        provider,
        temperature=float(spec.get("temperature", 0.0)),
        max_output_tokens=int(spec.get("max_output_tokens", 1024)),
        seed=spec.get("seed"),
    )


def s0_requires_missing_credential(config: ExperimentConfig) -> str | None:
    """Return the env-var name S0 needs but is unset, else None.

    Used by the CLI to fail clearly (non-zero) before running a real
    provider without credentials. Never resolves or exposes the secret.
    """
    import os

    spec = dict((config.metadata or {}).get("provider") or {})
    if spec.get("type") != "openai_compat":
        return None
    env_name = spec.get("api_key_env", "ABY_LLM_API_KEY")
    if not os.environ.get(env_name):
        return env_name
    return None
