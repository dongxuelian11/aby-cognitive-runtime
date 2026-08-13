"""Provider/model-neutral shared encoder contract and offline reference encoder."""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

REFERENCE_ENCODER_STATUS = "REFERENCE_ONLY_NOT_SEMANTIC_QUALITY_EVIDENCE"
REFERENCE_ENCODER_ID = "reference_hashing"
REFERENCE_ENCODER_REVISION = "p1.5-v0.1"
_TOKEN_PATTERN = re.compile(r"\w+", flags=re.UNICODE)


class EncoderProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    encoder_id: str = Field(min_length=1)
    encoder_revision: str = Field(min_length=1)
    dimension: int = Field(ge=1)
    algorithm_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


@runtime_checkable
class SharedEncoder(Protocol):
    """Replaceable external coordinate contract; independent of chat providers."""

    @property
    def provenance(self) -> EncoderProvenance: ...

    def encode(self, texts: Sequence[str]) -> list[list[float]]: ...


class DeterministicHashingEncoder:
    """Offline replay encoder; infrastructure-only, never a quality claim."""

    encoder_id = REFERENCE_ENCODER_ID
    encoder_revision = REFERENCE_ENCODER_REVISION
    scientific_status = REFERENCE_ENCODER_STATUS

    def __init__(self, dimension: int = 32) -> None:
        if not isinstance(dimension, int) or isinstance(dimension, bool):
            raise TypeError("dimension must be an integer")
        if dimension < 8 or dimension > 4096:
            raise ValueError("reference encoder dimension must be in [8, 4096]")
        self.dimension = dimension
        config = {
            "algorithm": "sha256_signed_token_hash_v1",
            "dimension": dimension,
            "projections_per_token": 4,
            "tokenizer": "unicode_word_casefold_v1",
            "scientific_status": REFERENCE_ENCODER_STATUS,
        }
        raw = json.dumps(config, sort_keys=True, separators=(",", ":"))
        self.algorithm_fingerprint = hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @property
    def provenance(self) -> EncoderProvenance:
        return EncoderProvenance(
            encoder_id=self.encoder_id,
            encoder_revision=self.encoder_revision,
            dimension=self.dimension,
            algorithm_fingerprint=self.algorithm_fingerprint,
        )

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text_index, text in enumerate(texts):
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"texts[{text_index}] must be non-blank")
            tokens = _TOKEN_PATTERN.findall(text.casefold())
            if not tokens:
                raise ValueError(f"texts[{text_index}] has no encodable word tokens")
            vector = [0.0] * self.dimension
            for token in tokens:
                for projection in range(4):
                    digest = hashlib.sha256(
                        f"{token}\x1f{projection}".encode("utf-8")
                    ).digest()
                    slot = int.from_bytes(digest[:8], "big") % self.dimension
                    sign = 1.0 if digest[8] & 1 else -1.0
                    vector[slot] += sign
            if not all(math.isfinite(value) for value in vector):
                raise ValueError("reference encoder produced a non-finite vector")
            vectors.append(vector)
        return vectors


__all__ = [
    "REFERENCE_ENCODER_STATUS",
    "REFERENCE_ENCODER_ID",
    "REFERENCE_ENCODER_REVISION",
    "EncoderProvenance",
    "SharedEncoder",
    "DeterministicHashingEncoder",
]
