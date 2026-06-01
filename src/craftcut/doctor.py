"""External-tool version probes for `craftcut doctor`."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from craftcut.models.reports import DoctorReport, DoctorTool

TOOLS: tuple[tuple[str, str, str, str], ...] = (
    # (name, version-arg, regex, remedy)
    ("ffmpeg", "-version", r"ffmpeg version (\S+)", "brew install ffmpeg"),
    ("ffprobe", "-version", r"ffprobe version (\S+)", "brew install ffmpeg"),
    ("auto-editor", "--version", r"([0-9]+\.[0-9]+\S*)", "uv tool install auto-editor"),
    ("melt", "--version", r"melt ([\d.]+)", "brew install --HEAD mlt"),
)


def probe_tool(name: str, version_arg: str, pattern: str) -> tuple[str | None, Path | None]:
    binary = shutil.which(name)
    if not binary:
        return None, None
    try:
        out = subprocess.run(  # noqa: S603 — argv list, trusted
            [binary, version_arg],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None, Path(binary)
    combined = out.stdout + out.stderr
    match = re.search(pattern, combined)
    if not match:
        return None, Path(binary)
    return match.group(1), Path(binary)


def run_doctor() -> DoctorReport:
    tools: list[DoctorTool] = []
    for name, arg, pattern, remedy in TOOLS:
        version, path = probe_tool(name, arg, pattern)
        tools.append(
            DoctorTool(
                name=name,
                present=version is not None,
                version=version,
                path=path,
                remedy=None if version else remedy,
            )
        )
    ok = all(t.present for t in tools)
    return DoctorReport(ok=ok, tools=tools)
