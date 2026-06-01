"""Typer root app with global flags + subcommand wiring."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Any

import typer
from pydantic import BaseModel
from rich.console import Console

from craftcut import __version__
from craftcut.commands.derive import run_derive
from craftcut.commands.render import run_render
from craftcut.commands.restructure import run_restructure
from craftcut.commands.trim import run_trim
from craftcut.commands.validate import run_validate
from craftcut.config import ProjectLayout, load_project_config
from craftcut.doctor import run_doctor
from craftcut.errors import (
    BadInputError,
    CraftcutError,
    ExternalToolError,
    InternalError,
    SourceIntegrityError,
    StatusCode,
)
from craftcut.platform import best_effort_banner, color_enabled

_ERROR_TYPE_MAP: dict[type[Exception], tuple[str, str]] = {
    BadInputError: ("/errors/bad-input", "Bad input"),
    SourceIntegrityError: ("/errors/source-integrity", "Source integrity failure"),
    ExternalToolError: ("/errors/external-tool", "External tool failure"),
    InternalError: ("/errors/internal", "Internal error"),
}

app = typer.Typer(
    name="craftcut",
    help="Sewing-tutorial editing orchestration CLI.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"craftcut {__version__}")
        raise typer.Exit


@app.callback()
def root(
    ctx: typer.Context,
    _version: Annotated[
        bool,
        typer.Option(
            "--version",
            help="Print version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
    json_out: Annotated[
        bool,
        typer.Option("--json", help="Emit machine-readable JSON on stdout."),
    ] = False,
    no_color: Annotated[
        bool,
        typer.Option("--no-color", help="Disable ANSI color (also NO_COLOR env)."),
    ] = False,
    no_hwaccel: Annotated[
        bool, typer.Option("--no-hwaccel", help="Force software encode (libx264).")
    ] = False,
    accept_pacing: Annotated[
        bool,
        typer.Option(
            "--accept-pacing",
            help="Silence cuts-per-minute out-of-band warning (FR-055).",
        ),
    ] = False,
    allow_outside_root: Annotated[
        bool,
        typer.Option(
            "--allow-outside-root",
            help="Bypass FR-046 path-root guard (audit-logged).",
        ),
    ] = False,
) -> None:
    banner = best_effort_banner()
    if banner:
        typer.echo(banner, err=True)

    color = color_enabled(sys.stderr) and not no_color
    ctx.obj = GlobalOpts(
        json_out=json_out,
        color=color,
        no_hwaccel=no_hwaccel,
        accept_pacing=accept_pacing,
        allow_outside_root=allow_outside_root,
    )


class GlobalOpts:
    __slots__ = ("accept_pacing", "allow_outside_root", "color", "json_out", "no_hwaccel")

    def __init__(
        self,
        *,
        json_out: bool,
        color: bool,
        no_hwaccel: bool,
        accept_pacing: bool,
        allow_outside_root: bool,
    ) -> None:
        self.json_out = json_out
        self.color = color
        self.no_hwaccel = no_hwaccel
        self.accept_pacing = accept_pacing
        self.allow_outside_root = allow_outside_root


def _emit(opts: GlobalOpts, payload: BaseModel | dict[str, Any]) -> None:  # noqa: ARG001
    body = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
    json.dump(body, sys.stdout, separators=(",", ":"))
    sys.stdout.write("\n")


def _handle_error(err: Exception) -> None:
    type_url, title = _ERROR_TYPE_MAP.get(type(err), ("/errors/internal", "Internal error"))
    code = getattr(err, "code", "INTERNAL")
    status: StatusCode = getattr(err, "status", 5)
    envelope = CraftcutError(
        type=type_url,
        title=title,
        status=status,
        code=code,
        detail=str(err),
        remedy="run `craftcut doctor` and re-check inputs",
    )
    json.dump(
        envelope.model_dump(by_alias=True, exclude_none=True),
        sys.stdout,
        separators=(",", ":"),
    )
    sys.stdout.write("\n")
    raise typer.Exit(code=status)


def _layout(project: Path) -> ProjectLayout:
    return ProjectLayout.for_project(project)


@app.command()
def doctor(ctx: typer.Context) -> None:
    """Probe external tool versions + install remedies."""
    opts: GlobalOpts = ctx.obj
    report = run_doctor()
    if opts.json_out:
        typer.echo(report.model_dump_json(exclude_none=True))
    else:
        console = Console(stderr=True, force_terminal=opts.color)
        for tool in report.tools:
            glyph = "[OK]" if tool.present else "[MISSING]"
            line = f"{glyph} {tool.name:<12} {tool.version or '—':<12} {tool.path or ''}"
            console.print(line)
            if tool.remedy:
                console.print(f"    remedy: {tool.remedy}")
    raise typer.Exit(code=0 if report.ok else 2)


@app.command()
def validate(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Project folder root.")],
    strict: Annotated[
        bool,
        typer.Option("--strict", help="Promote warnings to findings."),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Plan only; no external calls."),
    ] = False,
) -> None:
    """Source-integrity check (FCPXML↔MOV parity, SRT bounds, rotation, disk budget)."""
    opts: GlobalOpts = ctx.obj
    layout = _layout(project)
    try:
        report = run_validate(
            layout,
            strict=strict,
            dry_run=dry_run,
            argv=sys.argv,
        )
    except (BadInputError, SourceIntegrityError, ExternalToolError, InternalError) as err:
        _handle_error(err)
        return
    _emit(opts, report)
    raise typer.Exit(code=0 if report.status == "ok" else 2)


@app.command()
def trim(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Project folder root.")],
    threshold: Annotated[float, typer.Option("--threshold", help="Silence threshold pct.")] = 4.0,
    margin: Annotated[float, typer.Option("--margin", help="Margin seconds around speech.")] = 0.2,
    force: Annotated[bool, typer.Option("--force", help="Rebuild even if cached.")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    """Per-clip silence trim via auto-editor."""
    opts: GlobalOpts = ctx.obj
    layout = _layout(project)
    cfg = load_project_config(layout)
    cfg = cfg.model_copy(
        update={
            "trim": cfg.trim.model_copy(
                update={"threshold_pct": threshold, "margin_seconds": margin}
            )
        }
    )
    try:
        result = run_trim(layout, cfg=cfg, force=force, dry_run=dry_run, argv=sys.argv)
    except (BadInputError, SourceIntegrityError, ExternalToolError, InternalError) as err:
        _handle_error(err)
        return
    _emit(opts, result)


@app.command()
def restructure(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Project folder root.")],
    section_map: Annotated[
        Path | None,
        typer.Option("--section-map", help="Override section-map path."),
    ] = None,
    force: Annotated[bool, typer.Option("--force")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    """Section-map driven OTIO timeline surgery."""
    opts: GlobalOpts = ctx.obj
    layout = _layout(project)
    try:
        result = run_restructure(
            layout,
            section_map=section_map,
            force=force,
            dry_run=dry_run,
            allow_outside_root=opts.allow_outside_root,
            argv=sys.argv,
        )
    except (BadInputError, SourceIntegrityError, ExternalToolError, InternalError) as err:
        _handle_error(err)
        return
    _emit(opts, result)


@app.command()
def render(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Project folder root.")],
    force: Annotated[bool, typer.Option("--force")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Emit dependency DAG JSON.")] = False,
    proof: Annotated[
        bool,
        typer.Option("--proof", help="Print the powermetrics argv for saturation capture."),
    ] = False,
) -> None:
    """Headless render via melt to 1080×1920 portrait master."""
    opts: GlobalOpts = ctx.obj
    layout = _layout(project)
    if proof:
        _emit(
            opts,
            {
                "schema": "craftcut.render.proof.v1",
                "argv": [
                    "sudo",
                    "powermetrics",
                    "--samplers",
                    "cpu_power,gpu_power,thermal",
                    "-i",
                    "1000",
                ],
            },
        )
        raise typer.Exit(code=0)

    try:
        result = run_render(
            layout,
            force=force,
            dry_run=dry_run,
            no_hwaccel=opts.no_hwaccel,
            allow_outside_root=opts.allow_outside_root,
            argv=sys.argv,
        )
    except (BadInputError, SourceIntegrityError, ExternalToolError, InternalError) as err:
        _handle_error(err)
        return
    _emit(opts, result)


@app.command()
def derive(
    ctx: typer.Context,
    project: Annotated[Path, typer.Option("--project", help="Project folder root.")],
    landscape: Annotated[bool, typer.Option("--landscape")] = False,
    shorts: Annotated[int | None, typer.Option("--shorts", help="Number of cutdowns.")] = None,
    force: Annotated[bool, typer.Option("--force")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    """Landscape pillarbox (1920×1080) or shorts cutdowns (≤ 180 s per segment)."""
    opts: GlobalOpts = ctx.obj
    layout = _layout(project)
    try:
        result = run_derive(
            layout,
            landscape=landscape,
            shorts=shorts,
            force=force,
            dry_run=dry_run,
            no_hwaccel=opts.no_hwaccel,
            allow_outside_root=opts.allow_outside_root,
            argv=sys.argv,
        )
    except (BadInputError, SourceIntegrityError, ExternalToolError, InternalError) as err:
        _handle_error(err)
        return
    _emit(opts, result)


if __name__ == "__main__":
    app()
