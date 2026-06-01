# Troubleshooting

## Exit codes

| Code | Meaning              | Typical cause                                       | First step                                  |
|------|----------------------|-----------------------------------------------------|---------------------------------------------|
| 0    | ok                   | —                                                   | —                                           |
| 2    | `BAD_INPUT`          | Bad flags, missing section-map, path outside root.  | Read `detail` in the JSON envelope.         |
| 3    | `SOURCE_INTEGRITY`   | Render self-probe mismatch, rotation/SRT defect.    | `craftcut validate --project X --strict`.   |
| 4    | `EXTERNAL_TOOL`      | auto-editor / melt / ffmpeg / ffprobe crashed.      | `craftcut doctor` to verify install.        |
| 5    | `INTERNAL`           | craftcut bug. Not your fault.                       | File an issue with the `manifest.json`.     |

Every non-zero exit is accompanied by an RFC 9457 Problem Details envelope on
stdout (schema `craftcut.error.v1`). Inspect `code`, `detail`, `remedy`.

## Log & state paths

All per-project artifacts live under `<project>/.craftcut/`:

| Path                       | What it is                                                   |
|----------------------------|--------------------------------------------------------------|
| `manifest.json`            | Stage history + cache keys + tool versions.                  |
| `progress.json`            | Single-tick rewrite; pollable mid-run. Schema `craftcut.progress.v1`. |
| `logs/<timestamp>.ndjson`  | Structured logs; gzipped after 7 d, retained 30 d (floor 10).|
| `manifest.lock`            | Advisory `filelock`; auto-broken after 24 h.                 |
| `polished.mlt_xml`         | OTIO-bridged timeline handed to `melt`.                      |
| `master.mp4`               | Final 1080×1920 portrait render.                             |
| `.progress-*.tmp`          | Orphan tempfiles left after a crash — safe to inspect or delete.|

## `craftcut doctor` remedies

| Tool         | Missing → install                                 |
|--------------|---------------------------------------------------|
| `auto-editor`| `uv tool install auto-editor` or `brew install auto-editor`. |
| `melt`       | `brew install mlt`.                               |
| `ffmpeg`     | `brew install ffmpeg`.                            |
| `ffprobe`    | Bundled with `ffmpeg`.                            |

## Cancelling mid-run

Press `Ctrl-C`. craftcut forwards `SIGTERM` to the process group (`killpg`), so
child decoders/encoders shut down cleanly. The next invocation:

1. Breaks stale locks (> 24 h, FR-048).
2. Leaves orphan `.progress-*.tmp` in place for inspection.
3. Re-runs any stage whose cache-key hash no longer matches.

## Pacing warning

`restructure` flags `pacing_warning: true` when cuts-per-minute falls outside
`[4.0, 12.0]`. Accept intentional slow beats with `--accept-pacing`.

## Path-guard bypass (`--allow-outside-root`)

Emits a structured warning in `logs/*.ndjson` (`event: path_root_guard_bypassed`)
and proceeds. Use only when the section-map legitimately lives outside the
project directory (shared narrative templates, tutorial series).

## Hardware acceleration

Default: `h264_videotoolbox` (VideoToolbox). Force software encode with
`--no-hwaccel` if thermal envelope is an issue on the M-series laptops. The
render self-probe (FR-035) compares output WxH against `config.render`; a
mismatch exits 3.
