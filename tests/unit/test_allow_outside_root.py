"""T052b — --allow-outside-root bypasses FR-046 guard with audit log."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from craftcut.config import ProjectLayout
from craftcut.errors import BadInputError
from craftcut.sandbox import load_section_map

SECTION_MAP = (
    "schema_version: 1\nproject: outside\nsections:\n"
    "  - name: intro\n    segments:\n"
    "      - { clip: clip01, start: 0, end: 1 }\n"
)


def _outside(tmp_path: Path) -> tuple[Path, ProjectLayout]:
    project = tmp_path / "proj"
    project.mkdir()
    outside = tmp_path / "outside" / "section-map.yaml"
    outside.parent.mkdir()
    outside.write_text(SECTION_MAP, encoding="utf-8")
    return outside, ProjectLayout.for_project(project)


def test_outside_root_rejected_by_default(tmp_path: Path) -> None:
    outside, layout = _outside(tmp_path)
    with pytest.raises(BadInputError, match="escapes project root"):
        load_section_map(outside, layout)


def test_allow_outside_root_permits_with_audit(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    outside, layout = _outside(tmp_path)
    with caplog.at_level(logging.WARNING):
        smap = load_section_map(outside, layout, allow_outside_root=True)
    assert smap.project == "outside"
