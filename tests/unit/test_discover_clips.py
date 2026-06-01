"""Clip discovery: pair video/audio/subtitle by NFC stem."""

from __future__ import annotations

from pathlib import Path

from craftcut.commands._common import discover_clips
from craftcut.config import ProjectLayout


def test_discover_clips_pairs_by_stem(micro_project: Path) -> None:
    (micro_project / "media" / "clip01.mov").write_bytes(b"")
    (micro_project / "media" / "clip02.mp4").write_bytes(b"")
    (micro_project / "audio-clean" / "clip01.wav").write_bytes(b"")
    (micro_project / "subtitles" / "clip02.srt").write_bytes(b"")

    layout = ProjectLayout.for_project(micro_project)
    clips = discover_clips(layout)
    assert [c.stem for c in clips] == ["clip01", "clip02"]
    assert clips[0].audio_clean is not None
    assert clips[0].subtitle is None
    assert clips[1].audio_clean is None
    assert clips[1].subtitle is not None


def test_discover_clips_nfc_normalizes_stem(micro_project: Path) -> None:
    nfd_name = "bolsa\u0303.mov"
    (micro_project / "media" / nfd_name).write_bytes(b"")
    layout = ProjectLayout.for_project(micro_project)
    clips = discover_clips(layout)
    assert len(clips) == 1
    assert "\u0303" not in clips[0].stem
