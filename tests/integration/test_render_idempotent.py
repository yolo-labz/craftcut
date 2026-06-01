"""T037 — second `render` run hits cache and finishes fast (SC-004).

Runs the full render twice on the same project. Asserts second run completes
in < 30 s wall time and manifest latest render stage status is `cached`.
Requires auto-editor, melt, ffmpeg, ffprobe.
"""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

import pytest

from craftcut.commands.render import run_render
from craftcut.config import ProjectLayout
from craftcut.manifest import load_manifest

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

REQUIRED_TOOLS = ("auto-editor", "melt", "ffmpeg", "ffprobe")
CACHE_BUDGET_SECONDS = 30.0


def _require_tools() -> None:
    missing = [t for t in REQUIRED_TOOLS if not shutil.which(t)]
    if missing:
        pytest.skip(f"missing tools: {', '.join(missing)}")


def _synth_clip(path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=duration=2:size=1920x1080:rate=30",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=2",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(path),
        ],
        check=True,
        capture_output=True,
    )


def _seed_project(root: Path) -> ProjectLayout:
    for sub in ("media", "audio-clean", "subtitles", "cuts"):
        (root / sub).mkdir(exist_ok=True)
    _synth_clip(root / "media" / "clip01.mov")
    (root / "section-map.yaml").write_text(
        "schema_version: 1\nproject: idempotent\nsections:\n"
        "  - name: intro\n    segments:\n      - { clip: clip01, start: 0, end: 1.5 }\n",
        encoding="utf-8",
    )
    return ProjectLayout.for_project(root)


def test_second_run_hits_cache(tmp_path: Path) -> None:
    _require_tools()
    layout = _seed_project(tmp_path)

    first = run_render(layout)
    assert not isinstance(first, dict)
    assert first.status == "ok"

    t0 = time.monotonic()
    second = run_render(layout)
    wall = time.monotonic() - t0
    assert not isinstance(second, dict)
    assert second.status == "cached"
    assert wall < CACHE_BUDGET_SECONDS

    manifest = load_manifest(layout)
    render_stages = [s for s in manifest.stages if s.stage == "render"]
    assert render_stages, "manifest has no render stage"
    assert render_stages[-1].status == "ok"
