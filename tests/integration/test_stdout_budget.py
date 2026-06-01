"""T046 — each --json payload ≤ 2 KB; pipeline total ≤ 6 KB (SC-005, FR-038)."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from craftcut.cli import app

runner = CliRunner()
BUDGET_PER_CALL = 2048
BUDGET_PIPELINE = 6144


def _invoke(args: list[str]) -> str:
    res = runner.invoke(app, args)
    assert res.exit_code == 0, res.output
    return res.stdout


def test_single_subcommand_payload_under_2kb(micro_project: Path) -> None:
    (micro_project / "media" / "clip01.mov").write_bytes(b"stub")
    out = _invoke(["--json", "trim", "--project", str(micro_project), "--dry-run"])
    assert 0 < len(out.encode("utf-8")) <= BUDGET_PER_CALL


def test_pipeline_total_under_6kb(micro_project: Path) -> None:
    (micro_project / "media" / "clip01.mov").write_bytes(b"stub")
    trim_out = _invoke(["--json", "trim", "--project", str(micro_project), "--dry-run"])
    restruct_out = _invoke(["--json", "restructure", "--project", str(micro_project), "--dry-run"])
    render_out = _invoke(["--json", "render", "--project", str(micro_project), "--dry-run"])
    total = sum(len(s.encode("utf-8")) for s in (trim_out, restruct_out, render_out))
    assert total <= BUDGET_PIPELINE, f"pipeline stdout {total} bytes exceeds {BUDGET_PIPELINE}"
