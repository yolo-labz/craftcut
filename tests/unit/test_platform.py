"""Platform utilities."""

from __future__ import annotations

from craftcut.platform import nfc


def test_nfc_normalizes_ios_decomposed() -> None:
    decomposed = "cafe\u0301"
    assert nfc(decomposed) == "café"
