"""T034 — probe_file parses ffprobe JSON; _parse_rational handles edge cases."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from craftcut import probe as pmod
from craftcut.errors import ExternalToolError


class _Ok:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.stdout: str = json.dumps(payload)
        self.stderr: str = ""


def _payload() -> dict[str, Any]:
    return {
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1920,
                "height": 1080,
                "r_frame_rate": "30000/1001",
                "duration": "12.345",
                "sample_aspect_ratio": "1:1",
                "side_data_list": [{"rotation": -90}],
            },
            {
                "codec_type": "audio",
                "codec_name": "aac",
                "channels": 2,
                "sample_rate": "48000",
            },
        ],
        "format": {"duration": "12.345"},
    }


def _stub_ffprobe_path() -> str:
    return "/usr/bin/ffprobe"


def _null_which(_tool: str) -> str | None:
    return None


def test_parse_rational_normal() -> None:
    got = pmod._parse_rational("30000/1001")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    assert got == pytest.approx(29.97, rel=1e-3)


def test_parse_rational_zero_division() -> None:
    got = pmod._parse_rational("0/0")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    assert got == 0.0


def test_parse_rational_garbage() -> None:
    got = pmod._parse_rational("abc")  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
    assert got == 0.0


def test_probe_file_parses_streams(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pmod, "_find_ffprobe", _stub_ffprobe_path)

    def _fake_run(*_a: Any, **_kw: Any) -> _Ok:
        return _Ok(_payload())

    monkeypatch.setattr(pmod.subprocess, "run", _fake_run, raising=False)
    result = pmod.probe_file(tmp_path / "stub.mov")
    assert result.width == 1920
    assert result.height == 1080
    assert result.rotation == -90
    assert result.codec == "h264"
    assert result.audio_codec == "aac"
    assert result.audio_channels == 2
    assert result.audio_sample_rate == 48000
    assert result.duration_seconds == pytest.approx(12.345)


def test_probe_file_raises_on_ffprobe_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(pmod, "_find_ffprobe", _stub_ffprobe_path)

    def _boom(*_a: Any, **_kw: Any) -> Any:
        raise subprocess.CalledProcessError(1, "ffprobe", stderr="bad file")

    monkeypatch.setattr(pmod.subprocess, "run", _boom, raising=False)
    with pytest.raises(ExternalToolError, match="ffprobe failed"):
        pmod.probe_file(tmp_path / "stub.mov")


def test_probe_file_missing_binary(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(pmod.shutil, "which", _null_which)
    with pytest.raises(ExternalToolError, match="ffprobe not found"):
        pmod.probe_file(tmp_path / "stub.mov")
