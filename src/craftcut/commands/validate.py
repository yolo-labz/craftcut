"""T056 — `craftcut validate` orchestrator. Aggregates R14 rules into a ValidateReport."""

from __future__ import annotations

import re
from pathlib import Path
from xml.etree import ElementTree as ET

from craftcut.commands._common import discover_clips, utc_now_iso
from craftcut.config import CraftcutProjectConfig, ProjectLayout, load_project_config
from craftcut.errors import ExternalToolError
from craftcut.manifest import append_stage
from craftcut.models.manifest import Finding, StageReport, Warning_
from craftcut.models.project import ProbeResult, SourceClip
from craftcut.models.reports import ValidateReport
from craftcut.probe import probe_file
from craftcut.progress import ProgressWriter
from craftcut.validators import (
    ClipBundle,
    disk_budget,
    duration_parity,
    promote_warnings,
    rotation_consistency,
    srt_bounds,
)

_ROTATION_FCP = re.compile(r"rotation=\"(-?\d+(?:\.\d+)?)\"")


def _parse_fcpxml(path: Path) -> tuple[float | None, int | None]:
    """Best-effort FCPXML duration (s) + rotation (°). Returns (None, None) on fail."""
    if not path.exists():
        return None, None
    try:
        tree = ET.parse(path)  # noqa: S314 — local trusted fcpxml
    except ET.ParseError:
        return None, None
    root = tree.getroot()
    duration_s: float | None = None
    for clip in root.iter():
        dur = clip.get("duration")
        if dur and "/" in dur and dur.endswith("s"):
            num, denom = dur[:-1].split("/", 1)
            try:
                duration_s = float(num) / float(denom)
            except (ValueError, ZeroDivisionError):
                duration_s = None
            if duration_s is not None:
                break
    rotation_match = _ROTATION_FCP.search(path.read_text(encoding="utf-8", errors="replace"))
    rotation = int(float(rotation_match.group(1))) if rotation_match else None
    return duration_s, rotation


def _bundle(clip: SourceClip, layout: ProjectLayout) -> ClipBundle | None:
    try:
        probe: ProbeResult = probe_file(clip.video)
    except ExternalToolError:
        return None
    fcpxml_path = layout.cuts / f"{clip.stem}.fcpxml"
    dur, rot = _parse_fcpxml(fcpxml_path)
    return ClipBundle(
        stem=clip.stem,
        probe=probe,
        fcpxml_duration_s=dur,
        fcpxml_rotation=rot,
        subtitle_path=clip.subtitle,
    )


def run_validate(
    layout: ProjectLayout,
    *,
    cfg: CraftcutProjectConfig | None = None,
    strict: bool = False,
    dry_run: bool = False,
    argv: list[str] | None = None,
) -> ValidateReport:
    cfg = cfg or load_project_config(layout)
    clips = discover_clips(layout)
    progress = ProgressWriter(layout.progress, stage="validate")
    progress.tick(phase="prepare", pct=0.0, total=float(len(clips) or 1))

    if dry_run:
        progress.close()
        return ValidateReport(status="ok", clip_count=len(clips))

    warnings: list[Warning_] = []
    findings: list[Finding] = []
    unreadable: list[str] = []

    for clip in clips:
        bundle = _bundle(clip, layout)
        if bundle is None:
            unreadable.append(clip.stem)
            findings.append(
                Finding(
                    code="VAL_UNREADABLE",
                    message=f"ffprobe could not read {clip.video.name}",
                    clip=clip.stem,
                    remedy="reinstall ffmpeg or re-export the source clip",
                )
            )
            continue
        warnings.extend(duration_parity(bundle))
        warnings.extend(rotation_consistency(bundle))
        findings.extend(srt_bounds(bundle))

    findings.extend(disk_budget(layout.media, cfg.validate_.disk_budget_multiplier))

    if strict or cfg.validate_.strict:
        findings.extend(promote_warnings(warnings))
        warnings = []

    status = "failed" if findings else "ok"
    report = ValidateReport(
        status=status,
        clip_count=len(clips),
        warnings=warnings,
        findings=findings,
    )
    append_stage(
        layout,
        StageReport(
            stage="validate",
            status=status,
            started_at=utc_now_iso(),
            finished_at=utc_now_iso(),
            wall_seconds=0.0,
            argv=argv or [],
            inputs={c.stem: str(c.video) for c in clips},
            outputs={},
            warnings=warnings,
            findings=findings,
            extra={"unreadable": unreadable, "strict": strict or cfg.validate_.strict},
        ),
    )
    progress.close()
    return report


__all__ = ["run_validate"]
