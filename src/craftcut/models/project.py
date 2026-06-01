"""Project / SourceClip / ProbeResult entities."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class ProbeResult(BaseModel, extra="forbid"):
    path: Path
    width: int
    height: int
    rotation: int = 0
    sample_aspect_ratio: str = "1:1"
    frame_rate: float
    duration_seconds: float
    codec: str
    audio_codec: str | None = None
    audio_channels: int | None = None
    audio_sample_rate: int | None = None
    container_duration_seconds: float | None = None


class SourceClip(BaseModel, extra="forbid"):
    stem: str
    video: Path
    audio_clean: Path | None = None
    subtitle: Path | None = None
    probe: ProbeResult | None = None


class Project(BaseModel, extra="forbid"):
    root: Path
    clips: list[SourceClip] = Field(default_factory=list)
    section_map_path: Path | None = None
    butter_cut_fcpxml: Path | None = None
