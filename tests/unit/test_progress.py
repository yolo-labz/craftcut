"""progress.json atomic rewrite."""

from __future__ import annotations

import json
from pathlib import Path

from craftcut.progress import ProgressWriter


def test_atomic_rewrite(tmp_path: Path) -> None:
    path = tmp_path / "progress.json"
    writer = ProgressWriter(path, stage="render")
    writer.tick(phase="encode", pct=42.5, current=100, total=235)
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema"] == "craftcut.progress.v1"
    assert data["stage"] == "render"
    assert data["phase"] == "encode"
    assert data["pct"] == 42.5


def test_close_sets_100(tmp_path: Path) -> None:
    path = tmp_path / "progress.json"
    writer = ProgressWriter(path, stage="trim")
    writer.close()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["pct"] == 100
    assert data["phase"] == "cleanup"
