"""T033 — subcommand JSON envelopes validate against `contracts/*.schema.json`.

Covers the two always-on envelopes: error (RFC 9457) + progress (atomic tick).
Richer per-stage result schemas (render/restructure/derive/validate/trim) are
exercised via their own integration suites; this file pins the wire format
every subcommand shares.
"""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft7Validator

from craftcut.errors import CraftcutError
from craftcut.progress import ProgressWriter

CONTRACTS = Path(__file__).resolve().parents[2] / "contracts"


def _load(name: str) -> dict[str, object]:
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


def _validate(payload: dict[str, object], schema_name: str) -> None:
    Draft7Validator(_load(schema_name)).validate(payload)


def test_error_envelope_conforms() -> None:
    err = CraftcutError(
        type="about:blank",
        title="BadInput",
        status=2,
        code="BAD_INPUT",
        detail="missing section-map",
        remedy="create section-map.yaml",
        stage="restructure",
    )
    payload = err.model_dump(by_alias=True, exclude_none=True)
    _validate(payload, "error.schema.json")


def test_progress_tick_conforms(tmp_path: Path) -> None:
    target = tmp_path / "progress.json"
    writer = ProgressWriter(target, stage="trim")
    writer.tick(phase="decode", pct=0.42, current=42.0, total=100.0)
    payload = json.loads(target.read_text(encoding="utf-8"))
    _validate(payload, "progress.schema.json")
