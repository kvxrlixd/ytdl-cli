"""
utils.py — shared helpers used across the application.

Responsibilities:
  - dependency presence checks (ffmpeg, yt-dlp)
  - filename sanitization
  - human-readable size / speed / ETA formatting
  - random User-Agent pool
  - yt-dlp update check / self-update
  - platform detection
"""

from __future__ import annotations

import os
import platform
import random
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Optional


# ── platform ──────────────────────────────────────────────────────────────────

SYSTEM = platform.system()   # "Windows" | "Darwin" | "Linux"
IS_WINDOWS = SYSTEM == "Windows"
IS_MACOS = SYSTEM == "Darwin"
IS_LINUX = SYSTEM == "Linux"


# ── dependency checks ─────────────────────────────────────────────────────────

def check_ffmpeg() -> tuple[bool, str]:
    """Return (found, version_string)."""
    path = shutil.which("ffmpeg")
    if path is None:
        return False, ""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        first_line = result.stdout.splitlines()[0] if result.stdout else ""
        return True, first_line
    except Exception:
        return False, ""


def check_ytdlp() -> tuple[bool, str]:
    """Return (found, version_string)."""
    try:
        import yt_dlp  # noqa: F401
        from yt_dlp.version import __version__ as v
        return True, v
    except ImportError:
        return False, ""


def assert_dependencies() -> None:
    """Raise SystemExit with a human-friendly message if deps are missing."""
    ytdlp_ok, ytdlp_ver = check_ytdlp()
    ffmpeg_ok, ffmpeg_ver = check_ffmpeg()

    missing = []
    if not ytdlp_ok:
        missing.append("yt-dlp  →  pip install yt-dlp")
    if not ffmpeg_ok:
        if IS_WINDOWS:
            missing.append("ffmpeg  →  https://ffmpeg.org/download.html  (add to PATH)")
        elif IS_MACOS:
            missing.append("ffmpeg  →  brew install ffmpeg")
        else:
            missing.append("ffmpeg  →  sudo apt install ffmpeg  OR  sudo dnf install ffmpeg")

    if missing:
        lines = ["", "  [!] Missing required dependencies:", ""]
        for m in missing:
            lines.append(f"      {m}")
        lines.append("")
        sys.exit("\n".join(lines))


# ── filename sanitization ─────────────────────────────────────────────────────

_UNSAFE_CHARS = r'[<>:"/\\|?*\x00-\x1f]'
_RESERVED_NAMES = {
    "CON","PRN","AUX","NUL",
    "COM1","COM2","COM3","COM4","COM5","COM6","COM7","COM8","COM9",
    "LPT1","LPT2","LPT3","LPT4","LPT5","LPT6","LPT7","LPT8","LPT9",
}


def sanitize_filename(name: str, max_length: int = 200) -> str:
    """Return a filesystem-safe filename."""
    # normalize unicode
    name = unicodedata.normalize("NFKC", name)
    # strip unsafe chars
    name = re.sub(_UNSAFE_CHARS, "_", name)
    # collapse consecutive spaces/underscores
    name = re.sub(r"[_ ]{2,}", " ", name).strip(". ")
    # Windows reserved names
    stem = Path(name).stem.upper()
    if stem in _RESERVED_NAMES:
        name = f"_{name}"
    # length cap
    if len(name) > max_length:
        ext = Path(name).suffix
        name = name[: max_length - len(ext)] + ext
    return name or "download"


# ── human-readable formatters ─────────────────────────────────────────────────

_SIZE_UNITS = ["B", "KB", "MB", "GB", "TB"]


def format_bytes(n: Optional[float]) -> str:
    if n is None:
        return "?"
    n = float(n)
    for unit in _SIZE_UNITS[:-1]:
        if abs(n) < 1024.0:
            return f"{n:6.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} {_SIZE_UNITS[-1]}"


def format_speed(n: Optional[float]) -> str:
    if n is None:
        return "?/s"
    return format_bytes(n) + "/s"


def format_eta(seconds: Optional[float]) -> str:
    if seconds is None:
        return "--:--"
    seconds = int(seconds)
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def format_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "?"
    return format_eta(seconds)


# ── user-agent pool ───────────────────────────────────────────────────────────

_USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Firefox on Linux
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    # Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
    # Safari on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
]


def random_user_agent() -> str:
    return random.choice(_USER_AGENTS)


# ── yt-dlp self-update ────────────────────────────────────────────────────────

def update_ytdlp() -> tuple[bool, str]:
    """Run yt-dlp's built-in updater. Returns (success, message)."""
    try:
        import yt_dlp
        from yt_dlp.update import Updater
        updater = Updater(yt_dlp.YoutubeDL())
        result = updater.update()
        return True, str(result) if result else "Already up to date."
    except Exception as exc:
        # fallback: pip upgrade
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "yt-dlp", "-q"],
                check=True,
                timeout=60,
            )
            return True, "Updated via pip."
        except Exception as exc2:
            return False, str(exc2)


def check_for_updates(current_version: str) -> Optional[str]:
    """
    Fetch latest yt-dlp version tag from GitHub.
    Returns the newer version string, or None if already current / unreachable.
    """
    try:
        import urllib.request, json as _json
        url = "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest"
        req = urllib.request.Request(url, headers={"User-Agent": random_user_agent()})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = _json.loads(resp.read())
        latest = data.get("tag_name", "")
        if latest and latest != current_version:
            return latest
    except Exception:
        pass
    return None


# ── misc ──────────────────────────────────────────────────────────────────────

def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def url_is_playlist(url: str) -> bool:
    return "playlist" in url.lower() or "list=" in url


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
