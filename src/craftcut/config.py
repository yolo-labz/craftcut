"""Per-project config (`.craftcut/config.toml`) + project-folder layout."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from craftcut.platform import nfc


class TrimConfig(BaseModel, extra="forbid"):
    threshold_pct: Annotated[float, Field(ge=0, le=100)] = 4.0
    margin_seconds: Annotated[float, Field(ge=0, le=5)] = 0.2
    jobs: Annotated[int, Field(ge=1)] | None = None


class RenderConfig(BaseModel, extra="forbid"):
    width: int = 1080
    height: int = 1920
    frame_rate: int = 30
    video_bitrate: str = "8M"
    video_maxrate: str = "12M"
    video_bufsize: str = "16M"
    audio_bitrate: str = "192k"
    hwaccel: bool = True
    subtitle_font: str = "SF Pro"
    subtitle_font_size: int = 28
    subtitle_margin_v: int = 80


class ValidateConfig(BaseModel, extra="forbid"):
    strict: bool = False
    ignore_rotation: bool = False
    disk_budget_multiplier: Annotated[float, Field(ge=1)] = 3.0


class LogConfig(BaseModel, extra="forbid"):
    retention_days: Annotated[int, Field(ge=1)] = 30
    retention_floor: Annotated[int, Field(ge=1)] = 10
    gzip_after_days: Annotated[int, Field(ge=1)] = 7


class CraftcutProjectConfig(BaseModel, extra="forbid"):
    schema_version: Literal[1] = 1
    trim: TrimConfig = Field(default_factory=TrimConfig)
    render: RenderConfig = Field(default_factory=RenderConfig)
    validate_: ValidateConfig = Field(default_factory=ValidateConfig, alias="validate")
    log: LogConfig = Field(default_factory=LogConfig)

    model_config = {"populate_by_name": True}


class ProjectLayout(BaseModel, frozen=True):
    """Conventional layout inside a project folder."""

    root: Path
    media: Path
    audio: Path
    subtitles: Path
    cuts: Path
    state: Path
    logs: Path
    manifest: Path
    progress: Path
    config: Path
    section_map: Path

    @classmethod
    def for_project(cls, root: Path) -> ProjectLayout:
        root = root.expanduser().resolve()
        state = root / ".craftcut"
        return cls(
            root=root,
            media=root / "media",
            audio=root / "audio-clean",
            subtitles=root / "subtitles",
            cuts=root / "cuts",
            state=state,
            logs=state / "logs",
            manifest=state / "manifest.json",
            progress=state / "progress.json",
            config=state / "config.toml",
            section_map=root / "section-map.yaml",
        )


def load_project_config(layout: ProjectLayout) -> CraftcutProjectConfig:
    """Load `.craftcut/config.toml`; missing file returns defaults."""
    if not layout.config.exists():
        return CraftcutProjectConfig()
    with layout.config.open("rb") as fp:
        raw = tomllib.load(fp)
    return CraftcutProjectConfig.model_validate(raw)


def within_project_root(candidate: Path, layout: ProjectLayout) -> bool:
    """FR-046 path-traversal guard. Uses `realpath` then checks prefix."""
    real = Path(nfc(str(candidate))).expanduser().resolve()
    try:
        real.relative_to(layout.root)
    except ValueError:
        return False
    return True
