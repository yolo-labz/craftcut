"""T054 — broken fixture: SRT overrun + rotation drift named; exit 2 via CLI."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from craftcut.commands import validate as vmod
from craftcut.config import ProjectLayout
from craftcut.models.project import ProbeResult

runner = CliRunner()


def _probe_rotated(path: Path) -> ProbeResult:
    return ProbeResult(
        path=path,
        width=1920,
        height=1080,
        rotation=90,
        frame_rate=30.0,
        duration_seconds=5.0,
        codec="h264",
    )


def _write_fixture(project: Path) -> None:
    (project / "media" / "clip01.mov").write_bytes(b"x" * 1024)
    (project / "subtitles" / "clip01.srt").write_text(
        "1\n00:00:00,000 --> 00:00:20,000\noverrun\n", encoding="utf-8"
    )
    (project / "cuts").mkdir(exist_ok=True)
    (project / "cuts" / "clip01.fcpxml").write_text(
        '<fcpxml version="1.9"><resources><asset duration="150/30s" '
        'rotation="0"/></resources></fcpxml>\n',
        encoding="utf-8",
    )


def test_validate_flags_both_defects(micro_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_fixture(micro_project)
    monkeypatch.setattr(vmod, "probe_file", _probe_rotated)
    layout = ProjectLayout.for_project(micro_project)
    report = vmod.run_validate(layout, strict=False)
    assert report.status == "failed"
    codes = {f.code for f in report.findings}
    assert "VAL_SRT_OVERRUN" in codes
    rotation_codes = {w.code for w in report.warnings}
    assert "VAL_ROTATION_DRIFT" in rotation_codes


def test_validate_strict_promotes_warnings(
    micro_project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_fixture(micro_project)
    monkeypatch.setattr(vmod, "probe_file", _probe_rotated)
    layout = ProjectLayout.for_project(micro_project)
    report = vmod.run_validate(layout, strict=True)
    codes = {f.code for f in report.findings}
    assert "VAL_ROTATION_DRIFT" in codes
    assert report.warnings == []
