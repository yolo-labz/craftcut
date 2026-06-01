"""T034a — NFR-PORT-01: clip-stem matching on case-sensitive APFS + default FS.

Mounts a case-sensitive APFS DMG via `hdiutil` on macOS. Skips on non-Darwin.
Integration-marked because DMG create/attach takes ~5 s.
"""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from craftcut.commands._common import discover_clips
from craftcut.config import ProjectLayout

pytestmark = pytest.mark.integration


@pytest.fixture
def case_sensitive_apfs(tmp_path: Path) -> Iterator[Path]:
    """Yield a case-sensitive APFS mount point; tear down on exit (macOS only)."""
    if sys.platform != "darwin":
        pytest.skip("case-sensitive APFS test is macOS-only")

    dmg = tmp_path / "case.dmg"
    mount = tmp_path / "mount"
    mount.mkdir()
    subprocess.run(
        [
            "/usr/bin/hdiutil",
            "create",
            "-size",
            "16m",
            "-fs",
            "Case-sensitive APFS",
            "-volname",
            "craftcut-cs",
            str(dmg),
        ],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["/usr/bin/hdiutil", "attach", str(dmg), "-mountpoint", str(mount), "-nobrowse"],
        check=True,
        capture_output=True,
    )
    try:
        yield mount
    finally:
        subprocess.run(
            ["/usr/bin/hdiutil", "detach", str(mount), "-force"],
            check=False,
            capture_output=True,
        )


def _project_with_clip(root: Path, stem: str) -> ProjectLayout:
    for sub in ("media", "audio-clean", "subtitles", "cuts"):
        (root / sub).mkdir(exist_ok=True)
    (root / "media" / f"{stem}.mov").write_bytes(b"stub")
    (root / "audio-clean" / f"{stem}.wav").write_bytes(b"stub")
    (root / "subtitles" / f"{stem}.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\nhi\n")
    return ProjectLayout.for_project(root)


def test_stem_pairing_on_case_sensitive_apfs(case_sensitive_apfs: Path) -> None:
    layout = _project_with_clip(case_sensitive_apfs, "clip01")
    clips = discover_clips(layout)
    assert len(clips) == 1
    assert clips[0].stem == "clip01"
    assert clips[0].audio_clean is not None
    assert clips[0].subtitle is not None


def test_stem_pairing_on_default_tmp_fs(tmp_path: Path) -> None:
    layout = _project_with_clip(tmp_path, "clip01")
    clips = discover_clips(layout)
    assert len(clips) == 1
    assert clips[0].stem == "clip01"
    assert clips[0].audio_clean is not None
    assert clips[0].subtitle is not None


def test_case_sensitive_distinguishes_stems(case_sensitive_apfs: Path) -> None:
    """On case-sensitive FS, `Clip01.mov` and `clip01.mov` coexist as distinct files."""
    layout = _project_with_clip(case_sensitive_apfs, "clip01")
    (layout.media / "Clip01.mov").write_bytes(b"stub")
    (layout.audio / "Clip01.wav").write_bytes(b"stub")
    clips = discover_clips(layout)
    stems = sorted(c.stem for c in clips)
    assert stems == ["Clip01", "clip01"]
