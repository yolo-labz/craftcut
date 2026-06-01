"""Config + project layout."""

from __future__ import annotations

from pathlib import Path

from craftcut.config import (
    CraftcutProjectConfig,
    ProjectLayout,
    load_project_config,
    within_project_root,
)


def test_layout_paths(tmp_path: Path) -> None:
    layout = ProjectLayout.for_project(tmp_path)
    assert layout.root == tmp_path.resolve()
    assert layout.manifest == tmp_path.resolve() / ".craftcut" / "manifest.json"
    assert layout.progress == tmp_path.resolve() / ".craftcut" / "progress.json"


def test_missing_config_uses_defaults(tmp_path: Path) -> None:
    layout = ProjectLayout.for_project(tmp_path)
    cfg = load_project_config(layout)
    assert cfg == CraftcutProjectConfig()
    assert cfg.render.width == 1080
    assert cfg.render.height == 1920


def test_config_round_trip(tmp_path: Path) -> None:
    layout = ProjectLayout.for_project(tmp_path)
    layout.state.mkdir()
    layout.config.write_text(
        "schema_version = 1\n[trim]\nthreshold_pct = 6.0\n[render]\nhwaccel = false\n",
        encoding="utf-8",
    )
    cfg = load_project_config(layout)
    assert cfg.trim.threshold_pct == 6.0
    assert cfg.render.hwaccel is False
    assert cfg.validate_.strict is False


def test_path_traversal_guard(tmp_path: Path) -> None:
    layout = ProjectLayout.for_project(tmp_path)
    inside = tmp_path / "media" / "foo.mov"
    outside = tmp_path.parent / "other.mov"
    assert within_project_root(inside, layout)
    assert not within_project_root(outside, layout)
