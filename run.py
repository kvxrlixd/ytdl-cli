#!/usr/bin/env python3
"""
run.py — project entry point.

Usage
-----
  python run.py [COMMAND] [OPTIONS]

First run: automatically checks for missing packages and prompts
to install them, then starts the CLI.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from pathlib import Path

# ── minimum Python version guard ─────────────────────────────────────────────

if sys.version_info < (3, 9):
    sys.exit(
        "\n  [!] Python 3.9 or newer is required.\n"
        "      Current: " + sys.version + "\n"
    )

# ── ensure project root is importable ────────────────────────────────────────

ROOT = Path(__file__).parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ── auto-install helper ───────────────────────────────────────────────────────

REQUIRED = [
    "yt_dlp",
    "rich",
    "typer",
]

INSTALL_MAP = {
    "yt_dlp": "yt-dlp",
    "rich":   "rich",
    "typer":  "typer[all]",
}


def _check_and_install() -> None:
    missing = []
    for pkg in REQUIRED:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)

    if not missing:
        return

    print("\n  Some dependencies are not installed:")
    for m in missing:
        print(f"    · {INSTALL_MAP[m]}")

    answer = input("\n  Install them now? [Y/n]: ").strip().lower()
    if answer in ("", "y", "yes"):
        install_args = [sys.executable, "-m", "pip", "install"] + [INSTALL_MAP[m] for m in missing]
        result = subprocess.run(install_args)
        if result.returncode != 0:
            sys.exit("\n  [!] Installation failed. Run manually:\n"
                     "      pip install -r requirements.txt\n")
        print("\n  Dependencies installed. Starting…\n")
    else:
        sys.exit(
            "\n  Run:  pip install -r requirements.txt\n"
            "  Then: python run.py\n"
        )


# ── logging setup ─────────────────────────────────────────────────────────────

def _setup_logging() -> None:
    try:
        from app.config import LOG_FILE, CONFIG_DIR
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            level=logging.WARNING,
            format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
            handlers=[
                logging.FileHandler(LOG_FILE, encoding="utf-8"),
            ],
        )
    except Exception:
        logging.basicConfig(level=logging.WARNING)


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    _check_and_install()
    _setup_logging()

    from app.cli import app
    app()


if __name__ == "__main__":
    main()
