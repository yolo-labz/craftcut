"""T064 — `craftcut derive` orchestrator. Landscape pillarbox or shorts cutdowns.

Modes:
  - `landscape`: 1920×1080 blurred pillarbox via ffmpeg filter_complex (T065).
  - `shorts N`: splits master.mp4 into N segments of ≤ 180 s based on section-map
    cut points; subtitle re-timing is best-effort per segment (T066).
"""

from __future__ import annotations

import time
from pathlib import Path

from craftcut.commands._common import utc_now_iso
from craftcut.config import CraftcutProjectConfig, ProjectLayout, load_project_config
from craftcut.errors import BadInputError
from craftcut.manifest import append_stage
from craftcut.models.manifest import StageReport
from craftcut.models.reports import DeriveResult
from craftcut.progress import ProgressWriter
from craftcut.runners.ffmpeg import landscape_argv, run_argv, short_argv
from craftcut.sandbox import load_section_map

SHORTS_MAX_SECONDS = 180.0


def _master(layout: ProjectLayout) -> Path:
    return layout.state / "master.mp4"


def _derived_dir(layout: ProjectLayout) -> Path:
    out = layout.root / "derivatives"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _plan_shorts(
    layout: ProjectLayout,
    count: int,
    *,
    allow_outside_root: bool,
) -> list[tuple[float, float]]:
    """Return list of (start_s, duration_s) slices, each ≤ SHORTS_MAX_SECONDS."""
    smap = load_section_map(layout.section_map, layout, allow_outside_root=allow_outside_root)
    section_durations: list[tuple[float, float]] = []
    cursor = 0.0
    for section in smap.sections:
        seg_seconds = sum(seg.end - seg.start for seg in section.segments)
        section_durations.append((cursor, min(seg_seconds, SHORTS_MAX_SECONDS)))
        cursor += seg_seconds
    return section_durations[:count] if count <= len(section_durations) else section_durations


def run_derive(
    layout: ProjectLayout,
    *,
    cfg: CraftcutProjectConfig | None = None,
    landscape: bool = False,
    shorts: int | None = None,
    force: bool = False,
    dry_run: bool = False,
    no_hwaccel: bool = False,
    allow_outside_root: bool = False,
    argv: list[str] | None = None,
) -> DeriveResult:
    _ = force  # derive always re-encodes; cache is intentionally not wired (R25)
    cfg = cfg or load_project_config(layout)
    hwaccel = cfg.render.hwaccel and not no_hwaccel

    if landscape == bool(shorts):
        raise BadInputError("derive: pick exactly one of --landscape or --shorts N")

    master = _master(layout)
    if not dry_run and not master.exists():
        raise BadInputError(f"master render missing at {master}; run `craftcut render` first")

    progress = ProgressWriter(layout.progress, stage="derive")
    progress.tick(phase="prepare", pct=0.0)
    started = time.monotonic()

    if landscape:
        outputs = [_derived_dir(layout) / "landscape.mp4"]
        argv_plan = [landscape_argv(master, outputs[0], hwaccel=hwaccel, lenient=dry_run)]
        mode: str = "landscape"
    else:
        assert shorts is not None
        slices = _plan_shorts(layout, shorts, allow_outside_root=allow_outside_root)
        outputs = [_derived_dir(layout) / f"short_{i:02d}.mp4" for i in range(len(slices))]
        argv_plan = [
            short_argv(
                master,
                outputs[i],
                start_seconds=start,
                duration_seconds=dur,
                hwaccel=hwaccel,
                lenient=dry_run,
            )
            for i, (start, dur) in enumerate(slices)
        ]
        mode = "shorts"

    if dry_run:
        progress.close()
        return DeriveResult(status="ok", mode=mode, outputs=outputs)  # type: ignore[arg-type]

    for i, plan in enumerate(argv_plan):
        progress.tick(phase="encode", pct=100.0 * i / max(len(argv_plan), 1))
        run_argv(plan)
    progress.tick(phase="mux", pct=100.0)

    wall = time.monotonic() - started
    append_stage(
        layout,
        StageReport(
            stage="derive",
            status="ok",
            started_at=utc_now_iso(),
            finished_at=utc_now_iso(),
            wall_seconds=wall,
            argv=argv or [],
            inputs={"master": str(master)},
            outputs={p.stem: str(p) for p in outputs},
            extra={"mode": mode},
        ),
    )
    progress.close()
    return DeriveResult(status="ok", mode=mode, outputs=outputs)  # type: ignore[arg-type]


__all__ = ["run_derive"]
