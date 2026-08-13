"""Small canonical-JSON helpers shared by the P1.6 runtime."""

from __future__ import annotations

import hashlib
import json


def canonical_json(value: object) -> str:
    """Serialize stable evidence without timestamps, NaN, or formatting drift."""

    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


__all__ = ["canonical_json", "canonical_sha256"]
