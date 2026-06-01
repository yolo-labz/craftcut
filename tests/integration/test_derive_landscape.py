"""T062 — derive --landscape dry-run emits ffmpeg argv with pillarbox filter chain."""

from __future__ import annotations

from pathlib import Path

from craftcut.commands.derive import run_derive
from craftcut.config import ProjectLayout
from craftcut.runners.ffmpeg import landscape_argv


def test_landscape_dryrun_plans_ffmpeg(micro_project: Path) -> None:
    (micro_project / ".craftcut").mkdir(exist_ok=True)
    (micro_project / ".craftcut" / "master.mp4").write_bytes(b"stub")
    layout = ProjectLayout.for_project(micro_project)
    result = run_derive(layout, landscape=True, dry_run=True)
    assert result.status == "ok"
    assert result.mode == "landscape"
    assert result.outputs == [micro_project / "derivatives" / "landscape.mp4"]


def test_landscape_argv_contains_pillarbox_filter(tmp_path: Path) -> None:
    argv = landscape_argv(
        tmp_path / "master.mp4", tmp_path / "out.mp4", hwaccel=False, lenient=True
    )
    chain = " ".join(argv)
    assert "gblur=sigma=24" in chain
    assert "scale=1920:1080" in chain
    assert "overlay=(W-w)/2:0" in chain
