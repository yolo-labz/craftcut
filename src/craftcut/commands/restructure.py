"""Section-map driven OTIO timeline surgery (T039).

Reads the per-clip trimmed FCPXMLs from `cuts/`, merges them via
OpenTimelineIO into a single portrait timeline following the section
map, emits `.craftcut/polished.mlt_xml` for melt consumption.

Real OTIO FCPXML↔mlt_xml bridge invoked only when `dry_run=False`.
OTIO plugin import is lazy so dry-run can plan without OTIO installed.
"""

from __future__ import annotations

import time
from pathlib import Path

from craftcut.commands._common import utc_now_iso
from craftcut.config import CraftcutProjectConfig, ProjectLayout, load_project_config
from craftcut.errors import BadInputError
from craftcut.hashing import combined_key, file_hash
from craftcut.manifest import append_stage, find_cached_stage
from craftcut.models.manifest import StageReport
from craftcut.models.reports import RestructureReport
from craftcut.models.sectionmap import SectionMap
from craftcut.otio_io import compose_mlt
from craftcut.progress import ProgressWriter
from craftcut.sandbox import load_section_map

CUTS_PER_MINUTE_LOW = 4.0
CUTS_PER_MINUTE_HIGH = 12.0


def _collect_trim_outputs(layout: ProjectLayout, smap: SectionMap) -> list[Path]:
    missing: list[str] = []
    paths: list[Path] = []
    for section in smap.sections:
        for seg in section.segments:
            candidate = layout.cuts / f"{seg.clip}.fcpxml"
            if not candidate.exists():
                missing.append(seg.clip)
            else:
                paths.append(candidate)
    if missing:
        raise BadInputError(f"restructure: missing trimmed FCPXML for clips {sorted(set(missing))}")
    return paths


def _cache_key(smap: SectionMap, cuts: list[Path]) -> str:
    parts = ["restructure.v1", smap.model_dump_json()]
    parts.extend(file_hash(p) for p in cuts)
    return combined_key(parts)


def run_restructure(
    layout: ProjectLayout,
    *,
    section_map: Path | None = None,
    cfg: CraftcutProjectConfig | None = None,
    force: bool = False,
    dry_run: bool = False,
    allow_outside_root: bool = False,
    argv: list[str] | None = None,
) -> RestructureReport:
    cfg = cfg or load_project_config(layout)
    smap_path = section_map or layout.section_map
    if not smap_path.exists():
        raise BadInputError(f"section-map not found at {smap_path}")
    smap = load_section_map(smap_path, layout, allow_outside_root=allow_outside_root)

    cuts = _collect_trim_outputs(layout, smap) if not dry_run else []
    polished = layout.state / "polished.mlt_xml"
    progress = ProgressWriter(layout.progress, stage="restructure")
    progress.tick(phase="prepare", pct=0.0)

    if dry_run:
        total = sum(seg.end - seg.start for s in smap.sections for seg in s.segments)
        cuts_per_minute = (len(smap.sections) * 60 / total) if total else 0.0
        return RestructureReport(
            status="ok",
            polished_fcpxml=polished,
            total_runtime_seconds=total,
            cuts_per_minute=cuts_per_minute,
            pacing_warning=not (CUTS_PER_MINUTE_LOW <= cuts_per_minute <= CUTS_PER_MINUTE_HIGH),
            moves=[f"{s.name}: {len(s.segments)} segments" for s in smap.sections],
        )

    key = _cache_key(smap, cuts)
    prior = None if force else find_cached_stage(layout, "restructure", key)
    started = time.monotonic()
    if prior and polished.exists():
        progress.close()
        return RestructureReport(
            status="cached",
            polished_fcpxml=polished,
            total_runtime_seconds=float(prior.extra.get("total_runtime_seconds", 0.0)),
            cuts_per_minute=float(prior.extra.get("cuts_per_minute", 0.0)),
            pacing_warning=bool(prior.extra.get("pacing_warning", False)),
        )

    total, cpm = _compose_timeline(cuts, smap, polished, layout, cfg)
    wall = time.monotonic() - started
    pacing_warning = not (CUTS_PER_MINUTE_LOW <= cpm <= CUTS_PER_MINUTE_HIGH)
    append_stage(
        layout,
        StageReport(
            stage="restructure",
            status="ok",
            started_at=utc_now_iso(),
            finished_at=utc_now_iso(),
            wall_seconds=wall,
            cache_key=key,
            argv=argv or [],
            inputs={p.stem: str(p) for p in cuts},
            outputs={"polished": str(polished)},
            extra={
                "total_runtime_seconds": total,
                "cuts_per_minute": cpm,
                "pacing_warning": pacing_warning,
            },
        ),
    )
    progress.close()
    return RestructureReport(
        status="ok",
        polished_fcpxml=polished,
        total_runtime_seconds=total,
        cuts_per_minute=cpm,
        pacing_warning=pacing_warning,
        moves=[f"{s.name}: {len(s.segments)} segments" for s in smap.sections],
    )


def _compose_timeline(
    cuts: list[Path],  # noqa: ARG001 — kept for cache-key parity with fan-in
    smap: SectionMap,
    polished: Path,
    layout: ProjectLayout,
    cfg: CraftcutProjectConfig,
) -> tuple[float, float]:
    return compose_mlt(layout.cuts, smap, polished, rate=cfg.render.frame_rate)


__all__ = ["run_restructure"]
