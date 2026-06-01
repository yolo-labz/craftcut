"""Per-subcommand report models returned on stdout (--json)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from craftcut.models.manifest import Finding, Warning_


class DoctorTool(BaseModel, extra="forbid"):
    name: str
    present: bool
    version: str | None = None
    path: Path | None = None
    remedy: str | None = None


class DoctorReport(BaseModel, extra="forbid"):
    schema_version: Literal[1] = 1
    ok: bool
    tools: list[DoctorTool]


class ValidateReport(BaseModel, extra="forbid"):
    schema_version: Literal[1] = 1
    status: Literal["ok", "failed"]
    clip_count: int
    warnings: list[Warning_] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)


class TrimClip(BaseModel, extra="forbid"):
    clip: str
    input_duration: float
    output_duration: float
    removed_seconds: float
    fcpxml_path: Path


class TrimResult(BaseModel, extra="forbid"):
    schema_version: Literal[1] = 1
    status: Literal["ok", "failed", "cached"]
    clips: list[TrimClip]
    total_removed: float


class RestructureReport(BaseModel, extra="forbid"):
    schema_version: Literal[1] = 1
    status: Literal["ok", "failed", "cached"]
    polished_fcpxml: Path
    total_runtime_seconds: float
    cuts_per_minute: float
    pacing_warning: bool = False
    moves: list[str] = Field(default_factory=list)


class RenderResult(BaseModel, extra="forbid"):
    schema_version: Literal[1] = 1
    status: Literal["ok", "failed", "cached"]
    output_path: Path
    width: int
    height: int
    frame_rate: float
    duration_seconds: float
    file_size_bytes: int
    wall_seconds: float
    probe_ok: bool


class DeriveResult(BaseModel, extra="forbid"):
    schema_version: Literal[1] = 1
    status: Literal["ok", "failed", "cached"]
    mode: Literal["landscape", "shorts"]
    outputs: list[Path]
