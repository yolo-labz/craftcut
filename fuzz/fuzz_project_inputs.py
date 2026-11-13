"""Atheris fuzz target for craftcut's user-supplied project files.

Drives the real loaders on the three files an editor writes by hand: `.craftcut/config.toml`,
`section-map.yaml` (the FR-044 hardened YAML loader) and `.craftcut/manifest.json`.
Run: `uv sync --frozen --group fuzz`, then
`uv run --no-sync python fuzz/fuzz_project_inputs.py -max_total_time=60`.
Only the documented validation failures are expected; any other exception is a bug.
"""

from __future__ import annotations

import contextlib
import json
import sys
import tempfile
import tomllib
from pathlib import Path

import atheris

with atheris.instrument_imports(include=["craftcut", "ruamel", "tomllib"]):
    from pydantic import ValidationError

    from craftcut.config import ProjectLayout, load_project_config
    from craftcut.errors import BadInputError
    from craftcut.manifest import load_manifest
    from craftcut.sandbox import load_section_map

_ROOT = Path(tempfile.mkdtemp(prefix="craftcut-fuzz-"))
_LAYOUT = ProjectLayout.for_project(_ROOT)
_LAYOUT.state.mkdir(parents=True, exist_ok=True)
# A corrupt manifest.json that is not UTF-8 raises UnicodeDecodeError, like invalid JSON raises
# JSONDecodeError: both are ValueError and both mean "corrupt file".
_EXPECTED = (
    ValidationError,
    BadInputError,
    tomllib.TOMLDecodeError,
    json.JSONDecodeError,
    UnicodeDecodeError,
)


def test_one_input(data: bytes) -> None:
    fdp = atheris.FuzzedDataProvider(data)
    which = fdp.ConsumeIntInRange(0, 2)
    payload = fdp.ConsumeBytes(len(data))
    with contextlib.suppress(*_EXPECTED):
        if which == 0:
            _LAYOUT.config.write_bytes(payload)
            load_project_config(_LAYOUT)
        elif which == 1:
            _LAYOUT.section_map.write_bytes(payload)
            load_section_map(_LAYOUT.section_map, _LAYOUT)
        else:
            _LAYOUT.manifest.write_bytes(payload)
            load_manifest(_LAYOUT)


if __name__ == "__main__":
    atheris.Setup(sys.argv, test_one_input)
    atheris.Fuzz()
