"""Atomic-rewrite pollable progress file (FR-040, R22).

Claude Code's Bash tool buffers stderr until the process completes, so
mid-run progress must live in a pollable file the operator/LLM can `cat`
between turns. Every tick rewrites `<project>/.craftcut/progress.json`
atomically.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

Stage = Literal["validate", "trim", "restructure", "render", "derive"]
Phase = Literal["prepare", "decode", "filter", "encode", "mux", "verify", "cleanup"]


class ProgressTick(BaseModel, extra="forbid"):
    schema_: Literal["craftcut.progress.v1"] = Field(default="craftcut.progress.v1", alias="schema")
    stage: Stage
    started_at: str
    phase: Phase
    current: float | None = None
    total: float | None = None
    pct: float = Field(ge=0, le=100)
    eta_seconds: float | None = None
    deterministic: bool = True


class ProgressWriter:
    """Atomically rewrite <project>/.craftcut/progress.json on each tick."""

    def __init__(self, path: Path, stage: Stage) -> None:
        self.path = path
        self.stage: Stage = stage
        self.started_at = _utc_now_iso()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def tick(
        self,
        *,
        phase: Phase,
        pct: float,
        current: float | None = None,
        total: float | None = None,
        eta_seconds: float | None = None,
        deterministic: bool = True,
    ) -> None:
        payload = ProgressTick(
            stage=self.stage,
            started_at=self.started_at,
            phase=phase,
            current=current,
            total=total,
            pct=max(0.0, min(100.0, pct)),
            eta_seconds=eta_seconds,
            deterministic=deterministic,
        ).model_dump(by_alias=True, exclude_none=True)
        _atomic_write_json(self.path, payload)

    def close(self, *, phase: Phase = "cleanup") -> None:
        self.tick(phase=phase, pct=100.0)


def _utc_now_iso() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write to tmp in same dir, fsync, rename. F_FULLFSYNC on Darwin."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=path.parent,
        prefix=".progress-",
        suffix=".tmp",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        json.dump(payload, tmp, separators=(",", ":"), ensure_ascii=False)
        tmp.flush()
        fullfsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)


def fullfsync(fd: int) -> None:
    """Darwin F_FULLFSYNC (R19); no-op fsync elsewhere."""
    import contextlib

    try:
        import fcntl

        F_FULLFSYNC = 51  # noqa: N806 — Darwin constant
        fcntl.fcntl(fd, F_FULLFSYNC)
    except (OSError, ValueError, AttributeError):
        with contextlib.suppress(OSError):
            os.fsync(fd)
