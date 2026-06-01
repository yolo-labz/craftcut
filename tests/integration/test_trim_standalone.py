"""T044 — trim runs standalone (no prior validate/restructure)."""

from __future__ import annotations

from pathlib import Path

from craftcut.commands.trim import run_trim
from craftcut.config import ProjectLayout


def test_trim_dryrun_standalone(micro_project: Path) -> None:
    (micro_project / "media" / "clip01.mov").write_bytes(b"stub")
    layout = ProjectLayout.for_project(micro_project)
    result = run_trim(layout, dry_run=True)
    assert result.status == "ok"
    assert [c.clip for c in result.clips] == ["clip01"]
    assert result.clips[0].fcpxml_path == layout.cuts / "clip01.fcpxml"
