"""Source-integrity rules (R14). Pure functions — easy to unit-test."""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from craftcut.models.manifest import Finding, Warning_
from craftcut.models.project import ProbeResult

_SRT_TS = re.compile(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})")


@dataclass(frozen=True)
class ClipBundle:
    stem: str
    probe: ProbeResult
    fcpxml_duration_s: float | None = None
    fcpxml_rotation: int | None = None
    subtitle_path: Path | None = None


def duration_parity(bundle: ClipBundle) -> list[Warning_]:
    """T057 — FCPXML ↔ MOV duration within ±1 frame."""
    if bundle.fcpxml_duration_s is None:
        return []
    if bundle.probe.frame_rate <= 0:
        return [
            Warning_(
                code="VAL_DUR_FPS0",
                message="probe frame_rate is zero; cannot compute parity",
                clip=bundle.stem,
            )
        ]
    one_frame = 1.0 / bundle.probe.frame_rate
    delta = abs(bundle.probe.duration_seconds - bundle.fcpxml_duration_s)
    if delta > one_frame:
        return [
            Warning_(
                code="VAL_DUR_PARITY",
                message=(
                    f"FCPXML {bundle.fcpxml_duration_s:.4f}s vs MOV "
                    f"{bundle.probe.duration_seconds:.4f}s drift {delta:.4f}s (>1 frame)"
                ),
                clip=bundle.stem,
            )
        ]
    return []


def srt_bounds(bundle: ClipBundle) -> list[Finding]:
    """T058 — SRT end timecode must not exceed clip duration."""
    if bundle.subtitle_path is None or not bundle.subtitle_path.exists():
        return []
    text = bundle.subtitle_path.read_text(encoding="utf-8", errors="replace")
    max_end_s = 0.0
    for line in text.splitlines():
        match = _SRT_TS.findall(line)
        if len(match) == 2:
            end = match[1]
            end_s = int(end[0]) * 3600 + int(end[1]) * 60 + int(end[2]) + int(end[3]) / 1000.0
            max_end_s = max(max_end_s, end_s)
    if max_end_s > bundle.probe.duration_seconds + 0.001:
        return [
            Finding(
                code="VAL_SRT_OVERRUN",
                message=(
                    f"SRT ends at {max_end_s:.3f}s but clip is {bundle.probe.duration_seconds:.3f}s"
                ),
                clip=bundle.stem,
                remedy=f"trim subtitles to ≤ {bundle.probe.duration_seconds:.3f}s",
            )
        ]
    return []


def rotation_consistency(bundle: ClipBundle) -> list[Warning_]:
    """T059 — rotation metadata consistent between MOV and FCPXML."""
    if bundle.fcpxml_rotation is None:
        return []
    if (bundle.probe.rotation % 360) != (bundle.fcpxml_rotation % 360):
        return [
            Warning_(
                code="VAL_ROTATION_DRIFT",
                message=(
                    f"MOV rotation={bundle.probe.rotation}° vs "
                    f"FCPXML rotation={bundle.fcpxml_rotation}°"
                ),
                clip=bundle.stem,
            )
        ]
    return []


def disk_budget(media_root: Path, multiplier: float) -> list[Finding]:
    """T060 — require free space ≥ multiplier × media bytes."""
    if not media_root.exists():
        return []
    media_bytes = sum(p.stat().st_size for p in media_root.rglob("*") if p.is_file())
    required = int(media_bytes * multiplier)
    usage = shutil.disk_usage(media_root)
    if usage.free < required:
        gb_free = usage.free / 1e9
        gb_req = required / 1e9
        return [
            Finding(
                code="VAL_DISK_BUDGET",
                message=f"free {gb_free:.1f}GB < required {gb_req:.1f}GB (x{multiplier})",
                clip=None,
                remedy="free disk space or lower disk_budget_multiplier in config",
            )
        ]
    return []


def promote_warnings(warnings: list[Warning_]) -> list[Finding]:
    """T061 — `--strict` converts warnings into findings."""
    remedy = "strict mode: treated as finding"
    return [Finding(code=w.code, message=w.message, clip=w.clip, remedy=remedy) for w in warnings]


__all__ = [
    "ClipBundle",
    "disk_budget",
    "duration_parity",
    "promote_warnings",
    "rotation_consistency",
    "srt_bounds",
]
