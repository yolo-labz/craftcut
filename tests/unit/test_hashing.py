"""Hashing determinism."""

from __future__ import annotations

from pathlib import Path

from craftcut.hashing import combined_key, file_hash


def test_file_hash_deterministic(tmp_path: Path) -> None:
    p = tmp_path / "x.bin"
    p.write_bytes(b"hello world")
    assert file_hash(p) == file_hash(p)


def test_combined_key_order_sensitive() -> None:
    assert combined_key(["a", "b"]) != combined_key(["b", "a"])
