"""CLI smoke: --version + --help exit 0, doctor runs."""

from __future__ import annotations

from typer.testing import CliRunner

from craftcut.cli import app


def test_version() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "craftcut" in result.stdout


def test_help() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "validate" in result.stdout
    assert "render" in result.stdout
