"""BLAKE3 content hashing for manifest idempotency."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from pathlib import Path

try:
    import blake3 as _blake3
except ImportError:  # pragma: no cover — hard dep
    _blake3 = None


_CHUNK = 1 << 20  # 1 MiB


def file_hash(path: Path) -> str:
    """Hash a file's contents with BLAKE3 (preferred) or BLAKE2b fallback."""
    hasher = _blake3.blake3() if _blake3 else hashlib.blake2b()
    with path.open("rb") as fp:
        while chunk := fp.read(_CHUNK):
            hasher.update(chunk)
    return hasher.hexdigest()


def combined_key(parts: Iterable[str]) -> str:
    """Deterministic cache key from ordered parts (stage inputs)."""
    hasher = _blake3.blake3() if _blake3 else hashlib.blake2b()
    for part in parts:
        hasher.update(part.encode("utf-8"))
        hasher.update(b"\x00")
    return hasher.hexdigest()
