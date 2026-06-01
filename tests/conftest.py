"""Shared fixtures for contract, unit, and integration tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def micro_project(tmp_path: Path) -> Path:
    """Create a minimal project-folder skeleton in tmp_path."""
    for sub in ("media", "audio-clean", "subtitles", "cuts"):
        (tmp_path / sub).mkdir()
    (tmp_path / "section-map.yaml").write_text(
        "schema_version: 1\nproject: micro\nsections:\n"
        "  - name: intro\n    segments:\n"
        "      - { clip: clip01, start: 0, end: 1 }\n",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"
