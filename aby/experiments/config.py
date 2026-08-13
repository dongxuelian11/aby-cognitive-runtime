"""Versioned experiment configuration — P1.1 contract.

NOT part of the P0 freeze. The P0 frozen telemetry contract is separate.

Design rules (P1.1 task §7.1):
- serializable, JSON round-trip;
- unknown top-level fields fail closed (pydantic extra="forbid");
- schema version is explicit;
- no secret material (no API keys, no tokens);
- no ABY-specific fields in the common schema.

Path safety (P1.1 correction D): ``experiment_id`` is used to derive
artifact directory paths, so it must match a strict safe-identifier pattern
(``[A-Za-z0-9._-]+``, not "." or ".."). ``/``, ``\\``, absolute paths and
empty identifiers are rejected.
"""

import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EXPERIMENT_CONFIG_SCHEMA_VERSION = "ABY_EXPERIMENT_CONFIG_V1_0"

SAFE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


def validate_safe_identifier(value: str, field: str = "identifier") -> str:
    """Reject identifiers that could escape the artifact root (correction D)."""
    if not value or not SAFE_IDENTIFIER_PATTERN.match(value) or value in (".", ".."):
        raise ValueError(
            f"unsafe {field} {value!r}: must match [A-Za-z0-9._-]+ "
            f"and must not be empty, '.', or '..'"
        )
    return value


class ExperimentConfig(BaseModel):
    """One reproducible experiment definition.

    ``system_id`` is any neutral label (e.g. "S0".."S3", "null", "echo",
    or an arbitrary baseline name). The harness never interprets its
    meaning beyond selecting an offline deterministic system for dry-runs.
    """

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["ABY_EXPERIMENT_CONFIG_V1_0"]
    experiment_id: str = Field(min_length=1)
    seed: int
    system_id: str = Field(min_length=1)
    dataset_id: str = Field(min_length=1)
    task_family: str = Field(min_length=1)
    difficulty: str = ""
    risk: str = ""
    episode_limit: int = Field(default=1, ge=1)
    timeout_seconds: float = Field(default=30.0, gt=0.0)
    model_config_ref: str = ""
    memory_config_ref: str = ""
    tool_config_ref: str = ""
    telemetry_enabled: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("experiment_id")
    @classmethod
    def _experiment_id_must_be_path_safe(cls, value: str) -> str:
        return validate_safe_identifier(value, field="experiment_id")

    def to_json(self) -> str:
        """Canonical serialized form (also used for config hashing)."""
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, raw: str) -> "ExperimentConfig":
        return cls.model_validate_json(raw)


def load_config(path: str | Path) -> ExperimentConfig:
    """Load and validate an experiment config file (JSON).

    Raises FileNotFoundError or pydantic.ValidationError on failure.
    No network access.
    """
    raw = Path(path).read_text(encoding="utf-8")
    return ExperimentConfig.from_json(raw)
