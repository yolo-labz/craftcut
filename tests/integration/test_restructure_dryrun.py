"""T045-lite — restructure --dry-run emits plan without OTIO invocation."""

from __future__ import annotations

from pathlib import Path

from craftcut.commands.restructure import run_restructure
from craftcut.config import ProjectLayout


def test_restructure_dryrun(micro_project: Path) -> None:
    layout = ProjectLayout.for_project(micro_project)
    report = run_restructure(layout, dry_run=True)
    assert report.status == "ok"
    assert report.total_runtime_seconds == 1.0
    assert report.moves == ["intro: 1 segments"]
    assert report.polished_fcpxml == layout.state / "polished.mlt_xml"
