"""T047 — SIGINT mid-render leaves stale `.tmp`+`.lock`; next run resumes cleanly.

We simulate a crashed render by leaving an orphan `.progress-*.tmp` and a stale
advisory lock in `.craftcut/`, then verify the next dry-run still succeeds
without mutating the orphan tempfile (crash-recovery R19 contract).
"""

from __future__ import annotations

import time
from pathlib import Path

from craftcut.commands.trim import run_trim
from craftcut.config import ProjectLayout
from craftcut.manifest import STALE_LOCK_AGE_SECONDS, manifest_lock


def test_orphan_tmp_does_not_block_next_run(micro_project: Path) -> None:
    (micro_project / "media" / "clip01.mov").write_bytes(b"stub")
    layout = ProjectLayout.for_project(micro_project)
    layout.state.mkdir(parents=True, exist_ok=True)
    orphan = layout.state / ".progress-deadbeef.tmp"
    orphan.write_text("{}", encoding="utf-8")

    result = run_trim(layout, dry_run=True)
    assert result.status == "ok"
    assert orphan.exists(), "orphan .tmp should remain for operator audit"


def test_stale_lock_auto_broken(micro_project: Path) -> None:
    layout = ProjectLayout.for_project(micro_project)
    layout.state.mkdir(parents=True, exist_ok=True)
    stale = layout.state / "manifest.lock"
    stale.write_text("", encoding="utf-8")
    aged = time.time() - (STALE_LOCK_AGE_SECONDS + 60)
    import os

    os.utime(stale, (aged, aged))
    with manifest_lock(layout, timeout=1.0):
        pass
