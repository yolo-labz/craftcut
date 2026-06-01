"""Platform gates + TTY/color/Unicode handling (FR-050..054)."""

from __future__ import annotations

import os
import platform
import sys
import unicodedata


def is_apple_silicon_macos14() -> bool:
    """FR-053 launch target: macOS ≥ 14 on arm64."""
    if sys.platform != "darwin":
        return False
    if platform.machine() != "arm64":
        return False
    mac_ver = platform.mac_ver()[0]
    if not mac_ver:
        return False
    major = int(mac_ver.split(".", 1)[0])
    return major >= 14


def best_effort_banner() -> str | None:
    """Emit a one-line banner on non-target hosts (FR-053). None on target."""
    if is_apple_silicon_macos14():
        return None
    return (
        "craftcut: best-effort unsupported host "
        f"({sys.platform}/{platform.machine()}) — Apple Silicon macOS 14+ is the launch target"
    )


def color_enabled(stream: object) -> bool:
    """FR-050 NO_COLOR + non-TTY auto-disable."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("CRAFTCUT_NO_COLOR") or os.environ.get("CLICOLOR") == "0":
        return False
    isatty = getattr(stream, "isatty", None)
    return bool(isatty and isatty())


def use_ascii_glyphs() -> bool:
    """FR-052 — degrade to ASCII when LC_ALL=C or similar."""
    locale_env = os.environ.get("LC_ALL") or os.environ.get("LANG") or ""
    return locale_env.upper() in {"C", "POSIX"}


def nfc(text: str) -> str:
    """FR-054 — iOS emits NFD; normalize on read."""
    return unicodedata.normalize("NFC", text)
