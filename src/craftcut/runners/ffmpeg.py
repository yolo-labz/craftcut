"""ffmpeg helpers for derive subcommand."""

from __future__ import annotations

import subprocess
from pathlib import Path

from craftcut.errors import ExternalToolError
from craftcut.runners._proc import resolve_tool, resolve_tool_or_name


def _ffmpeg(lenient: bool) -> str:
    return resolve_tool_or_name("ffmpeg") if lenient else resolve_tool("ffmpeg")


def landscape_argv(
    master: Path, output: Path, *, hwaccel: bool, lenient: bool = False
) -> list[str]:
    vf = (
        "split[bg][fg];"
        "[bg]scale=1920:1080:force_original_aspect_ratio=increase,"
        "crop=1920:1080,gblur=sigma=24[bgblur];"
        "[fg]scale=-1:1080[fgscaled];"
        "[bgblur][fgscaled]overlay=(W-w)/2:0"
    )
    vcodec = "h264_videotoolbox" if hwaccel else "libx264"
    return [
        _ffmpeg(lenient),
        "-y",
        "-i",
        str(master),
        "-filter_complex",
        vf,
        "-c:v",
        vcodec,
        "-b:v",
        "8M",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(output),
    ]


def short_argv(
    master: Path,
    output: Path,
    *,
    start_seconds: float,
    duration_seconds: float,
    hwaccel: bool,
    lenient: bool = False,
) -> list[str]:
    vcodec = "h264_videotoolbox" if hwaccel else "libx264"
    return [
        _ffmpeg(lenient),
        "-y",
        "-ss",
        f"{start_seconds}",
        "-i",
        str(master),
        "-t",
        f"{duration_seconds}",
        "-c:v",
        vcodec,
        "-b:v",
        "8M",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        str(output),
    ]


def run_argv(argv: list[str], *, timeout: float | None = None) -> None:
    try:
        subprocess.run(  # noqa: S603 — argv list, trusted binary
            argv,
            check=True,
            capture_output=True,
            text=True,
            start_new_session=True,
            timeout=timeout,
        )
    except subprocess.CalledProcessError as err:
        raise ExternalToolError(f"ffmpeg exit {err.returncode}: {err.stderr}") from err
    except subprocess.TimeoutExpired as err:
        raise ExternalToolError("ffmpeg timed out") from err
