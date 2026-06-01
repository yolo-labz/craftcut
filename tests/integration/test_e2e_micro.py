"""T036 — end-to-end render on a micro fixture (US1).

Exercises the full `render` pipeline: discover → trim → restructure → melt.
Requires `auto-editor`, `melt`, `ffmpeg`, `ffprobe` on PATH. Skips otherwise.
Generates its own 2 s 1080p test clip via ffmpeg `testsrc2` + sine audio so it
is hermetic.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from craftcut.commands.render import run_render
from craftcut.config import ProjectLayout
from craftcut.probe import probe_file

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

REQUIRED_TOOLS = ("auto-editor", "melt", "ffmpeg", "ffprobe")


def _require_tools() -> None:
    missing = [t for t in REQUIRED_TOOLS if not shutil.which(t)]
    if missing:
        pytest.skip(f"missing tools: {', '.join(missing)}")


def _synth_clip(path: Path, *, duration: int = 2) -> None:
    argv = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        f"testsrc2=duration={duration}:size=1920x1080:rate=30",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=440:duration={duration}",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        str(path),
    ]
    subprocess.run(argv, check=True, capture_output=True)


def _seed_project(root: Path) -> ProjectLayout:
    for sub in ("media", "audio-clean", "subtitles", "cuts"):
        (root / sub).mkdir(exist_ok=True)
    _synth_clip(root / "media" / "clip01.mov")
    (root / "section-map.yaml").write_text(
        "schema_version: 1\nproject: e2e-micro\nsections:\n"
        "  - name: intro\n    segments:\n      - { clip: clip01, start: 0, end: 1.5 }\n",
        encoding="utf-8",
    )
    return ProjectLayout.for_project(root)


def test_e2e_micro_render(tmp_path: Path) -> None:
    _require_tools()
    layout = _seed_project(tmp_path)
    result = run_render(layout)
    assert not isinstance(result, dict)
    assert result.status == "ok"
    assert result.output_path.exists()

    probe = probe_file(result.output_path)
    assert probe.width == 1080
    assert probe.height == 1920
    assert probe.duration_seconds > 0
