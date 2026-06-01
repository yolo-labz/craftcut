"""Run manifest (`.craftcut/manifest.json`) — stage history + tool versions."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

StageName = Literal["doctor", "validate", "trim", "restructure", "render", "derive"]
Status = Literal["ok", "failed", "cached", "skipped"]


class Warning_(BaseModel, extra="forbid"):
    code: str
    message: str
    clip: str | None = None


class Finding(BaseModel, extra="forbid"):
    code: str
    message: str
    clip: str | None = None
    remedy: str | None = None


class StageReport(BaseModel, extra="forbid"):
    stage: StageName
    status: Status
    started_at: str
    finished_at: str
    wall_seconds: float
    cache_key: str | None = None
    argv: list[str] = Field(default_factory=list)
    inputs: dict[str, str] = Field(default_factory=dict)
    outputs: dict[str, str] = Field(default_factory=dict)
    warnings: list[Warning_] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


class ToolVersion(BaseModel, extra="forbid"):
    name: str
    version: str
    path: Path


class Manifest(BaseModel, extra="forbid"):
    schema_version: Literal[1] = 1
    project: Path
    created_at: str
    updated_at: str
    craftcut_version: str
    tool_versions: list[ToolVersion] = Field(default_factory=list)
    stages: list[StageReport] = Field(default_factory=list)
