"""T053 — clean fixture: validate exits 0, zero findings."""

from __future__ import annotations

from pathlib import Path

import pytest

from craftcut.commands import validate as vmod
from craftcut.config import ProjectLayout
from craftcut.models.project import ProbeResult


def _probe(path: Path) -> ProbeResult:
    return ProbeResult(
        path=path,
        width=1920,
        height=1080,
        rotation=0,
        frame_rate=30.0,
        duration_seconds=10.0,
        codec="h264",
    )


def test_validate_clean(micro_project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (micro_project / "media" / "clip01.mov").write_bytes(b"x" * 1024)
    (micro_project / "subtitles" / "clip01.srt").write_text(
        "1\n00:00:00,000 --> 00:00:05,000\nhi\n", encoding="utf-8"
    )
    monkeypatch.setattr(vmod, "probe_file", _probe)
    layout = ProjectLayout.for_project(micro_project)
    report = vmod.run_validate(layout)
    assert report.status == "ok"
    assert report.findings == []
    assert report.clip_count == 1
