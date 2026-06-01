"""melt subprocess wrapper — consumer string per R17."""

from __future__ import annotations

import subprocess
from pathlib import Path

from craftcut.config import RenderConfig
from craftcut.errors import ExternalToolError
from craftcut.runners._proc import resolve_tool, resolve_tool_or_name

SUBTITLE_FONT_STACK = ("SF Pro", "Helvetica Neue", "Helvetica", "sans-serif")


def build_subtitle_style(cfg: RenderConfig) -> str:
    """SSA `force_style` string (FR-037, R3).

    Font stack SF Pro → Helvetica Neue → Helvetica → sans-serif. FontSize=28,
    MarginV=80 — tuned for 1080x1920 portrait.
    """
    primary = cfg.subtitle_font or SUBTITLE_FONT_STACK[0]
    return (
        f"FontName={primary},"
        f"FontSize={cfg.subtitle_font_size},"
        f"MarginV={cfg.subtitle_margin_v},"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H80000000,"
        "BorderStyle=3,"
        "Outline=2,"
        "Shadow=0,"
        "Alignment=2"
    )


def build_consumer(cfg: RenderConfig, output: Path, *, hwaccel: bool) -> list[str]:
    """Consumer params: R17 — H.264 VBR capped, VT when hwaccel."""
    target = "avformat:" + str(output)
    vcodec = "h264_videotoolbox" if hwaccel else "libx264"
    params = [
        target,
        f"vcodec={vcodec}",
        f"vb={cfg.video_bitrate}",
        f"maxrate={cfg.video_maxrate}",
        f"vbufsize={cfg.video_bufsize}",
        "acodec=aac",
        f"ab={cfg.audio_bitrate}",
        f"width={cfg.width}",
        f"height={cfg.height}",
        f"frame_rate_num={cfg.frame_rate}",
        "frame_rate_den=1",
        "real_time=-1",
        "rescale=bilinear",
        "threads=0",
    ]
    if not hwaccel:
        params += ["preset=veryfast", "crf=19"]
    params.append(f"sub_style={build_subtitle_style(cfg)}")
    return params


def build_argv(
    mlt_xml: Path, output: Path, cfg: RenderConfig, *, hwaccel: bool, lenient: bool = False
) -> list[str]:
    binary = resolve_tool_or_name("melt") if lenient else resolve_tool("melt")
    return [
        binary,
        str(mlt_xml),
        "-consumer",
        *build_consumer(cfg, output, hwaccel=hwaccel),
    ]


def run_melt(
    mlt_xml: Path,
    output: Path,
    cfg: RenderConfig,
    *,
    hwaccel: bool = True,
    timeout: float | None = None,
) -> None:
    argv = build_argv(mlt_xml, output, cfg, hwaccel=hwaccel)
    output.parent.mkdir(parents=True, exist_ok=True)
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
        raise ExternalToolError(f"melt exit {err.returncode}: {err.stderr}") from err
    except subprocess.TimeoutExpired as err:
        raise ExternalToolError("melt timed out") from err
