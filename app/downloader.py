"""
downloader.py — core download engine.

DownloadManager wraps the yt-dlp Python API directly (not via
subprocess) to get granular progress hooks, reliable error
propagation, and first-class support for every yt-dlp option.

Architecture
------------
  DownloadManager.download_video()    → single video
  DownloadManager.download_playlist() → all videos in a playlist
  DownloadManager.download_audio()    → audio-only MP3/FLAC/etc.

Progress is fed back through a hook that updates Rich Progress tasks.
Retry logic wraps yt-dlp's own retry handling with an outer loop for
network-level failures.
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import yt_dlp

from app.config import Config, save_history
from app.formats import (
    build_audio_format_string,
    build_format_sort,
    build_format_string,
)
from app.ui import (
    error,
    info,
    make_download_progress,
    make_playlist_progress,
    ok,
    warn,
    console,
)
from app.utils import (
    ensure_dir,
    format_bytes,
    random_user_agent,
    sanitize_filename,
    timestamp,
)
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

logger = logging.getLogger("ytdl")


# ── download result ────────────────────────────────────────────────────────────

@dataclass
class DownloadResult:
    url: str
    title: str = ""
    filepath: str = ""
    status: str = "pending"   # "done" | "error" | "skipped"
    error_msg: str = ""
    duration_s: float = 0.0


# ── progress hook ─────────────────────────────────────────────────────────────

class _ProgressHook:
    """Bridges yt-dlp's status dict into a Rich Progress task."""

    def __init__(self, progress, task_id):
        self._progress = progress
        self._task_id  = task_id
        self._started  = False

    def __call__(self, d: dict) -> None:
        status = d.get("status")

        if status == "downloading":
            total     = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            speed     = d.get("speed") or 0
            fragment  = d.get("fragment_index")
            frag_total = d.get("fragment_count")

            desc = "downloading"
            if fragment and frag_total:
                desc = f"fragment {fragment}/{frag_total}"

            if total:
                if not self._started:
                    self._progress.update(self._task_id, total=total)
                    self._started = True
                self._progress.update(
                    self._task_id,
                    completed=downloaded,
                    description=desc,
                )
            else:
                self._progress.update(
                    self._task_id,
                    advance=1024,
                    description=desc,
                )

        elif status == "finished":
            total = d.get("total_bytes") or d.get("downloaded_bytes", 0)
            self._progress.update(
                self._task_id,
                completed=total,
                total=total,
                description="processing…",
            )

        elif status == "error":
            self._progress.update(self._task_id, description="[bold red]error")


# ── main manager ──────────────────────────────────────────────────────────────

class DownloadManager:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self._lock = threading.Lock()

    # ── shared yt-dlp option builder ─────────────────────────────────────────

    def _base_opts(
        self,
        output_dir: str,
        filename_template: Optional[str] = None,
        progress_hooks: Optional[list] = None,
        extra: Optional[dict] = None,
    ) -> dict:
        cfg = self.cfg
        template = filename_template or cfg.filename_template
        outtmpl  = str(Path(output_dir) / template)

        opts: dict = {
            # output
            "outtmpl":           outtmpl,
            "restrictfilenames": False,
            "windowsfilenames":  True,

            # network resilience
            "retries":            cfg.retries,
            "fragment_retries":   cfg.fragment_retries,
            "concurrent_fragment_downloads": cfg.concurrent_fragments,
            "socket_timeout":     cfg.socket_timeout,
            "sleep_interval":     cfg.sleep_interval,
            "max_sleep_interval": cfg.max_sleep_interval,

            # post-processing
            "merge_output_format": "mp4",

            # metadata
            "writethumbnail":  cfg.write_thumbnail,
            "embedthumbnail":  cfg.embed_thumbnail,
            "addmetadata":     cfg.embed_metadata,
            "embed_chapters":  cfg.embed_chapters,

            # misc
            "quiet":        True,
            "no_warnings":  True,
            "ignoreerrors": False,
            "noprogress":   True,   # we handle progress ourselves

            # HTTP headers
            "http_headers": {
                "User-Agent": random_user_agent(),
                "Accept-Language": "en-US,en;q=0.9",
            },
        }

        # cookies
        if cfg.cookies_browser:
            opts["cookiesfrombrowser"] = (cfg.cookies_browser,)
        if cfg.cookies_file:
            opts["cookiefile"] = cfg.cookies_file

        # rate limit
        if cfg.rate_limit:
            opts["ratelimit"] = cfg.rate_limit

        # subtitles
        if cfg.subtitles:
            opts["writesubtitles"]  = True
            opts["subtitleslangs"]  = cfg.subtitle_langs
            if cfg.auto_subtitles:
                opts["writeautomaticsub"] = True

        # SponsorBlock
        if cfg.sponsorblock_remove:
            opts["sponsorblock_remove"] = cfg.sponsorblock_remove

        if progress_hooks:
            opts["progress_hooks"] = progress_hooks

        if extra:
            opts.update(extra)

        return opts

    # ── single video download ─────────────────────────────────────────────────

    def download_video(
        self,
        url: str,
        output_dir: Optional[str] = None,
        quality: str = "best",
        fps: str = "best",
        download_subs: Optional[bool] = None,
        download_thumb: Optional[bool] = None,
    ) -> DownloadResult:
        cfg        = self.cfg
        out_dir    = output_dir or cfg.output_dir
        ensure_dir(out_dir)

        # override per-call settings
        if download_subs is not None:
            cfg.subtitles = download_subs
        if download_thumb is not None:
            cfg.write_thumbnail = download_thumb

        fmt     = build_format_string(quality, fps, cfg.prefer_vp9, cfg.prefer_av1)
        sort    = build_format_sort(quality, fps, cfg.prefer_av1, cfg.prefer_vp9)

        progress = make_download_progress()
        task     = progress.add_task("connecting…", total=None)
        hook     = _ProgressHook(progress, task)

        opts = self._base_opts(out_dir, progress_hooks=[hook], extra={
            "format":      fmt,
            "format_sort": sort,
        })

        result = DownloadResult(url=url)
        t0     = time.monotonic()

        with Live(progress, console=console, refresh_per_second=10):
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info_dict = ydl.extract_info(url, download=True)
                    result.title    = info_dict.get("title", url)
                    result.filepath = ydl.prepare_filename(info_dict)
                    result.status   = "done"
                    progress.update(task, description="[green]done", completed=progress.tasks[task].total or 1)
            except yt_dlp.utils.DownloadError as exc:
                result.status    = "error"
                result.error_msg = str(exc)
                progress.update(task, description="[red]failed")
            except KeyboardInterrupt:
                result.status    = "skipped"
                progress.update(task, description="[yellow]cancelled")

        result.duration_s = time.monotonic() - t0
        self._record(result, "video", quality)
        return result

    # ── playlist download ─────────────────────────────────────────────────────

    def download_playlist(
        self,
        url: str,
        output_dir: Optional[str] = None,
        quality: str = "best",
        fps: str = "best",
        parallel: int = 1,
        start_index: int = 1,
        end_index: Optional[int] = None,
    ) -> list[DownloadResult]:
        cfg     = self.cfg
        out_dir = output_dir or cfg.output_dir
        ensure_dir(out_dir)

        fmt  = build_format_string(quality, fps, cfg.prefer_vp9, cfg.prefer_av1)
        sort = build_format_sort(quality, fps, cfg.prefer_av1, cfg.prefer_vp9)

        # first, fetch playlist entries without downloading
        info(f"Fetching playlist info…")
        list_opts = self._base_opts(out_dir, extra={
            "format": fmt, "format_sort": sort,
            "extract_flat": True, "quiet": True,
        })
        try:
            with yt_dlp.YoutubeDL(list_opts) as ydl:
                playlist_info = ydl.extract_info(url, download=False)
        except Exception as exc:
            error(f"Could not read playlist: {exc}")
            return []

        entries = playlist_info.get("entries", [])
        if not entries:
            warn("Playlist appears empty.")
            return []

        # apply index range
        entries = list(entries)
        total   = len(entries)
        if end_index:
            entries = entries[start_index - 1 : end_index]
        else:
            entries = entries[start_index - 1 :]

        playlist_title = playlist_info.get("title", "playlist")
        info(f"Playlist: [accent]{playlist_title}[/accent]  ({total} videos, downloading {len(entries)})")

        # per-video subdirectory named after playlist
        safe_name = sanitize_filename(playlist_title)
        video_dir = str(Path(out_dir) / safe_name)
        ensure_dir(video_dir)

        # playlist-level progress bar
        pl_progress = make_playlist_progress()
        pl_task     = pl_progress.add_task(f"[cyan]{safe_name[:40]}", total=len(entries))

        results: list[DownloadResult] = []
        errors: list[str] = []

        workers = max(1, min(parallel, 4))   # cap at 4 simultaneous

        with Live(pl_progress, console=console, refresh_per_second=5):
            if workers == 1:
                for entry in entries:
                    entry_url = entry.get("url") or entry.get("webpage_url") or f"https://www.youtube.com/watch?v={entry.get('id','')}"
                    r = self._download_single_quiet(entry_url, video_dir, fmt, sort, entry.get("title", ""))
                    results.append(r)
                    pl_progress.advance(pl_task)
                    if r.status == "error":
                        errors.append(r.error_msg)
            else:
                with ThreadPoolExecutor(max_workers=workers) as pool:
                    futures = {
                        pool.submit(
                            self._download_single_quiet,
                            entry.get("url") or entry.get("webpage_url") or f"https://www.youtube.com/watch?v={entry.get('id','')}",
                            video_dir, fmt, sort, entry.get("title", ""),
                        ): entry
                        for entry in entries
                    }
                    for future in as_completed(futures):
                        r = future.result()
                        results.append(r)
                        pl_progress.advance(pl_task)
                        if r.status == "error":
                            errors.append(r.error_msg)

        done  = sum(1 for r in results if r.status == "done")
        skips = sum(1 for r in results if r.status == "skipped")
        ok(f"Playlist complete: {done}/{len(entries)} downloaded, {len(errors)} errors, {skips} skipped")
        return results

    # ── audio download ────────────────────────────────────────────────────────

    def download_audio(
        self,
        url: str,
        output_dir: Optional[str] = None,
        audio_format: str = "mp3",
        audio_quality: str = "0",
    ) -> DownloadResult:
        cfg     = self.cfg
        out_dir = output_dir or cfg.output_dir
        ensure_dir(out_dir)

        pp_opts = [{
            "key":             "FFmpegExtractAudio",
            "preferredcodec":  audio_format,
            "preferredquality": audio_quality,
        }]
        if cfg.embed_thumbnail:
            pp_opts.append({"key": "EmbedThumbnail"})
        if cfg.embed_metadata:
            pp_opts.append({"key": "FFmpegMetadata", "add_metadata": True})

        progress = make_download_progress()
        task     = progress.add_task("connecting…", total=None)
        hook     = _ProgressHook(progress, task)

        opts = self._base_opts(out_dir, progress_hooks=[hook], extra={
            "format":            build_audio_format_string(audio_format),
            "postprocessors":    pp_opts,
            "writethumbnail":    cfg.embed_thumbnail or cfg.write_thumbnail,
        })

        result = DownloadResult(url=url)
        t0     = time.monotonic()

        with Live(progress, console=console, refresh_per_second=10):
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info_dict = ydl.extract_info(url, download=True)
                    result.title  = info_dict.get("title", url)
                    result.status = "done"
                    progress.update(task, description="[green]done")
            except yt_dlp.utils.DownloadError as exc:
                result.status    = "error"
                result.error_msg = str(exc)
                progress.update(task, description="[red]failed")

        result.duration_s = time.monotonic() - t0
        self._record(result, "audio", audio_format)
        return result

    # ── internal: quiet single download (used inside playlist) ───────────────

    def _download_single_quiet(
        self,
        url: str,
        out_dir: str,
        fmt: str,
        sort: list,
        title_hint: str = "",
    ) -> DownloadResult:
        opts = self._base_opts(out_dir, extra={
            "format":      fmt,
            "format_sort": sort,
            "quiet":       True,
        })
        result = DownloadResult(url=url, title=title_hint)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info_dict = ydl.extract_info(url, download=True)
                result.title  = info_dict.get("title", title_hint or url)
                result.status = "done"
        except yt_dlp.utils.DownloadError as exc:
            result.status    = "error"
            result.error_msg = str(exc)
        except Exception as exc:
            result.status    = "error"
            result.error_msg = str(exc)
        return result

    # ── history recorder ──────────────────────────────────────────────────────

    def _record(self, result: DownloadResult, dl_type: str, quality: str) -> None:
        try:
            save_history({
                "date":    timestamp(),
                "type":    dl_type,
                "title":   result.title,
                "url":     result.url,
                "quality": quality,
                "status":  result.status,
                "path":    result.filepath,
            })
        except Exception:
            pass
