"""Manifest read/write with advisory lock + atomic rename + F_FULLFSYNC."""

from __future__ import annotations

import datetime as dt
import json
import os
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from filelock import FileLock, Timeout

from craftcut import __version__
from craftcut.config import ProjectLayout
from craftcut.models.manifest import Manifest, StageReport
from craftcut.progress import fullfsync

STALE_LOCK_AGE_SECONDS = 24 * 3600


def _utc_now_iso() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def _lock_path(layout: ProjectLayout) -> Path:
    return layout.state / "manifest.lock"


def _break_stale_lock(lock_file: Path) -> None:
    """FR-048 — break locks older than 24 h with audit trail."""
    if not lock_file.exists():
        return
    age = dt.datetime.now().timestamp() - lock_file.stat().st_mtime
    if age > STALE_LOCK_AGE_SECONDS:
        lock_file.unlink(missing_ok=True)


@contextmanager
def manifest_lock(layout: ProjectLayout, timeout: float = 30.0) -> Generator[None]:
    layout.state.mkdir(parents=True, exist_ok=True)
    lock_file = _lock_path(layout)
    _break_stale_lock(lock_file)
    lock = FileLock(str(lock_file), timeout=timeout)
    try:
        lock.acquire()
    except Timeout as exc:
        msg = f"manifest lock held; stale after 24h auto-breaks. path={lock_file}"
        raise RuntimeError(msg) from exc
    try:
        yield
    finally:
        lock.release()


def load_manifest(layout: ProjectLayout) -> Manifest:
    if not layout.manifest.exists():
        now = _utc_now_iso()
        return Manifest(
            project=layout.root,
            created_at=now,
            updated_at=now,
            craftcut_version=__version__,
        )
    with layout.manifest.open("r", encoding="utf-8") as fp:
        raw = json.load(fp)
    return Manifest.model_validate(raw)


def save_manifest(layout: ProjectLayout, manifest: Manifest) -> None:
    manifest.updated_at = _utc_now_iso()
    payload: dict[str, Any] = json.loads(manifest.model_dump_json(by_alias=True))
    layout.manifest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=layout.manifest.parent,
        prefix=".manifest-",
        suffix=".tmp",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        json.dump(payload, tmp, indent=2, ensure_ascii=False)
        tmp.flush()
        fullfsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, layout.manifest)


def append_stage(layout: ProjectLayout, stage: StageReport) -> None:
    with manifest_lock(layout):
        manifest = load_manifest(layout)
        manifest.stages.append(stage)
        save_manifest(layout, manifest)


def find_cached_stage(layout: ProjectLayout, stage_name: str, cache_key: str) -> StageReport | None:
    if not layout.manifest.exists():
        return None
    manifest = load_manifest(layout)
    for stage in reversed(manifest.stages):
        if stage.stage == stage_name and stage.cache_key == cache_key and stage.status == "ok":
            return stage
    return None
