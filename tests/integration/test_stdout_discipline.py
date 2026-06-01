"""T052 — structured summary only on stdout; progress lives in progress.json + stderr."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from craftcut.cli import app

runner = CliRunner()


def test_stdout_is_single_json_object(micro_project: Path) -> None:
    (micro_project / "media" / "clip01.mov").write_bytes(b"stub")
    res = runner.invoke(
        app,
        ["--json", "trim", "--project", str(micro_project), "--dry-run"],
    )
    assert res.exit_code == 0, res.output
    stripped = res.stdout.strip()
    assert stripped.count("\n") == 0, "stdout must be single-line JSON"
    payload = json.loads(stripped)
    assert payload["schema_version"] == 1


def test_progress_file_written_by_run(micro_project: Path) -> None:
    (micro_project / "media" / "clip01.mov").write_bytes(b"stub")
    res = runner.invoke(app, ["trim", "--project", str(micro_project), "--dry-run"])
    assert res.exit_code == 0
    progress = micro_project / ".craftcut" / "progress.json"
    assert progress.exists()
    tick = json.loads(progress.read_text())
    assert tick["schema"] == "craftcut.progress.v1"
    assert tick["stage"] == "trim"
