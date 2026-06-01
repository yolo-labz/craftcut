"""Per-clip silence trim via auto-editor (T038).

Fan-out heuristic (NFR-PERF-03): jobs = cfg.trim.jobs if set else
min(cpu_count//2, clip_count). We cap at cpu_count//2 to leave headroom
for the thermal envelope on M-series laptops.
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from craftcut.commands._common import discover_clips, utc_now_iso
from craftcut.config import CraftcutProjectConfig, ProjectLayout, load_project_config
from craftcut.errors import BadInputError
from craftcut.hashing import combined_key, file_hash
from craftcut.manifest import append_stage, find_cached_stage
from craftcut.models.manifest import StageReport
from craftcut.models.project import SourceClip
from craftcut.models.reports import TrimClip, TrimResult
from craftcut.progress import ProgressWriter
from craftcut.runners.autoeditor import build_argv, trim_clip


def _jobs(cfg: CraftcutProjectConfig, clip_count: int) -> int:
    if cfg.trim.jobs is not None:
        return cfg.trim.jobs
    cores = os.cpu_count() or 4
    return max(1, min(cores // 2, clip_count))


def _cache_key(clip: SourceClip, cfg: CraftcutProjectConfig) -> str:
    return combined_key(
        [
            "trim.v1",
            file_hash(clip.video),
            f"{cfg.trim.threshold_pct:.4f}",
            f"{cfg.trim.margin_seconds:.4f}",
        ]
    )


def run_trim(
    layout: ProjectLayout,
    *,
    cfg: CraftcutProjectConfig | None = None,
    force: bool = False,
    dry_run: bool = False,
    argv: list[str] | None = None,
) -> TrimResult:
    cfg = cfg or load_project_config(layout)
    clips = discover_clips(layout)
    if not clips:
        raise BadInputError(f"no media found under {layout.media}")

    layout.cuts.mkdir(parents=True, exist_ok=True)
    progress = ProgressWriter(layout.progress, stage="trim")
    progress.tick(phase="prepare", pct=0.0, total=float(len(clips)))

    if dry_run:
        plan = [
            TrimClip(
                clip=c.stem,
                input_duration=0.0,
                output_duration=0.0,
                removed_seconds=0.0,
                fcpxml_path=layout.cuts / f"{c.stem}.fcpxml",
            )
            for c in clips
        ]
        return TrimResult(status="ok", clips=plan, total_removed=0.0)

    started = time.monotonic()
    cached: list[TrimClip] = []
    todo: list[SourceClip] = []
    for clip in clips:
        key = _cache_key(clip, cfg)
        prior = None if force else find_cached_stage(layout, "trim", key)
        if prior:
            cached.append(
                TrimClip(
                    clip=clip.stem,
                    input_duration=0.0,
                    output_duration=0.0,
                    removed_seconds=0.0,
                    fcpxml_path=layout.cuts / f"{clip.stem}.fcpxml",
                )
            )
        else:
            todo.append(clip)

    results: list[TrimClip] = list(cached)
    jobs = _jobs(cfg, len(todo))
    if todo:
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            futures = {pool.submit(_run_one, clip, layout, cfg): clip for clip in todo}
            for idx, fut in enumerate(as_completed(futures), 1):
                clip = futures[fut]
                tc = fut.result()
                results.append(tc)
                progress.tick(
                    phase="encode",
                    pct=100.0 * idx / len(todo),
                    current=float(idx),
                    total=float(len(todo)),
                )

    results.sort(key=lambda r: r.clip)
    wall = time.monotonic() - started
    stage_cache_key = combined_key(sorted(_cache_key(c, cfg) for c in clips))
    status = "cached" if not todo and cached else "ok"
    append_stage(
        layout,
        StageReport(
            stage="trim",
            status=status,
            started_at=utc_now_iso(),
            finished_at=utc_now_iso(),
            wall_seconds=wall,
            cache_key=stage_cache_key,
            argv=argv or [],
            inputs={c.stem: str(c.video) for c in clips},
            outputs={c.stem: str(layout.cuts / f"{c.stem}.fcpxml") for c in clips},
        ),
    )
    progress.close()
    return TrimResult(status=status, clips=results, total_removed=0.0)


def _run_one(clip: SourceClip, layout: ProjectLayout, cfg: CraftcutProjectConfig) -> TrimClip:
    output = layout.cuts / f"{clip.stem}.fcpxml"
    trim_clip(
        clip.video,
        output,
        threshold_pct=cfg.trim.threshold_pct,
        margin_seconds=cfg.trim.margin_seconds,
    )
    return TrimClip(
        clip=clip.stem,
        input_duration=0.0,
        output_duration=0.0,
        removed_seconds=0.0,
        fcpxml_path=output,
    )


def plan_argv(clip: SourceClip, layout: ProjectLayout, cfg: CraftcutProjectConfig) -> list[str]:
    """Expose the argv builder for --dry-run DAG emission."""
    return build_argv(
        clip.video,
        layout.cuts / f"{clip.stem}.fcpxml",
        threshold_pct=cfg.trim.threshold_pct,
        margin_seconds=cfg.trim.margin_seconds,
        lenient=True,
    )


__all__ = ["plan_argv", "run_trim"]
_ = Path  # keep import warm for type annotations
