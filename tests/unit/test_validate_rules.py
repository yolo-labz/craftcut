"""T055 — each R14 rule unit-tested in isolation."""

from __future__ import annotations

from pathlib import Path

from craftcut.models.manifest import Warning_
from craftcut.models.project import ProbeResult
from craftcut.validators import (
    ClipBundle,
    disk_budget,
    duration_parity,
    promote_warnings,
    rotation_consistency,
    srt_bounds,
)


def _probe(duration: float = 10.0, rotation: int = 0, fps: float = 30.0) -> ProbeResult:
    return ProbeResult(
        path=Path("/dev/null"),
        width=1920,
        height=1080,
        rotation=rotation,
        frame_rate=fps,
        duration_seconds=duration,
        codec="h264",
    )


def test_duration_parity_within_one_frame_is_clean() -> None:
    bundle = ClipBundle(stem="c", probe=_probe(10.0, fps=30.0), fcpxml_duration_s=10.02)
    assert duration_parity(bundle) == []


def test_duration_parity_drift_warns() -> None:
    bundle = ClipBundle(stem="c", probe=_probe(10.0, fps=30.0), fcpxml_duration_s=10.5)
    warns = duration_parity(bundle)
    assert len(warns) == 1
    assert warns[0].code == "VAL_DUR_PARITY"


def test_srt_overrun_is_finding(tmp_path: Path) -> None:
    srt = tmp_path / "c.srt"
    srt.write_text("1\n00:00:00,000 --> 00:00:20,000\nhello\n", encoding="utf-8")
    bundle = ClipBundle(stem="c", probe=_probe(10.0), subtitle_path=srt)
    findings = srt_bounds(bundle)
    assert len(findings) == 1
    assert findings[0].code == "VAL_SRT_OVERRUN"


def test_srt_within_bounds_clean(tmp_path: Path) -> None:
    srt = tmp_path / "c.srt"
    srt.write_text("1\n00:00:00,000 --> 00:00:05,000\nok\n", encoding="utf-8")
    bundle = ClipBundle(stem="c", probe=_probe(10.0), subtitle_path=srt)
    assert srt_bounds(bundle) == []


def test_rotation_consistency_match() -> None:
    bundle = ClipBundle(stem="c", probe=_probe(rotation=90), fcpxml_rotation=90)
    assert rotation_consistency(bundle) == []


def test_rotation_consistency_drift() -> None:
    bundle = ClipBundle(stem="c", probe=_probe(rotation=0), fcpxml_rotation=90)
    warns = rotation_consistency(bundle)
    assert len(warns) == 1
    assert warns[0].code == "VAL_ROTATION_DRIFT"


def test_disk_budget_sufficient(tmp_path: Path) -> None:
    (tmp_path / "a.mov").write_bytes(b"x" * 1024)
    assert disk_budget(tmp_path, multiplier=1.0) == []


def test_disk_budget_insufficient(tmp_path: Path) -> None:
    (tmp_path / "a.mov").write_bytes(b"x" * 1024)
    findings = disk_budget(tmp_path, multiplier=10**18)
    assert len(findings) == 1
    assert findings[0].code == "VAL_DISK_BUDGET"


def test_promote_warnings_converts_to_findings() -> None:
    w = [Warning_(code="VAL_X", message="m", clip="c")]
    findings = promote_warnings(w)
    assert len(findings) == 1
    assert findings[0].code == "VAL_X"
    assert findings[0].remedy is not None
