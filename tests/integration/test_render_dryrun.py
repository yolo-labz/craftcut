"""T035 — `render --dry-run` emits DAG JSON without invoking melt (R23)."""

from __future__ import annotations

from pathlib import Path

from craftcut.commands.render import build_dag
from craftcut.config import ProjectLayout, load_project_config


def test_render_dryrun_emits_dag(micro_project: Path) -> None:
    (micro_project / "media" / "clip01.mov").write_bytes(b"not-a-real-mov")
    layout = ProjectLayout.for_project(micro_project)
    cfg = load_project_config(layout)

    dag = build_dag(layout, cfg)

    assert dag["schema"] == "craftcut.render.v1"
    assert dag["status"] == "dry_run"
    node_ids = [n["id"] for n in dag["nodes"]]
    assert "trim:clip01" in node_ids
    assert "restructure" in node_ids
    assert "render" in node_ids
    render_node = next(n for n in dag["nodes"] if n["id"] == "render")
    assert render_node["depends_on"] == ["restructure"]
    assert "melt" in render_node["argv"][0]


def test_render_dryrun_handles_empty_media(micro_project: Path) -> None:
    layout = ProjectLayout.for_project(micro_project)
    cfg = load_project_config(layout)
    dag = build_dag(layout, cfg)
    trim_nodes = [n for n in dag["nodes"] if n["stage"] == "trim"]
    assert trim_nodes == []
