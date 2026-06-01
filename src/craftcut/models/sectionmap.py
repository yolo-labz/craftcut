"""Section-map YAML: narrative blueprint handed to restructure."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SectionSegment(BaseModel, extra="forbid"):
    clip: str = Field(description="Source clip stem (NFC-normalized)")
    start: float = Field(ge=0, description="Inclusive start in seconds inside the clip")
    end: float = Field(gt=0, description="Exclusive end in seconds inside the clip")


class Section(BaseModel, extra="forbid"):
    name: str
    segments: list[SectionSegment] = Field(min_length=1)


class SectionMap(BaseModel, extra="forbid"):
    schema_version: Literal[1] = 1
    project: str
    sections: list[Section] = Field(min_length=1)
