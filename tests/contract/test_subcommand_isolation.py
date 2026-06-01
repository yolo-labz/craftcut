"""T052a — registering a new subcommand MUST NOT mutate existing schemas (FR-042)."""

from __future__ import annotations

from typer.testing import CliRunner

from craftcut.cli import app

runner = CliRunner()


def _help(cmd: str) -> str:
    return runner.invoke(app, [cmd, "--help"]).stdout


def test_existing_subcommand_help_stable_when_new_one_registered() -> None:
    baselines = {name: _help(name) for name in ("trim", "restructure", "render", "derive")}

    def _stub() -> None:  # pragma: no cover — registration side-effect only
        """Stub command registered in test."""

    app.command("stubcmd")(_stub)

    try:
        for name, baseline in baselines.items():
            assert _help(name) == baseline, f"{name} help mutated after stubcmd registration"
        assert "stubcmd" in runner.invoke(app, ["--help"]).stdout
    finally:
        registered = [c for c in app.registered_commands if c.name == "stubcmd"]
        for cmd in registered:
            app.registered_commands.remove(cmd)
