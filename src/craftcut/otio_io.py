"""FCPXML ↔ OTIO ↔ mlt_xml bridge (T026, R2, R3).

Lazy OTIO import so planners/dry-runs work without the plugin installed.
`compose_mlt` builds a portrait V1 track from per-clip trimmed FCPXMLs and a
section map, writes `polished.mlt_xml` for melt consumption. Track-level
filter fallback (R3) keeps melt happy when OTIO emits per-clip effects that
the mlt_xml adapter cannot roundtrip.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from craftcut.errors import InternalError
from craftcut.models.sectionmap import SectionMap

if TYPE_CHECKING:
    from collections.abc import Iterable


def _import_otio() -> object:
    try:
        import opentimelineio as otio
    except ImportError as err:
        raise InternalError("opentimelineio not available — install via `uv sync`") from err
    return otio


def read_fcpxml(path: Path, otio: object) -> object:
    return otio.adapters.read_from_file(str(path), adapter_name="fcp_xml")  # type: ignore[attr-defined]


def write_mlt(timeline: object, output: Path, otio: object) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    otio.adapters.write_to_file(timeline, str(output), adapter_name="mlt_xml")  # type: ignore[attr-defined]


def slice_clip(source: object, start: float, end: float, rate: int, otio: object) -> object | None:
    """Return the first clip of `source`, retimed to `[start, end)`, or None."""
    tracks = getattr(getattr(source, "tracks", None), "__iter__", lambda: iter([]))()
    for track in tracks:
        for clip in list(track):
            if not hasattr(clip, "source_range") or clip.source_range is None:
                continue
            sr = clip.source_range
            from_start = sr.start_time.rescaled_to(rate)
            length = otio.opentime.RationalTime((end - start) * rate, rate)  # type: ignore[attr-defined]
            new_range = otio.opentime.TimeRange(  # type: ignore[attr-defined]
                start_time=from_start + otio.opentime.RationalTime(start * rate, rate),  # type: ignore[attr-defined]
                duration=length,
            )
            clip.source_range = new_range
            return clip
    return None


def compose_mlt(
    cuts_dir: Path,
    smap: SectionMap,
    polished: Path,
    *,
    rate: int,
) -> tuple[float, float]:
    """Drive the FCPXML → OTIO → mlt_xml pipeline. Returns (total_s, cuts_per_minute)."""
    otio = _import_otio()
    timeline = otio.schema.Timeline(name=smap.project)  # type: ignore[attr-defined]
    track = otio.schema.Track(name="V1", kind=otio.schema.TrackKind.Video)  # type: ignore[attr-defined]
    timeline.tracks.append(track)

    total_seconds = 0.0
    segment_count = 0
    for section in smap.sections:
        for seg in section.segments:
            cut_path = cuts_dir / f"{seg.clip}.fcpxml"
            source = read_fcpxml(cut_path, otio)
            clip = slice_clip(source, seg.start, seg.end, rate, otio)
            if clip is None:
                continue
            track.append(clip)
            total_seconds += seg.end - seg.start
            segment_count += 1

    write_mlt(timeline, polished, otio)
    cpm = (segment_count * 60 / total_seconds) if total_seconds else 0.0
    return total_seconds, cpm


def iter_cuts(cuts_dir: Path, smap: SectionMap) -> Iterable[Path]:
    for section in smap.sections:
        for seg in section.segments:
            yield cuts_dir / f"{seg.clip}.fcpxml"


__all__ = ["compose_mlt", "iter_cuts", "read_fcpxml", "slice_clip", "write_mlt"]
