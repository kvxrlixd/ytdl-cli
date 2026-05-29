"""
ui.py — all Rich-based terminal rendering.

Single responsibility: display. No download logic lives here.
Every component uses a minimal monochrome-leaning palette with
strategic accent colours so the output looks like a proper
professional tool rather than a toy.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from rich import box
from rich.columns import Columns
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    DownloadColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.rule import Rule
from rich.style import Style
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

from app.utils import format_bytes, format_duration

# ── theme & console ───────────────────────────────────────────────────────────

THEME = Theme(
    {
        "accent":    "bold cyan",
        "muted":     "dim white",
        "ok":        "bold green",
        "warn":      "bold yellow",
        "error":     "bold red",
        "label":     "bold white",
        "vid":       "cyan",
        "aud":       "magenta",
        "info":      "blue",
        "highlight": "bold cyan",
    }
)

console = Console(theme=THEME, highlight=False)


# ── banner ────────────────────────────────────────────────────────────────────

BANNER = r"""
 __  ____________  __         ________    ____
 \ \/ /_  __/ __ \/ /        / ____/ /   /  _/
  \  / / / / / / / /  ______/ /   / /    / /  
  / / / / / /_/ / /__/_____/ /___/ /____/ /   
 /_/ /_/ /_____/_____/     \____/_____/___/   

"""


def print_banner(version: str = "1.0.0") -> None:
    console.print(BANNER, style="accent", highlight=False)
    console.print(
        f"  [muted]yt-dlp powered YouTube downloader  ·  v{version}[/muted]\n"
    )


def print_rule(title: str = "") -> None:
    console.print(Rule(title, style="dim cyan"))


# ── video info panel ──────────────────────────────────────────────────────────

def print_video_info(info: dict) -> None:
    if info.get("type") == "playlist":
        table = Table(box=None, show_header=False, padding=(0, 2))
        table.add_column(style="muted", width=14)
        table.add_column(style="label")
        table.add_row("type",     "[accent]playlist[/accent]")
        table.add_row("title",    info.get("title", "?"))
        table.add_row("uploader", info.get("uploader", "?"))
        table.add_row("count",    str(info.get("count", "?")))
    else:
        dur = format_duration(info.get("duration"))
        views = f"{info.get('view_count', 0):,}" if info.get("view_count") else "?"
        date_raw = info.get("upload_date", "")
        date_str = (
            f"{date_raw[:4]}-{date_raw[4:6]}-{date_raw[6:]}"
            if len(date_raw) == 8
            else date_raw
        )
        age = info.get("age_limit", 0)
        age_str = f"[warn]{age}+[/warn]" if age else "—"

        table = Table(box=None, show_header=False, padding=(0, 2))
        table.add_column(style="muted", width=14)
        table.add_column(style="label")
        table.add_row("title",    info.get("title", "?"))
        table.add_row("uploader", info.get("uploader", "?"))
        table.add_row("duration", dur)
        table.add_row("views",    views)
        table.add_row("uploaded", date_str)
        table.add_row("age gate", age_str)

    console.print(
        Panel(table, title="[accent]  video info[/accent]", border_style="dim cyan", padding=(0, 1))
    )


# ── format table ──────────────────────────────────────────────────────────────

def print_formats_table(formats: list[dict]) -> None:
    table = Table(
        box=box.SIMPLE_HEAD,
        border_style="dim",
        header_style="bold cyan",
        show_lines=False,
        padding=(0, 1),
    )
    table.add_column("id",         style="dim",     width=8)
    table.add_column("ext",        style="muted",   width=6)
    table.add_column("resolution", style="vid",     width=12)
    table.add_column("fps",        style="muted",   width=6)
    table.add_column("vcodec",     style="vid",     width=8)
    table.add_column("acodec",     style="aud",     width=8)
    table.add_column("size",       style="label",   width=10, justify="right")
    table.add_column("bitrate",    style="muted",   width=10, justify="right")
    table.add_column("note",       style="muted")

    for f in formats:
        size = format_bytes(f.get("filesize")) if f.get("filesize") else "?"
        tbr  = f"{f['tbr']:.0f}k" if f.get("tbr") else "?"
        fps  = str(f["fps"]) if f.get("fps") else "—"
        table.add_row(
            f["format_id"],
            f["ext"],
            f["resolution"],
            fps,
            f["vcodec"],
            f["acodec"],
            size,
            tbr,
            f["note"],
        )

    console.print(table)
    console.print(f"  [muted]{len(formats)} formats listed[/muted]\n")


# ── history table ─────────────────────────────────────────────────────────────

def print_history_table(history: list[dict], limit: int = 20) -> None:
    if not history:
        console.print("  [muted]No download history.[/muted]")
        return

    table = Table(
        box=box.SIMPLE_HEAD,
        border_style="dim",
        header_style="bold cyan",
        show_lines=False,
        padding=(0, 1),
    )
    table.add_column("#",      style="dim",   width=4,  justify="right")
    table.add_column("date",   style="muted", width=12)
    table.add_column("type",   style="accent",width=6)
    table.add_column("title",  style="label", max_width=50, no_wrap=True)
    table.add_column("quality",style="vid",   width=8)
    table.add_column("status", style="ok",    width=8)

    for i, entry in enumerate(history[:limit], 1):
        status_style = "ok" if entry.get("status") == "done" else "error"
        table.add_row(
            str(i),
            entry.get("date", "?")[:10],
            entry.get("type", "video"),
            entry.get("title", "?"),
            entry.get("quality", "?"),
            f"[{status_style}]{entry.get('status', '?')}[/{status_style}]",
        )

    console.print(table)


# ── progress display ──────────────────────────────────────────────────────────

def make_download_progress() -> Progress:
    """Return a Rich Progress configured for downloads."""
    return Progress(
        SpinnerColumn(spinner_name="dots", style="cyan"),
        TextColumn("[bold cyan]{task.description}", justify="left"),
        BarColumn(bar_width=36, style="cyan", complete_style="bold cyan", finished_style="green"),
        "[progress.percentage]{task.percentage:>5.1f}%",
        "·",
        DownloadColumn(binary_units=True),
        "·",
        TransferSpeedColumn(),
        "·",
        TextColumn("ETA", style="muted"),
        TimeRemainingColumn(),
        console=console,
        transient=False,
    )


def make_playlist_progress() -> Progress:
    """Return a Rich Progress for playlist-level tracking."""
    return Progress(
        SpinnerColumn(spinner_name="line", style="dim cyan"),
        TextColumn("[dim cyan]{task.description}"),
        BarColumn(bar_width=30, style="dim cyan", complete_style="cyan"),
        MofNCompleteColumn(),
        "·",
        TimeElapsedColumn(),
        console=console,
        transient=False,
    )


# ── status messages ───────────────────────────────────────────────────────────

def ok(msg: str)    -> None: console.print(f"  [ok]✓[/ok]  {msg}")
def warn(msg: str)  -> None: console.print(f"  [warn]![/warn]  {msg}")
def error(msg: str) -> None: console.print(f"  [error]✗[/error]  {msg}")
def info(msg: str)  -> None: console.print(f"  [muted]·[/muted]  {msg}")


# ── confirm prompt ────────────────────────────────────────────────────────────

def confirm(prompt: str, default: bool = True) -> bool:
    hint = "[Y/n]" if default else "[y/N]"
    try:
        answer = console.input(f"  [muted]{prompt} {hint}:[/muted] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        console.print()
        return False
    if not answer:
        return default
    return answer in ("y", "yes")


# ── config display ────────────────────────────────────────────────────────────

def print_config(cfg) -> None:
    import dataclasses
    table = Table(box=box.SIMPLE_HEAD, border_style="dim", header_style="bold cyan", padding=(0, 2))
    table.add_column("key",   style="muted",  width=26)
    table.add_column("value", style="label")

    for f in dataclasses.fields(cfg):
        val = getattr(cfg, f.name)
        val_str = str(val) if val is not None else "[dim]none[/dim]"
        table.add_row(f.name, val_str)

    console.print(Panel(table, title="[accent]  config[/accent]", border_style="dim cyan"))


# ── dependency status panel ───────────────────────────────────────────────────

def print_dependency_status(ffmpeg_ok: bool, ffmpeg_ver: str, ytdlp_ok: bool, ytdlp_ver: str) -> None:
    rows = []
    for name, ok_flag, ver in [("yt-dlp", ytdlp_ok, ytdlp_ver), ("ffmpeg", ffmpeg_ok, ffmpeg_ver)]:
        sym   = "[ok]✓[/ok]" if ok_flag else "[error]✗[/error]"
        ver_s = f"[muted]{ver}[/muted]" if ver else "[muted]not found[/muted]"
        rows.append(f"  {sym}  [label]{name:<10}[/label]  {ver_s}")
    console.print("\n".join(rows) + "\n")


def prompt_quality_selection(default_quality: str = "best") -> str:
    import sys
    choices = ["best", "8K", "4K", "2K", "1080p", "720p", "480p", "360p", "240p", "144p"]
    
    console.print("\n  [accent]Select video quality:[/accent]\n")
    for i, q in enumerate(choices, 1):
        def_label = " [dim](default)[/dim]" if q == default_quality else ""
        console.print(f"    [{i:2d}] [label]{q:<6}[/label]{def_label}")
    console.print()
    
    while True:
        try:
            choice = console.input("  [muted]Enter choice (1-10) or press Enter for default: [/muted]").strip()
            if not choice:
                return default_quality
            if choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(choices):
                    return choices[idx - 1]
            console.print("  [error]Invalid choice. Please enter a number between 1 and 10.[/error]")
        except (EOFError, KeyboardInterrupt):
            console.print()
            sys.exit(0)
