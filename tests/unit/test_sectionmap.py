"""Section-map YAML loader + hardening."""

from __future__ import annotations

from pathlib import Path

import pytest

from craftcut.config import ProjectLayout
from craftcut.errors import BadInputError
from craftcut.sandbox import load_section_map


def test_happy_path(micro_project: Path) -> None:
    layout = ProjectLayout.for_project(micro_project)
    sm = load_section_map(micro_project / "section-map.yaml", layout)
    assert sm.schema_version == 1
    assert sm.sections[0].name == "intro"


def test_refuses_escape(tmp_path: Path) -> None:
    layout = ProjectLayout.for_project(tmp_path)
    outside = tmp_path.parent / "escape.yaml"
    outside.write_text("schema_version: 1\nproject: bad\nsections: []\n", encoding="utf-8")
    try:
        with pytest.raises(BadInputError):
            load_section_map(outside, layout)
    finally:
        outside.unlink(missing_ok=True)
