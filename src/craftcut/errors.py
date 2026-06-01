"""RFC 9457 Problem Details error envelope for craftcut.

Emitted on stdout when `--json` is set and the subcommand exits non-zero.
Schema: contracts/error.schema.json, discriminator `craftcut.error.v1`.
"""

from __future__ import annotations

import json
import sys
from typing import Literal

from pydantic import BaseModel, Field

Stage = Literal["doctor", "validate", "trim", "restructure", "render", "derive"]
StatusCode = Literal[2, 3, 4, 5]


class CraftcutError(BaseModel, extra="allow"):
    """RFC 9457 Problem Details with craftcut extensions."""

    schema_: Literal["craftcut.error.v1"] = Field(default="craftcut.error.v1", alias="schema")
    type: str = Field(description="URI identifying the error kind.")
    title: str
    status: StatusCode
    code: str = Field(description="Stable SCREAMING_SNAKE_CASE enum.")
    detail: str
    remedy: str
    instance: str | None = None
    stage: Stage | None = None
    clip: str | None = None
    doc_url: str | None = None

    def emit_and_exit(self) -> None:
        """Write envelope to stdout and exit with the carried status."""
        json.dump(
            self.model_dump(by_alias=True, exclude_none=True),
            sys.stdout,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        sys.stdout.write("\n")
        sys.stdout.flush()
        raise SystemExit(self.status)


class BadInputError(Exception):
    """exit 2 — operator supplied bad input."""

    code = "BAD_INPUT"
    status: StatusCode = 2


class SourceIntegrityError(Exception):
    """exit 3 — source probe mismatch."""

    code = "SOURCE_INTEGRITY"
    status: StatusCode = 3


class ExternalToolError(Exception):
    """exit 4 — auto-editor / melt / ffmpeg failure."""

    code = "EXTERNAL_TOOL"
    status: StatusCode = 4


class InternalError(Exception):
    """exit 5 — craftcut bug."""

    code = "INTERNAL"
    status: StatusCode = 5
