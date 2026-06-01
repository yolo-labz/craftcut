"""ndjson structured logger with schema header + retention prune."""

from __future__ import annotations

import datetime as dt
import gzip
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import structlog

from craftcut.config import CraftcutProjectConfig, ProjectLayout

LOG_SCHEMA = "craftcut.log.v1"


def _utc_now_iso() -> str:
    return dt.datetime.now(dt.UTC).isoformat().replace("+00:00", "Z")


def prune_logs(layout: ProjectLayout, cfg: CraftcutProjectConfig) -> None:
    """FR-049 — prune ndjson beyond retention_days, keep floor; gzip after gzip_after_days."""
    if not layout.logs.exists():
        return
    now = dt.datetime.now(dt.UTC)
    files = sorted(
        layout.logs.glob("*.ndjson*"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    floor = cfg.log.retention_floor
    for idx, path in enumerate(files):
        age_days = (now.timestamp() - path.stat().st_mtime) / 86_400
        if idx < floor:
            _maybe_gzip(path, age_days, cfg.log.gzip_after_days)
            continue
        if age_days > cfg.log.retention_days:
            path.unlink(missing_ok=True)
        else:
            _maybe_gzip(path, age_days, cfg.log.gzip_after_days)


def _maybe_gzip(path: Path, age_days: float, threshold: int) -> None:
    if path.suffix == ".gz" or age_days < threshold:
        return
    gz = path.with_suffix(path.suffix + ".gz")
    with path.open("rb") as src, gzip.open(gz, "wb") as dst:
        shutil.copyfileobj(src, dst)
    path.unlink(missing_ok=True)


def configure_logger(layout: ProjectLayout, subcommand: str, argv: list[str]) -> Path:
    """Wire structlog to an ndjson file under .craftcut/logs/. Returns log path."""
    layout.logs.mkdir(parents=True, exist_ok=True)
    ts = _utc_now_iso().replace(":", "").replace("-", "")
    log_path = layout.logs / f"{ts}-{subcommand}.ndjson"

    header: dict[str, Any] = {
        "schema": LOG_SCHEMA,
        "ts": _utc_now_iso(),
        "subcommand": subcommand,
        "argv": argv,
    }
    with log_path.open("w", encoding="utf-8") as fp:
        fp.write(json.dumps(header, ensure_ascii=False) + "\n")

    def _sink(_logger: Any, _name: str, event_dict: structlog.types.EventDict) -> str:
        with log_path.open("a", encoding="utf-8") as out:
            out.write(json.dumps(event_dict, ensure_ascii=False) + "\n")
        return json.dumps(event_dict, ensure_ascii=False)

    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _sink,
        ],
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )
    return log_path
