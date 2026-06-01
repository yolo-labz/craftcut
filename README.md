# craftcut

Sewing-tutorial editing orchestration CLI. Wraps `auto-editor` (silence trim), `OpenTimelineIO` (FCPXML ↔ MLT), and `melt` (headless render) into Bash-callable subcommands. Designed for Claude Code orchestration with minimal stdout context consumption.

## Install

```bash
uv tool install craftcut
craftcut doctor
```

Requires macOS 14+ on Apple Silicon. External tools: `auto-editor ≥ 26`, `melt ≥ 7.36`, `ffmpeg ≥ 7`.

## Subcommands

- `craftcut doctor` — probe external tool versions
- `craftcut validate` — source integrity check (ffprobe + SRT + rotation)
- `craftcut trim` — per-clip silence trim via auto-editor (parallel)
- `craftcut restructure` — section-map-driven OTIO timeline surgery
- `craftcut render` — melt headless render to 1080×1920 portrait master
- `craftcut derive` — landscape pillarbox + shorts cutdowns

See `specs/010-craftcut/quickstart.md` for the end-to-end walkthrough.

## Status

Pre-release scaffold. See `specs/010-craftcut/tasks.md` for the implementation roadmap.
