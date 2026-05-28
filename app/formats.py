"""
formats.py — quality/fps mapping and format introspection.

Translates user-friendly strings like "1080p / 60fps" into
yt-dlp format selector expressions, and lists all available
formats for a given URL as a structured data structure.
"""

from __future__ import annotations

from typing import Optional

import yt_dlp

# ── quality → height mapping ──────────────────────────────────────────────────

QUALITY_HEIGHT: dict[str, int] = {
    "144p":  144,
    "240p":  240,
    "360p":  360,
    "480p":  480,
    "720p":  720,
    "1080p": 1080,
    "2K":    1440,
    "4K":    2160,
    "8K":    4320,
}

# ── codec preference order ────────────────────────────────────────────────────
# yt-dlp format sort keys: vcodec preference
# av01 > vp9.2 > vp9 > h265 > h264

_CODEC_SORT_DEFAULT = "vcodec:vp9.2,vp9,av01,h265,h264"

# ── build format selector ─────────────────────────────────────────────────────

def build_format_string(
    quality: str = "best",
    fps: str = "best",
    prefer_vp9: bool = True,
    prefer_av1: bool = False,
) -> str:
    """
    Return a yt-dlp format selector string.

    Examples
    --------
    build_format_string("1080p", "60")
      → "bestvideo[height<=1080][fps<=60]+bestaudio/best[height<=1080]"
    build_format_string("best", "best")
      → "bestvideo+bestaudio/best"
    """
    if quality == "best":
        height_filter = ""
    else:
        h = QUALITY_HEIGHT.get(quality)
        height_filter = f"[height<={h}]" if h else ""

    if fps == "best":
        fps_filter = ""
    else:
        fps_filter = f"[fps<={fps}]"

    combo_filter = height_filter + fps_filter

    if combo_filter:
        return (
            f"bestvideo{combo_filter}[ext=mp4]+bestaudio[ext=m4a]/"
            f"bestvideo{combo_filter}+bestaudio/"
            f"best{combo_filter}/"
            "best"
        )
    return "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"


def build_audio_format_string(audio_format: str = "mp3") -> str:
    return "bestaudio/best"


# ── format sort keys ──────────────────────────────────────────────────────────

def build_format_sort(
    quality: str = "best",
    fps: str = "best",
    prefer_av1: bool = False,
    prefer_vp9: bool = True,
) -> list[str]:
    """Return yt-dlp format_sort list."""
    sort: list[str] = []

    if quality != "best":
        h = QUALITY_HEIGHT.get(quality, 0)
        sort.append(f"res:{h}")

    if fps != "best":
        sort.append(f"fps:{fps}")

    if prefer_av1:
        sort.append("vcodec:av01,vp9.2,vp9,h265,h264")
    elif prefer_vp9:
        sort.append("vcodec:vp9.2,vp9,av01,h265,h264")
    else:
        sort.append("vcodec:h264,h265,vp9.2,vp9,av01")

    sort.extend(["acodec:opus,aac,mp3", "br", "size"])
    return sort


# ── list available formats ────────────────────────────────────────────────────

def list_formats(url: str, cookies_browser: Optional[str] = None, cookies_file: Optional[str] = None) -> list[dict]:
    """
    Fetch available formats for a URL via yt-dlp.
    Returns a list of dicts with keys:
      format_id, ext, resolution, fps, vcodec, acodec, filesize, tbr, note
    """
    ydl_opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "ignoreerrors": False,
    }
    if cookies_browser:
        ydl_opts["cookiesfrombrowser"] = (cookies_browser,)
    if cookies_file:
        ydl_opts["cookiefile"] = cookies_file

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        raise RuntimeError(f"Could not fetch formats: {exc}") from exc

    raw_formats = info.get("formats", [])
    result = []
    for f in raw_formats:
        fps_val = f.get("fps")
        result.append({
            "format_id": f.get("format_id", "?"),
            "ext":        f.get("ext", "?"),
            "resolution": f.get("resolution") or _resolution_label(f),
            "fps":        int(fps_val) if fps_val else None,
            "vcodec":     _short_codec(f.get("vcodec", "none")),
            "acodec":     _short_codec(f.get("acodec", "none")),
            "filesize":   f.get("filesize") or f.get("filesize_approx"),
            "tbr":        f.get("tbr"),
            "note":       f.get("format_note", ""),
        })

    # sort: video-only / audio-video first, then audio-only
    result.sort(key=_format_sort_key)
    return result


def get_video_info(url: str, cookies_browser: Optional[str] = None, cookies_file: Optional[str] = None) -> dict:
    """Return lightweight metadata dict (title, uploader, duration, etc.)."""
    ydl_opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "ignoreerrors": False,
    }
    if cookies_browser:
        ydl_opts["cookiesfrombrowser"] = (cookies_browser,)
    if cookies_file:
        ydl_opts["cookiefile"] = cookies_file

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    entries = info.get("entries")
    if entries:
        count = len(list(entries)) if not isinstance(entries, list) else len(entries)
        return {
            "type": "playlist",
            "title": info.get("title", "Unknown Playlist"),
            "uploader": info.get("uploader", "?"),
            "count": count,
        }

    return {
        "type": "video",
        "title": info.get("title", "Unknown"),
        "uploader": info.get("uploader", "?"),
        "duration": info.get("duration"),
        "view_count": info.get("view_count"),
        "upload_date": info.get("upload_date"),
        "is_live": info.get("is_live", False),
        "age_limit": info.get("age_limit", 0),
    }


# ── internal helpers ──────────────────────────────────────────────────────────

def _resolution_label(f: dict) -> str:
    w = f.get("width")
    h = f.get("height")
    if w and h:
        return f"{w}x{h}"
    if h:
        return f"{h}p"
    return "audio only"


def _short_codec(codec: str) -> str:
    if not codec or codec == "none":
        return "—"
    # truncate dotted strings: "vp9.2" → "vp9.2", "avc1.640028" → "h264"
    mapping = {
        "avc1": "h264", "avc3": "h264",
        "hev1": "h265", "hvc1": "h265",
        "av01": "av1",
        "mp4a": "aac",
        "opus": "opus",
    }
    prefix = codec.split(".")[0].lower()
    return mapping.get(prefix, prefix)


def _format_sort_key(f: dict) -> tuple:
    res = f.get("resolution", "audio only")
    is_audio_only = res == "audio only"
    # extract height for numeric sort
    try:
        h = int(res.split("x")[-1].replace("p", ""))
    except Exception:
        h = 0
    return (is_audio_only, -h, -(f.get("tbr") or 0))
