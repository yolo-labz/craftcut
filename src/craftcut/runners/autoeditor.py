"""auto-editor subprocess wrapper.

FR-045: argv as list, no shell. Uses `subprocess.run` with
`start_new_session=True` so cancel can send SIGTERM to the entire group.
"""

from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path

from craftcut.errors import ExternalToolError
from craftcut.runners._proc import resolve_tool, resolve_tool_or_name


def build_argv(
    source: Path,
    output_fcpxml: Path,
    *,
    threshold_pct: float,
    margin_seconds: float,
    lenient: bool = False,
) -> list[str]:
    binary = resolve_tool_or_name("auto-editor") if lenient else resolve_tool("auto-editor")
    return [
        binary,
        str(source),
        "--edit",
        f"audio:threshold={threshold_pct / 100:.4f}",
        "--margin",
        f"{margin_seconds}sec",
        "--export",
        "final-cut-pro",
        "--output",
        str(output_fcpxml),
        "--no-open",
    ]


def trim_clip(
    source: Path,
    output_fcpxml: Path,
    *,
    threshold_pct: float,
    margin_seconds: float,
    timeout: float = 1800,
) -> None:
    """Blocking invocation — wrap in a thread pool for parallel fan-out."""
    argv = build_argv(
        source, output_fcpxml, threshold_pct=threshold_pct, margin_seconds=margin_seconds
    )
    output_fcpxml.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(  # noqa: S603 — argv list, trusted binary via PATH
            argv,
            check=True,
            capture_output=True,
            text=True,
            start_new_session=True,
            timeout=timeout,
        )
    except subprocess.CalledProcessError as err:
        raise ExternalToolError(
            f"auto-editor exit {err.returncode} on {source.name}: {err.stderr}"
        ) from err
    except subprocess.TimeoutExpired as err:
        raise ExternalToolError(f"auto-editor timeout on {source.name}") from err


def kill_group(pid: int) -> None:
    """Send SIGTERM to the process-group spawned with start_new_session."""
    import contextlib

    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(os.getpgid(pid), signal.SIGTERM)
