"""
cli.py — command-line interface built with Typer.

Commands
--------
  get       Download a single video
  audio     Download audio only (MP3/FLAC/etc.)
  playlist  Download an entire playlist
  formats   List available formats for a URL
  history   Show download history
  config    View or edit persistent configuration
  update    Self-update yt-dlp
  check     Verify dependency versions
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.rule import Rule

from app import __version__
from app.config import (
    BROWSER_CHOICES,
    FPS_CHOICES,
    QUALITY_CHOICES,
    Config,
    clear_history,
    load_config,
    load_history,
    save_config,
)
from app.downloader import DownloadManager
from app.formats import get_video_info, list_formats, get_available_qualities
from app.ui import (
    confirm,
    console,
    error,
    info,
    ok,
    print_banner,
    print_config,
    print_dependency_status,
    print_formats_table,
    print_history_table,
    print_rule,
    print_video_info,
    prompt_quality_selection,
    warn,
)
from app.utils import (
    assert_dependencies,
    check_ffmpeg,
    check_for_updates,
    check_ytdlp,
    update_ytdlp,
    url_is_playlist,
)

# ── typer app ─────────────────────────────────────────────────────────────────

app = typer.Typer(
    name="ytdl",
    help="[cyan]ytdl-cli[/cyan] — terminal YouTube downloader",
    rich_markup_mode="rich",
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)

# ── shared option helpers ─────────────────────────────────────────────────────

_quality_help  = f"Video quality. Choices: {', '.join(QUALITY_CHOICES)}"
_fps_help      = f"Frame rate. Choices: {', '.join(FPS_CHOICES)}"
_browser_help  = f"Import cookies from browser. Choices: {', '.join(BROWSER_CHOICES)}"
_output_help   = "Output directory (overrides config)."
_cookies_help  = "Path to a Netscape-format cookies.txt file."


# ── get ───────────────────────────────────────────────────────────────────────

@app.command()
def get(
    url: str = typer.Argument(..., help="YouTube video URL."),
    quality:  Optional[str] = typer.Option(None,     "-q", "--quality",        help=_quality_help),
    fps:      str           = typer.Option("best",   "-f", "--fps",             help=_fps_help),
    output:   Optional[str] = typer.Option(None,     "-o", "--output",          help=_output_help),
    subs:     bool          = typer.Option(False,    "-s", "--subs",            help="Download subtitles."),
    thumb:    bool          = typer.Option(False,    "-t", "--thumb",           help="Save thumbnail image."),
    browser:  Optional[str] = typer.Option(None,     "-b", "--browser",         help=_browser_help),
    cookies:  Optional[str] = typer.Option(None,     "-c", "--cookies",         help=_cookies_help),
    auto_quality: bool      = typer.Option(False,    "-a", "--auto",            help="Use highest quality automatically."),
    no_banner:    bool      = typer.Option(False,    "--no-banner",             help="Skip banner."),
) -> None:
    """Download a single YouTube video."""
    if not no_banner:
        print_banner(__version__)

    assert_dependencies()
    cfg = load_config()

    if browser:   cfg.cookies_browser = browser
    if cookies:   cfg.cookies_file    = cookies
    
    if auto_quality:
        quality, fps = "best", "best"

    if quality is None:
        info("Fetching available video qualities…")
        choices = get_available_qualities(url, cfg.cookies_browser, cfg.cookies_file)
        quality = prompt_quality_selection(choices, cfg.default_quality or "best")

    # validate
    if quality not in QUALITY_CHOICES:
        error(f"Unknown quality '{quality}'. Choose from: {', '.join(QUALITY_CHOICES)}")
        raise typer.Exit(1)
    if fps not in FPS_CHOICES:
        error(f"Unknown fps '{fps}'. Choose from: {', '.join(FPS_CHOICES)}")
        raise typer.Exit(1)

    # detect playlist URL passed to `get`
    if url_is_playlist(url):
        warn("URL looks like a playlist. Use the [accent]playlist[/accent] command instead, or continue downloading first video.")
        if not confirm("Continue anyway?", default=False):
            raise typer.Exit(0)

    # fetch & display info
    info("Fetching video info…")
    try:
        vinfo = get_video_info(url, cfg.cookies_browser, cfg.cookies_file)
        print_video_info(vinfo)
    except Exception as exc:
        warn(f"Could not fetch metadata: {exc}")

    cfg.subtitles      = subs
    cfg.write_thumbnail = thumb

    mgr    = DownloadManager(cfg)
    result = mgr.download_video(url, output_dir=output, quality=quality, fps=fps)

    if result.status == "done":
        ok(f"Saved → [label]{result.filepath}[/label]")
    elif result.status == "error":
        error(f"Download failed: {result.error_msg}")
        raise typer.Exit(1)


# ── audio ─────────────────────────────────────────────────────────────────────

@app.command()
def audio(
    url:      str           = typer.Argument(..., help="YouTube URL."),
    fmt:      str           = typer.Option("mp3",  "-f", "--format",  help="Audio format: mp3, m4a, flac, wav, opus."),
    quality:  str           = typer.Option("0",    "-q", "--quality", help="Audio quality: 0 (best) – 9 (worst) for mp3 VBR."),
    output:   Optional[str] = typer.Option(None,   "-o", "--output",  help=_output_help),
    browser:  Optional[str] = typer.Option(None,   "-b", "--browser", help=_browser_help),
    cookies:  Optional[str] = typer.Option(None,   "-c", "--cookies", help=_cookies_help),
    thumb:    bool          = typer.Option(False,  "-t", "--thumb",   help="Embed thumbnail in audio file."),
    no_banner: bool         = typer.Option(False,  "--no-banner"),
) -> None:
    """Extract audio from a YouTube video (MP3 / FLAC / M4A / etc.)."""
    if not no_banner:
        print_banner(__version__)

    assert_dependencies()
    cfg = load_config()

    if browser:  cfg.cookies_browser = browser
    if cookies:  cfg.cookies_file    = cookies
    cfg.embed_thumbnail = thumb

    info("Fetching video info…")
    try:
        vinfo = get_video_info(url, cfg.cookies_browser, cfg.cookies_file)
        print_video_info(vinfo)
    except Exception as exc:
        warn(f"Metadata fetch failed: {exc}")

    mgr    = DownloadManager(cfg)
    result = mgr.download_audio(url, output_dir=output, audio_format=fmt, audio_quality=quality)

    if result.status == "done":
        ok(f"Audio saved → [label]{result.filepath or output or cfg.output_dir}[/label]")
    else:
        error(f"Audio download failed: {result.error_msg}")
        raise typer.Exit(1)


# ── playlist ──────────────────────────────────────────────────────────────────

@app.command()
def playlist(
    url:      str           = typer.Argument(..., help="YouTube playlist URL."),
    quality:  str           = typer.Option("best",  "-q", "--quality",   help=_quality_help),
    fps:      str           = typer.Option("best",  "-f", "--fps",        help=_fps_help),
    output:   Optional[str] = typer.Option(None,    "-o", "--output",     help=_output_help),
    browser:  Optional[str] = typer.Option(None,    "-b", "--browser",    help=_browser_help),
    cookies:  Optional[str] = typer.Option(None,    "-c", "--cookies",    help=_cookies_help),
    parallel: int           = typer.Option(1,       "-p", "--parallel",   help="Concurrent downloads (1-4)."),
    start:    int           = typer.Option(1,        "--start",            help="Start index (1-based)."),
    end:      Optional[int] = typer.Option(None,     "--end",              help="End index (inclusive)."),
    no_banner: bool         = typer.Option(False,   "--no-banner"),
) -> None:
    """Download an entire YouTube playlist."""
    if not no_banner:
        print_banner(__version__)

    assert_dependencies()
    cfg = load_config()

    if browser:  cfg.cookies_browser = browser
    if cookies:  cfg.cookies_file    = cookies

    parallel = max(1, min(parallel, 4))

    mgr     = DownloadManager(cfg)
    results = mgr.download_playlist(
        url, output_dir=output, quality=quality, fps=fps,
        parallel=parallel, start_index=start, end_index=end,
    )

    errors = [r for r in results if r.status == "error"]
    if errors:
        warn(f"{len(errors)} video(s) failed:")
        for r in errors[:5]:
            console.print(f"  [dim]·[/dim] [error]{r.title or r.url}[/error]")
            console.print(f"    [muted]{r.error_msg[:120]}[/muted]")


# ── formats ───────────────────────────────────────────────────────────────────

@app.command()
def formats(
    url:      str           = typer.Argument(..., help="YouTube URL."),
    browser:  Optional[str] = typer.Option(None, "-b", "--browser", help=_browser_help),
    cookies:  Optional[str] = typer.Option(None, "-c", "--cookies", help=_cookies_help),
    no_banner: bool         = typer.Option(False, "--no-banner"),
) -> None:
    """List all available download formats for a URL."""
    if not no_banner:
        print_banner(__version__)

    assert_dependencies()
    cfg = load_config()

    if browser:  cfg.cookies_browser = browser
    if cookies:  cfg.cookies_file    = cookies

    info("Fetching format list…")
    try:
        fmt_list = list_formats(url, cfg.cookies_browser, cfg.cookies_file)
    except Exception as exc:
        error(str(exc))
        raise typer.Exit(1)

    print_rule("available formats")
    print_formats_table(fmt_list)


# ── history ───────────────────────────────────────────────────────────────────

@app.command()
def history(
    limit:  int  = typer.Option(20,  "-n", "--limit", help="Number of entries to show."),
    clear:  bool = typer.Option(False, "--clear",      help="Wipe download history."),
    no_banner: bool = typer.Option(False, "--no-banner"),
) -> None:
    """Show or clear download history."""
    if not no_banner:
        print_banner(__version__)

    if clear:
        if confirm("Clear all download history?", default=False):
            clear_history()
            ok("History cleared.")
        return

    h = load_history()
    print_rule("download history")
    print_history_table(h, limit=limit)
    if len(h) > limit:
        info(f"{len(h) - limit} more entries — use --limit to show more.")


# ── config ────────────────────────────────────────────────────────────────────

@app.command(name="config")
def config_cmd(
    output_dir:     Optional[str] = typer.Option(None,  "--output-dir",       help="Default output directory."),
    quality:        Optional[str] = typer.Option(None,  "--quality",           help="Default quality."),
    fps:            Optional[str] = typer.Option(None,  "--fps",               help="Default fps."),
    browser:        Optional[str] = typer.Option(None,  "--browser",           help="Default cookie browser."),
    parallel:       Optional[int] = typer.Option(None,  "--parallel",          help="Default parallel download count."),
    retries:        Optional[int] = typer.Option(None,  "--retries",           help="Retry count."),
    subs:           Optional[bool]= typer.Option(None,  "--subs/--no-subs",    help="Download subtitles by default."),
    embed_thumb:    Optional[bool]= typer.Option(None,  "--embed-thumb/--no-embed-thumb"),
    sponsorblock:   Optional[str] = typer.Option(None,  "--sponsorblock",      help="Comma-separated SponsorBlock categories to remove."),
    reset:          bool          = typer.Option(False, "--reset",              help="Reset config to defaults."),
    show:           bool          = typer.Option(False, "--show",               help="Print current config."),
    no_banner:      bool          = typer.Option(False, "--no-banner"),
) -> None:
    """View or modify persistent configuration."""
    if not no_banner:
        print_banner(__version__)

    cfg = load_config()

    if reset:
        if confirm("Reset all config to defaults?", default=False):
            save_config(Config())
            ok("Config reset to defaults.")
        return

    # apply changes
    changed = False
    if output_dir:   cfg.output_dir         = output_dir;  changed = True
    if quality:      cfg.default_quality     = quality;     changed = True
    if fps:          cfg.default_fps         = fps;         changed = True
    if browser:      cfg.cookies_browser     = browser;     changed = True
    if parallel:     cfg.parallel_downloads  = parallel;    changed = True
    if retries:      cfg.retries             = retries;     changed = True
    if subs is not None:       cfg.subtitles         = subs;        changed = True
    if embed_thumb is not None: cfg.embed_thumbnail  = embed_thumb; changed = True
    if sponsorblock:
        cfg.sponsorblock_remove = [s.strip() for s in sponsorblock.split(",")]
        changed = True

    if changed:
        save_config(cfg)
        ok("Config saved.")

    print_rule("current config")
    print_config(cfg)


# ── update ────────────────────────────────────────────────────────────────────

@app.command()
def update(
    no_banner: bool = typer.Option(False, "--no-banner"),
) -> None:
    """Update yt-dlp to the latest version."""
    if not no_banner:
        print_banner(__version__)

    info("Checking for yt-dlp updates…")
    success, msg = update_ytdlp()
    if success:
        ok(msg)
    else:
        error(msg)
        raise typer.Exit(1)


# ── check ─────────────────────────────────────────────────────────────────────

@app.command()
def check(
    no_banner: bool = typer.Option(False, "--no-banner"),
) -> None:
    """Check that all required dependencies are installed and current."""
    if not no_banner:
        print_banner(__version__)

    ffmpeg_ok, ffmpeg_ver = check_ffmpeg()
    ytdlp_ok,  ytdlp_ver  = check_ytdlp()

    print_rule("dependency check")
    print_dependency_status(ffmpeg_ok, ffmpeg_ver, ytdlp_ok, ytdlp_ver)

    if ytdlp_ok:
        latest = check_for_updates(ytdlp_ver)
        if latest:
            warn(f"yt-dlp update available: [accent]{latest}[/accent]  →  run [label]ytdl update[/label]")
        else:
            ok("yt-dlp is up to date.")

    if not ffmpeg_ok or not ytdlp_ok:
        raise typer.Exit(1)


# ── batch ─────────────────────────────────────────────────────────────────────

@app.command()
def batch(
    file:     str           = typer.Argument(..., help="Path to a text file with one URL per line."),
    quality:  str           = typer.Option("best", "-q", "--quality", help=_quality_help),
    fps:      str           = typer.Option("best", "-f", "--fps",      help=_fps_help),
    output:   Optional[str] = typer.Option(None,   "-o", "--output",   help=_output_help),
    browser:  Optional[str] = typer.Option(None,   "-b", "--browser",  help=_browser_help),
    audio_only: bool        = typer.Option(False,  "-a", "--audio",    help="Download audio only."),
    no_banner: bool         = typer.Option(False,  "--no-banner"),
) -> None:
    """Batch download from a text file of URLs (one per line)."""
    if not no_banner:
        print_banner(__version__)

    assert_dependencies()
    cfg = load_config()

    if browser:  cfg.cookies_browser = browser

    p = Path(file)
    if not p.exists():
        error(f"File not found: {file}")
        raise typer.Exit(1)

    urls = [line.strip() for line in p.read_text().splitlines() if line.strip() and not line.startswith("#")]
    if not urls:
        warn("No URLs found in file.")
        raise typer.Exit(0)

    info(f"Loaded [label]{len(urls)}[/label] URLs from {file}")
    mgr = DownloadManager(cfg)

    results = []
    for i, url in enumerate(urls, 1):
        print_rule(f"{i}/{len(urls)}")
        if audio_only:
            r = mgr.download_audio(url, output_dir=output)
        else:
            r = mgr.download_video(url, output_dir=output, quality=quality, fps=fps)
        results.append(r)

    done   = sum(1 for r in results if r.status == "done")
    failed = sum(1 for r in results if r.status == "error")
    ok(f"Batch complete: [green]{done}[/green] done, [red]{failed}[/red] failed out of {len(urls)}")


# ── version ───────────────────────────────────────────────────────────────────

@app.command()
def version() -> None:
    """Print version information."""
    _, ytdlp_ver  = check_ytdlp()
    _, ffmpeg_ver = check_ffmpeg()
    console.print(f"\n  [accent]ytdl-cli[/accent]  [muted]v{__version__}[/muted]")
    console.print(f"  [muted]yt-dlp   {ytdlp_ver}[/muted]")
    console.print(f"  [muted]ffmpeg   {ffmpeg_ver or 'not found'}[/muted]\n")
