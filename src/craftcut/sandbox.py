"""YAML hardening (FR-044) + section-map loader."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import structlog
from ruamel.yaml import YAML
from ruamel.yaml.nodes import MappingNode, SequenceNode

from craftcut.config import ProjectLayout, within_project_root
from craftcut.errors import BadInputError
from craftcut.models.sectionmap import SectionMap

_log = structlog.get_logger(__name__)


def reject_non_scalar_anchors(node: object) -> None:
    """FR-044 — refuse aliases/anchors on non-scalar nodes."""
    anchor = getattr(node, "anchor", None)
    if isinstance(node, (MappingNode, SequenceNode)) and anchor and anchor.value:
        raise BadInputError(f"YAML anchors on {type(node).__name__} are refused (FR-044)")


def load_section_map(
    path: Path,
    layout: ProjectLayout,
    *,
    allow_outside_root: bool = False,
) -> SectionMap:
    if not within_project_root(path, layout):
        if not allow_outside_root:
            raise BadInputError(f"section-map path {path} escapes project root {layout.root}")
        _log.warning(
            "path_root_guard_bypassed",
            path=str(path),
            root=str(layout.root),
            reason="--allow-outside-root",
        )
    yaml = YAML(typ="safe")
    yaml.composer.check_data = lambda: True  # type: ignore[attr-defined]
    with path.open("r", encoding="utf-8") as fp:
        try:
            raw: Any = yaml.load(fp)
        except Exception as err:
            raise BadInputError(f"section-map YAML parse failed: {err}") from err
    if not isinstance(raw, dict):
        raise BadInputError("section-map root must be a mapping")
    return SectionMap.model_validate(raw)
