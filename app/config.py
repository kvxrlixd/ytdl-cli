"""
config.py — persistent configuration management.

Reads/writes ~/.ytdl/config.toml so settings survive between runs.
Falls back to safe defaults when the file is absent or malformed.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

# Python 3.11+ ships tomllib; older installs can `pip install tomli`
if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]

try:
    import tomli_w  # optional write-side
except ImportError:
    tomli_w = None  # type: ignore[assignment]

# ── paths ─────────────────────────────────────────────────────────────────────

CONFIG_DIR = Path.home() / ".ytdl"
CONFIG_FILE = CONFIG_DIR / "config.toml"
HISTORY_FILE = CONFIG_DIR / "history.json"
LOG_FILE = CONFIG_DIR / "ytdl.log"

# ── defaults ──────────────────────────────────────────────────────────────────

DEFAULT_OUTPUT_DIR = str(Path.home() / "Downloads" / "ytdl")

QUALITY_CHOICES = ["144p", "240p", "360p", "480p", "720p", "1080p", "2K", "4K", "8K", "best"]
FPS_CHOICES = ["30", "60", "best"]
BROWSER_CHOICES = ["chrome", "firefox", "edge", "opera", "brave", "safari", "chromium", "vivaldi"]


@dataclass
class Config:
    # output
    output_dir: str = DEFAULT_OUTPUT_DIR
    filename_template: str = "%(uploader)s - %(title)s [%(id)s].%(ext)s"

    # quality defaults
    default_quality: str = "1080p"
    default_fps: str = "best"
    prefer_av1: bool = False
    prefer_vp9: bool = True

    # audio
    audio_format: str = "mp3"
    audio_quality: str = "0"           # 0 = best VBR for mp3

    # subtitles
    subtitles: bool = False
    subtitle_langs: list = field(default_factory=lambda: ["en"])
    auto_subtitles: bool = False

    # thumbnails
    embed_thumbnail: bool = False
    write_thumbnail: bool = False

    # network / resilience
    retries: int = 10
    fragment_retries: int = 10
    concurrent_fragments: int = 4
    rate_limit: Optional[str] = None     # e.g. "1M" to cap at 1 MB/s
    sleep_interval: int = 1
    max_sleep_interval: int = 5
    socket_timeout: int = 30

    # cookies
    cookies_browser: Optional[str] = None   # "chrome" | "firefox" | …
    cookies_file: Optional[str] = None      # path to Netscape cookie file

    # parallel downloads
    parallel_downloads: int = 1

    # metadata / extras
    embed_metadata: bool = True
    embed_chapters: bool = True
    sponsorblock_remove: list = field(default_factory=list)  # ["sponsor","intro",…]

    # update
    auto_update_ytdlp: bool = True

    # ui
    no_color: bool = False
    quiet: bool = False


# ── persistence helpers ────────────────────────────────────────────────────────

def _ensure_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    # create downloads folder placeholder
    Path(DEFAULT_OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


def load_config() -> Config:
    """Load config from TOML file; return defaults on any failure."""
    _ensure_dir()
    if not CONFIG_FILE.exists():
        cfg = Config()
        save_config(cfg)
        return cfg

    try:
        if tomllib is not None:
            with CONFIG_FILE.open("rb") as fh:
                data = tomllib.load(fh)
        else:
            # fallback: manual naive TOML key=value parse (no sections)
            data = _naive_toml_read(CONFIG_FILE)

        # only keep known fields
        known = {k: v for k, v in data.items() if k in Config.__dataclass_fields__}
        return Config(**known)
    except Exception:
        return Config()


def save_config(cfg: Config) -> None:
    """Persist Config to TOML (uses tomli_w if available, else JSON fallback)."""
    _ensure_dir()
    data = asdict(cfg)
    if tomli_w is not None:
        with CONFIG_FILE.open("wb") as fh:
            tomli_w.dump(data, fh)
    else:
        # fallback: write as JSON (still readable, not TOML but functional)
        fallback = CONFIG_FILE.with_suffix(".json")
        with fallback.open("w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)


def _naive_toml_read(path: Path) -> dict:
    """Bare-minimum TOML reader for flat key=value (no arrays/tables)."""
    result: dict = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("["):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            result[k] = v
    return result


# ── history helpers ────────────────────────────────────────────────────────────

def load_history() -> list[dict]:
    _ensure_dir()
    if not HISTORY_FILE.exists():
        return []
    try:
        with HISTORY_FILE.open(encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return []


def save_history(entry: dict) -> None:
    _ensure_dir()
    history = load_history()
    history.insert(0, entry)
    history = history[:500]          # cap at 500 entries
    with HISTORY_FILE.open("w", encoding="utf-8") as fh:
        json.dump(history, fh, indent=2, ensure_ascii=False)


def clear_history() -> None:
    if HISTORY_FILE.exists():
        HISTORY_FILE.unlink()
