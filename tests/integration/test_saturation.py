"""T043 — powermetrics harness verifies GPU/P-cluster ≥ 80% during render (NFR-PERF-01).

Reads `powermetrics -s gpu_power,cpu_power --sample-count N --sample-rate 1000`
in parallel with the render. Parses plist `--format plist`. Requires sudo.
Skipped unless `CRAFTCUT_SATURATION=1` is set (CI opt-in).
"""

from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from craftcut.commands.render import run_render
from craftcut.config import ProjectLayout

pytestmark = [pytest.mark.integration, pytest.mark.saturation, pytest.mark.e2e]

REQUIRED_TOOLS = ("auto-editor", "melt", "ffmpeg", "ffprobe", "powermetrics")
MIN_RESIDENCY_PCT = 80.0
SAMPLE_MS = 1000


def _require() -> None:
    if sys.platform != "darwin":
        pytest.skip("powermetrics is macOS-only")
    if os.environ.get("CRAFTCUT_SATURATION") != "1":
        pytest.skip("set CRAFTCUT_SATURATION=1 to run saturation tests (sudo required)")
    missing = [t for t in REQUIRED_TOOLS if not shutil.which(t)]
    if missing:
        pytest.skip(f"missing tools: {', '.join(missing)}")


def _synth_clip(path: Path, duration: int = 10) -> None:
    subprocess.run(
        [
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
        ],
        check=True,
        capture_output=True,
    )


def _seed_project(root: Path) -> ProjectLayout:
    for sub in ("media", "audio-clean", "subtitles", "cuts"):
        (root / sub).mkdir(exist_ok=True)
    _synth_clip(root / "media" / "clip01.mov")
    (root / "section-map.yaml").write_text(
        "schema_version: 1\nproject: saturation\nsections:\n"
        "  - name: intro\n    segments:\n      - { clip: clip01, start: 0, end: 9.5 }\n",
        encoding="utf-8",
    )
    return ProjectLayout.for_project(root)


def _peak_residency(plist_bytes: bytes) -> tuple[float, float]:
    """Return (gpu_active_pct, p_cluster_active_pct) peaks across all samples."""
    gpu_peak = 0.0
    p_peak = 0.0
    for chunk in plist_bytes.split(b"\x00"):
        if not chunk.strip():
            continue
        try:
            sample = plistlib.loads(chunk)
        except plistlib.InvalidFileException:
            continue
        gpu = sample.get("gpu", {}).get("hw_active_residency")
        if isinstance(gpu, (int, float)):
            gpu_peak = max(gpu_peak, float(gpu) * 100)
        for cluster in sample.get("processor", {}).get("clusters", []):
            if "P" in str(cluster.get("name", "")):
                res = cluster.get("hw_active_residency")
                if isinstance(res, (int, float)):
                    p_peak = max(p_peak, float(res) * 100)
    return gpu_peak, p_peak


def test_render_saturates_gpu_or_p_cluster(tmp_path: Path) -> None:
    _require()
    layout = _seed_project(tmp_path)
    samples_expected = 20
    proc = subprocess.Popen(
        [
            "sudo",
            "-n",
            "powermetrics",
            "-s",
            "gpu_power,cpu_power",
            "--sample-rate",
            str(SAMPLE_MS),
            "--sample-count",
            str(samples_expected),
            "--format",
            "plist",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    def _render() -> None:
        run_render(layout)

    t = threading.Thread(target=_render)
    t.start()
    t.join()

    try:
        out, _err = proc.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, _err = proc.communicate()

    gpu_peak, p_peak = _peak_residency(out)
    t_start = time.monotonic()
    assert gpu_peak >= MIN_RESIDENCY_PCT or p_peak >= MIN_RESIDENCY_PCT, (
        f"saturation shortfall: gpu={gpu_peak:.1f}% p_cluster={p_peak:.1f}% "
        f"after {time.monotonic() - t_start:.2f}s parse"
    )
