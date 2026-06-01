"""Shared subprocess helpers — tool resolution + argv-only dispatch (FR-045)."""

from __future__ import annotations

import shutil

from craftcut.errors import ExternalToolError


def resolve_tool(name: str) -> str:
    binary = shutil.which(name)
    if not binary:
        raise ExternalToolError(f"{name} not found on PATH — run `craftcut doctor`")
    return binary


def resolve_tool_or_name(name: str) -> str:
    """Return PATH binary if available else the bare name (for dry-run DAGs)."""
    return shutil.which(name) or name
