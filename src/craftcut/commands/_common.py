"""Shared helpers for command orchestrators."""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

from craftcut.config import ProjectLayout
from craftcut.models.project import SourceClip
from craftcut.platform import nfc

MEDIA_EXTENSIONS = {".mov", ".mp4", ".m4v"}
SUBTITLE_EXTENSIONS = {".srt"}
CLEAN_AUDIO_EXTENSIONS = {".wav", ".flac", ".m4a"}


def utc_now_iso() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def discover_clips(layout: ProjectLayout) -> list[SourceClip]:
    """Walk `media/`, pair with `audio-clean/` + `subtitles/` by NFC-normalized stem."""
    if not layout.media.exists():
        return []
    clips: list[SourceClip] = []
    for video in sorted(layout.media.iterdir()):
        if video.suffix.lower() not in MEDIA_EXTENSIONS:
            continue
        stem = nfc(video.stem)
        clean = _find_sibling(layout.audio, stem, CLEAN_AUDIO_EXTENSIONS)
        subs = _find_sibling(layout.subtitles, stem, SUBTITLE_EXTENSIONS)
        clips.append(SourceClip(stem=stem, video=video, audio_clean=clean, subtitle=subs))
    return clips


def _find_sibling(folder: Path, stem: str, exts: set[str]) -> Path | None:
    if not folder.exists():
        return None
    for entry in folder.iterdir():
        if nfc(entry.stem) == stem and entry.suffix.lower() in exts:
            return entry
    return None


def emit_json(payload: Any) -> None:
    json.dump(payload, sys.stdout, separators=(",", ":"))
    sys.stdout.write("\n")
