"""T063 — derive --shorts N dry-run splits master into ≤180s slices per section."""

from __future__ import annotations

from pathlib import Path

import pytest

from craftcut.commands.derive import SHORTS_MAX_SECONDS, run_derive
from craftcut.config import ProjectLayout
from craftcut.errors import BadInputError


def _multi_section(path: Path) -> None:
    (path / "section-map.yaml").write_text(
        "schema_version: 1\nproject: shorts-fixture\nsections:\n"
        "  - name: intro\n    segments:\n"
        "      - { clip: clip01, start: 0, end: 30 }\n"
        "  - name: body\n    segments:\n"
        "      - { clip: clip01, start: 0, end: 400 }\n"
        "  - name: outro\n    segments:\n"
        "      - { clip: clip01, start: 0, end: 20 }\n",
        encoding="utf-8",
    )


def test_shorts_dryrun_plans_n_outputs(micro_project: Path) -> None:
    _multi_section(micro_project)
    (micro_project / ".craftcut").mkdir(exist_ok=True)
    (micro_project / ".craftcut" / "master.mp4").write_bytes(b"stub")
    layout = ProjectLayout.for_project(micro_project)
    result = run_derive(layout, shorts=2, dry_run=True)
    assert result.status == "ok"
    assert result.mode == "shorts"
    assert len(result.outputs) == 2
    assert result.outputs[0].name == "short_00.mp4"
    assert result.outputs[1].name == "short_01.mp4"


def test_shorts_caps_duration_at_180s(micro_project: Path) -> None:
    _multi_section(micro_project)
    (micro_project / ".craftcut").mkdir(exist_ok=True)
    (micro_project / ".craftcut" / "master.mp4").write_bytes(b"stub")
    layout = ProjectLayout.for_project(micro_project)
    from craftcut.commands import derive as dmod

    slices = dmod._plan_shorts(layout, 3, allow_outside_root=False)  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    for _start, dur in slices:
        assert dur <= SHORTS_MAX_SECONDS


def test_derive_rejects_both_modes(micro_project: Path) -> None:
    (micro_project / ".craftcut").mkdir(exist_ok=True)
    (micro_project / ".craftcut" / "master.mp4").write_bytes(b"stub")
    layout = ProjectLayout.for_project(micro_project)
    with pytest.raises(BadInputError, match="exactly one"):
        run_derive(layout, landscape=True, shorts=2, dry_run=True)
