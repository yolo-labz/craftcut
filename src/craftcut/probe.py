"""ffprobe wrapper. Returns typed ProbeResult; raises ExternalToolError on failure."""

from __future__ import annotations

import json
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

from craftcut.errors import ExternalToolError
from craftcut.models.project import ProbeResult


def _find_ffprobe() -> str:
    binary = shutil.which("ffprobe")
    if not binary:
        raise ExternalToolError("ffprobe not found on PATH")
    return binary


def probe_file(path: Path) -> ProbeResult:
    """Run ffprobe on a media file and return a typed result."""
    argv = [
        _find_ffprobe(),
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_streams",
        "-show_format",
        str(path),
    ]
    try:
        out = subprocess.run(  # noqa: S603 — argv list, tool resolved via PATH
            argv,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.CalledProcessError as exc:
        raise ExternalToolError(f"ffprobe failed: {exc.stderr}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ExternalToolError("ffprobe timed out after 30 s") from exc

    payload = json.loads(out.stdout)
    video = next(s for s in payload["streams"] if s.get("codec_type") == "video")
    audio = next((s for s in payload["streams"] if s.get("codec_type") == "audio"), None)

    rotation = 0
    for sd in video.get("side_data_list") or []:
        if "rotation" in sd:
            rotation = int(sd["rotation"])
            break

    frame_rate = _parse_rational(video.get("r_frame_rate") or "0/1")
    duration = float(video.get("duration") or payload["format"].get("duration") or 0)

    return ProbeResult(
        path=path,
        width=int(video["width"]),
        height=int(video["height"]),
        rotation=rotation,
        sample_aspect_ratio=video.get("sample_aspect_ratio") or "1:1",
        frame_rate=frame_rate,
        duration_seconds=duration,
        codec=str(video.get("codec_name") or "unknown"),
        audio_codec=str(audio["codec_name"]) if audio else None,
        audio_channels=int(audio["channels"]) if audio else None,
        audio_sample_rate=int(audio["sample_rate"]) if audio else None,
        container_duration_seconds=float(payload["format"].get("duration") or 0) or None,
    )


def _parse_rational(rational: str) -> float:
    try:
        frac = Fraction(rational)
    except (ZeroDivisionError, ValueError):
        return 0.0
    return float(frac)
