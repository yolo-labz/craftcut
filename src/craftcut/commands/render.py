"""One-command orchestrator: trim → restructure → melt → self-probe (T040).

Emits the full dependency DAG on `--dry-run` (R23, T050).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from craftcut.commands._common import discover_clips, utc_now_iso
from craftcut.commands.restructure import run_restructure
from craftcut.commands.trim import plan_argv, run_trim
from craftcut.config import CraftcutProjectConfig, ProjectLayout, load_project_config
from craftcut.errors import BadInputError, SourceIntegrityError
from craftcut.hashing import combined_key, file_hash
from craftcut.manifest import append_stage, find_cached_stage
from craftcut.models.manifest import StageReport
from craftcut.models.reports import RenderResult
from craftcut.probe import probe_file
from craftcut.progress import ProgressWriter
from craftcut.runners.melt import build_argv as melt_argv
from craftcut.runners.melt import run_melt


def build_dag(layout: ProjectLayout, cfg: CraftcutProjectConfig) -> dict[str, Any]:
    """Return the dependency DAG for `render --dry-run` (R23)."""
    clips = discover_clips(layout)
    polished = layout.state / "polished.mlt_xml"
    output = layout.state / "master.mp4"
    trim_nodes = [
        {
            "id": f"trim:{c.stem}",
            "stage": "trim",
            "clip": c.stem,
            "inputs": [str(c.video)],
            "outputs": [str(layout.cuts / f"{c.stem}.fcpxml")],
            "argv": plan_argv(c, layout, cfg),
        }
        for c in clips
    ]
    restructure_node = {
        "id": "restructure",
        "stage": "restructure",
        "depends_on": [n["id"] for n in trim_nodes],
        "inputs": [str(layout.cuts / f"{c.stem}.fcpxml") for c in clips]
        + [str(layout.section_map)],
        "outputs": [str(polished)],
    }
    render_node = {
        "id": "render",
        "stage": "render",
        "depends_on": ["restructure"],
        "inputs": [str(polished)],
        "outputs": [str(output)],
        "argv": melt_argv(polished, output, cfg.render, hwaccel=cfg.render.hwaccel, lenient=True),
    }
    return {
        "schema": "craftcut.render.v1",
        "status": "dry_run",
        "nodes": [*trim_nodes, restructure_node, render_node],
    }


def _cache_key(polished: Path, cfg: CraftcutProjectConfig) -> str:
    return combined_key(
        [
            "render.v1",
            file_hash(polished),
            f"{cfg.render.width}x{cfg.render.height}@{cfg.render.frame_rate}",
            f"vb={cfg.render.video_bitrate}/max={cfg.render.video_maxrate}",
            "hwaccel" if cfg.render.hwaccel else "sw",
        ]
    )


def run_render(
    layout: ProjectLayout,
    *,
    cfg: CraftcutProjectConfig | None = None,
    force: bool = False,
    dry_run: bool = False,
    no_hwaccel: bool = False,
    allow_outside_root: bool = False,
    argv: list[str] | None = None,
) -> RenderResult | dict[str, Any]:
    cfg = cfg or load_project_config(layout)
    if no_hwaccel:
        cfg = cfg.model_copy(update={"render": cfg.render.model_copy(update={"hwaccel": False})})
    if dry_run:
        return build_dag(layout, cfg)

    run_trim(layout, cfg=cfg, force=force, argv=argv)
    run_restructure(
        layout,
        cfg=cfg,
        force=force,
        allow_outside_root=allow_outside_root,
        argv=argv,
    )

    polished = layout.state / "polished.mlt_xml"
    if not polished.exists():
        raise BadInputError("polished.mlt_xml missing after restructure")

    output = layout.state / "master.mp4"
    progress = ProgressWriter(layout.progress, stage="render")
    key = _cache_key(polished, cfg)
    prior = None if force else find_cached_stage(layout, "render", key)
    started = time.monotonic()
    if prior and output.exists():
        progress.close()
        return _cached_result(output)

    progress.tick(phase="encode", pct=0.0)
    run_melt(polished, output, cfg.render, hwaccel=cfg.render.hwaccel)
    wall = time.monotonic() - started

    probe = probe_file(output)
    if probe.width != cfg.render.width or probe.height != cfg.render.height:
        raise SourceIntegrityError(
            f"render probe mismatch: {probe.width}x{probe.height} "
            f"expected {cfg.render.width}x{cfg.render.height}"
        )

    result = RenderResult(
        status="ok",
        output_path=output,
        width=probe.width,
        height=probe.height,
        frame_rate=probe.frame_rate,
        duration_seconds=probe.duration_seconds,
        file_size_bytes=output.stat().st_size,
        wall_seconds=wall,
        probe_ok=True,
    )
    append_stage(
        layout,
        StageReport(
            stage="render",
            status="ok",
            started_at=utc_now_iso(),
            finished_at=utc_now_iso(),
            wall_seconds=wall,
            cache_key=key,
            argv=argv or [],
            inputs={"polished": str(polished)},
            outputs={"master": str(output)},
            extra={
                "width": probe.width,
                "height": probe.height,
                "frame_rate": probe.frame_rate,
                "duration_seconds": probe.duration_seconds,
                "file_size_bytes": output.stat().st_size,
            },
        ),
    )
    progress.close()
    return result


def _cached_result(output: Path) -> RenderResult:
    probe = probe_file(output)
    return RenderResult(
        status="cached",
        output_path=output,
        width=probe.width,
        height=probe.height,
        frame_rate=probe.frame_rate,
        duration_seconds=probe.duration_seconds,
        file_size_bytes=output.stat().st_size,
        wall_seconds=0.0,
        probe_ok=True,
    )


__all__ = ["build_dag", "run_render"]
