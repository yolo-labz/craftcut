"""T034 — manifest load/save/append/find_cached round-trip."""

from __future__ import annotations

from pathlib import Path

from craftcut.config import ProjectLayout
from craftcut.manifest import (
    append_stage,
    find_cached_stage,
    load_manifest,
    save_manifest,
)
from craftcut.models.manifest import StageName, StageReport, Status


def _layout(tmp_path: Path) -> ProjectLayout:
    for sub in ("media", "audio-clean", "subtitles", "cuts"):
        (tmp_path / sub).mkdir()
    return ProjectLayout.for_project(tmp_path)


def _stage(name: StageName = "trim", key: str = "k1", status: Status = "ok") -> StageReport:
    return StageReport(
        stage=name,
        status=status,
        started_at="2026-04-17T00:00:00Z",
        finished_at="2026-04-17T00:00:01Z",
        wall_seconds=1.0,
        cache_key=key,
        argv=[],
        inputs={},
        outputs={},
    )


def test_load_returns_empty_manifest_when_absent(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    manifest = load_manifest(layout)
    assert manifest.stages == []
    assert manifest.project == layout.root


def test_save_load_roundtrip(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    manifest = load_manifest(layout)
    manifest.stages.append(_stage())
    save_manifest(layout, manifest)

    reloaded = load_manifest(layout)
    assert len(reloaded.stages) == 1
    assert reloaded.stages[0].cache_key == "k1"
    assert reloaded.updated_at >= manifest.created_at


def test_append_stage_accumulates(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    append_stage(layout, _stage(key="k1"))
    append_stage(layout, _stage(key="k2"))
    manifest = load_manifest(layout)
    assert [s.cache_key for s in manifest.stages] == ["k1", "k2"]


def test_find_cached_stage_matches_ok_only(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    append_stage(layout, _stage(key="k1", status="failed"))
    append_stage(layout, _stage(key="k1", status="ok"))

    hit = find_cached_stage(layout, "trim", "k1")
    assert hit is not None
    assert hit.status == "ok"

    miss = find_cached_stage(layout, "trim", "nope")
    assert miss is None


def test_find_cached_stage_returns_most_recent(tmp_path: Path) -> None:
    layout = _layout(tmp_path)
    append_stage(layout, _stage(key="k1"))
    append_stage(layout, _stage(key="k1"))
    manifest = load_manifest(layout)
    assert len(manifest.stages) == 2

    hit = find_cached_stage(layout, "trim", "k1")
    assert hit == manifest.stages[-1]
