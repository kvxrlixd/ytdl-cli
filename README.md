# ytdl-cli

> Terminal-based YouTube downloader. Fast, scriptable, hacker-clean.

```
 __  _____ ____  _           ____ _     ___
 \ \/ / __/ __ \| |         / ___| |   |_ _|
  \  /\__ \ | | | |   ___  | |   | |    | |
  /  \___/ |_| | |__/___/  | |___| |___ | |
 /_/\_\____\____/_____|      \____|_____|___|

  yt-dlp powered YouTube downloader  ·  v1.0.0
```

Powered by **[yt-dlp](https://github.com/yt-dlp/yt-dlp)** and **[Rich](https://github.com/Textualize/rich)**.
Works on macOS, Windows, and Linux.

---

## Features

| Feature | Detail |
|---|---|
| Video download | Single videos, playlists, batch URLs |
| Audio extraction | MP3, M4A, FLAC, WAV, Opus |
| Quality selector | 144p → 8K, plus auto-best |
| FPS selector | 30fps, 60fps, or highest available |
| Format listing | View every available stream before downloading |
| Subtitles | Auto and manual, per-language, embedded or sidecar |
| Thumbnails | Embed into file or save as image |
| Progress display | Live speed, ETA, bar, downloaded/total |
| Retry logic | Configurable retries + fragment retries |
| Cookie import | Chrome, Firefox, Edge, Brave, Opera, Safari |
| Cookies file | Netscape-format `cookies.txt` support |
| Batch download | Text file of URLs, one per line |
| Parallel playlist | Up to 4 concurrent downloads |
| Resume | Interrupted downloads resume automatically |
| SponsorBlock | Remove sponsor segments via yt-dlp integration |
| Config file | Persistent settings in `~/.ytdl/config.toml` |
| Download history | Searchable JSON log at `~/.ytdl/history.json` |
| Self-update | `ytdl update` upgrades yt-dlp in place |

---

## Quick Start

```bash
git clone https://github.com/kvxrlixd/ytdl-cli
cd ytdl-cli
python run.py
```

First launch automatically installs missing Python packages.

Then download instantly:

```bash
python run.py get "https://youtube.com/watch?v=..."
```

The CLI now asks for video quality before every download.


---

## Installation

### Prerequisites

#### Python
Python 3.9 or newer. Check with:
```bash
python --version
```

#### ffmpeg

**macOS**
```bash
brew install ffmpeg
```

**Ubuntu / Debian**
```bash
sudo apt update && sudo apt install ffmpeg
```

**Fedora / RHEL**
```bash
sudo dnf install ffmpeg
```

**Windows**

1. Download a build from <https://ffmpeg.org/download.html> (recommend the **gyan.dev full build**).
2. Extract the archive.
3. Copy `ffmpeg.exe`, `ffprobe.exe`, and `ffplay.exe` to a folder already in `PATH` (e.g. `C:\Windows\System32`) — or add the `bin` folder to your `PATH` environment variable.
4. Verify: open a new terminal and run `ffmpeg -version`.

---

### Install the project

```bash
git clone https://github.com/kvxrlixd/ytdl-cli
cd ytdl-cli

# recommended: create a virtual environment first
python -m venv .venv

# activate — Linux/macOS:
source .venv/bin/activate
# activate — Windows (PowerShell):
.venv\Scripts\Activate.ps1
# activate — Windows (cmd):
.venv\Scripts\activate.bat

pip install -r requirements.txt
```

### Optional: install as a system command

```bash
pip install -e .
# now available everywhere as:
ytdl get "URL"
```

---

## Usage

All commands are available via `python run.py` or `ytdl` (if installed).

### Download a video

```bash
# best available quality
python run.py get "https://youtube.com/watch?v=..."

# specific quality
python run.py get "https://youtube.com/watch?v=..." -q 1080p

# 1080p at 60fps
python run.py get "https://youtube.com/watch?v=..." -q 1080p -f 60

# custom output folder
python run.py get "URL" -q 4K -o ~/Videos
```

### Download audio (MP3)

```bash
python run.py audio "URL"

# specify format
python run.py audio "URL" -f mp3
python run.py audio "URL" -f flac
python run.py audio "URL" -f m4a

# embed thumbnail
python run.py audio "URL" -f mp3 --thumb
```

### Download a playlist

```bash
python run.py playlist "https://youtube.com/playlist?list=..."

# 1080p, 2 parallel downloads
python run.py playlist "URL" -q 1080p -p 2

# only videos 5 through 20
python run.py playlist "URL" --start 5 --end 20
```

### List available formats

```bash
python run.py formats "URL"
```

Example output:
```
  id       ext    resolution    fps    vcodec    acodec    size        bitrate    note
 ──────────────────────────────────────────────────────────────────────────────────────
  400      mp4    7680x4320     30     vp9       —         12.4 GB     48000k     8K
  401      mp4    3840x2160     30     vp9       —          4.1 GB     18000k     4K
  137      mp4    1920x1080     30     h264      —          1.2 GB      4000k     1080p
  248      webm   1920x1080     30     vp9.2     —          900 MB      3000k     1080p
  136      mp4    1280x720      30     h264      —          600 MB      2000k     720p
  ...
  140      m4a    audio only    —      —         aac         48 MB       129k     m4a
  251      webm   audio only    —      —         opus        30 MB        80k     webm
```

### Batch download

Create a `urls.txt` file:
```
https://www.youtube.com/watch?v=VIDEO_1
https://www.youtube.com/watch?v=VIDEO_2
# lines starting with # are ignored
https://www.youtube.com/watch?v=VIDEO_3
```

Then:
```bash
python run.py batch urls.txt -q 720p

# audio only batch
python run.py batch urls.txt --audio
```

### Subtitles

```bash
# download English subtitles
python run.py get "URL" --subs

# configure default subtitle language
python run.py config --subs
```

To change languages, edit `~/.ytdl/config.toml`:
```toml
subtitles = true
subtitle_langs = ["en", "fr", "de"]
auto_subtitles = false
```

### Thumbnail

```bash
# save thumbnail as image file alongside video
python run.py get "URL" --thumb

# embed thumbnail into file (video or audio)
python run.py config --embed-thumb
```

### Cookie import (bypass bot detection)

**From browser (recommended)**
```bash
# Chrome
python run.py get "URL" -b chrome

# Firefox
python run.py get "URL" -b firefox

# Edge, Brave, Opera, Safari also supported
python run.py get "URL" -b edge
```

Set a default browser in config so you don't need to pass `-b` every time:
```bash
python run.py config --browser chrome
```

**From cookies file**
Export cookies from your browser using a browser extension such as *Get cookies.txt LOCALLY*, save as `cookies.txt`, then:
```bash
python run.py get "URL" -c /path/to/cookies.txt
```

### Age-restricted videos

Age-restricted videos require a signed-in session. Use cookie import:
```bash
python run.py get "URL" -b chrome
```
Make sure you are logged into YouTube in that browser.

---

## Configuration

Config is stored at `~/.ytdl/config.toml`.
Run `python run.py config --show` to see all current values.

```bash
# set default output directory
python run.py config --output-dir ~/Videos/YouTube

# set default quality
python run.py config --quality 1080p

# set default fps
python run.py config --fps 60

# enable subtitles globally
python run.py config --subs

# set default cookie browser
python run.py config --browser chrome

# change retry count
python run.py config --retries 15

# remove SponsorBlock categories (comma-separated)
python run.py config --sponsorblock sponsor,intro,outro

# reset everything to defaults
python run.py config --reset
```

Full config reference (`~/.ytdl/config.toml`):

```toml
output_dir          = "/home/you/Downloads/ytdl"
filename_template   = "%(uploader)s - %(title)s [%(id)s].%(ext)s"
default_quality     = "1080p"
default_fps         = "best"
prefer_av1          = false
prefer_vp9          = true
audio_format        = "mp3"
audio_quality       = "0"
subtitles           = false
subtitle_langs      = ["en"]
auto_subtitles      = false
embed_thumbnail     = false
write_thumbnail     = false
retries             = 10
fragment_retries    = 10
concurrent_fragments = 4
rate_limit          = ""         # e.g. "2M" to cap at 2 MB/s
sleep_interval      = 1
max_sleep_interval  = 5
socket_timeout      = 30
cookies_browser     = ""         # "chrome" | "firefox" | "edge" | ...
cookies_file        = ""         # path to cookies.txt
parallel_downloads  = 1
embed_metadata      = true
embed_chapters      = true
sponsorblock_remove = []
auto_update_ytdlp   = true
no_color            = false
quiet               = false
```

---

## Download History

History is stored at `~/.ytdl/history.json`.

```bash
# show last 20 downloads
python run.py history

# show last 50
python run.py history -n 50

# clear all history
python run.py history --clear
```

---

## Quality Reference

| Flag | Resolution | Notes |
|---|---|---|
| `144p` | 256×144 | Mobile data saver |
| `240p` | 426×240 | |
| `360p` | 640×360 | Standard SD |
| `480p` | 854×480 | SD |
| `720p` | 1280×720 | HD |
| `1080p` | 1920×1080 | Full HD |
| `2K` | 2560×1440 | Quad HD |
| `4K` | 3840×2160 | Ultra HD |
| `8K` | 7680×4320 | Requires capable source |
| `best` | highest available | Default |

---

## Rate Limiting & Throttling

YouTube may throttle download speeds. ytdl-cli handles this via:

- yt-dlp's built-in throttle detection and workaround
- Automatic retries with exponential back-off
- Fragment-based downloading with retry on fragment failure
- Rotating User-Agent strings

If you are still hitting limits, try:

1. Importing cookies from a logged-in browser (`-b chrome`)
2. Adding a small sleep between requests in config:
   ```toml
   sleep_interval     = 2
   max_sleep_interval = 8
   ```
3. Capping your download rate to appear more organic:
   ```toml
   rate_limit = "2M"
   ```

---

## Troubleshooting

**`ffmpeg not found`**
→ Install ffmpeg and make sure it is in your `PATH`. Run `ffmpeg -version` to confirm.

**`yt-dlp not found`**
→ Run `pip install yt-dlp` or `pip install -r requirements.txt`.

**`ERROR: Sign in to confirm your age`**
→ Use cookie import: `python run.py get "URL" -b chrome`

**`HTTP Error 429: Too Many Requests`**
→ Wait a few minutes, then retry. Enable cookie import and/or set a `rate_limit` in config.

**`Requested format is not available`**
→ Run `python run.py formats "URL"` to see what is actually available for that video. The requested quality may not exist.

**`Merge failed / ffmpeg error`**
→ Confirm ffmpeg works: `ffmpeg -version`. On Windows, make sure `ffprobe.exe` is also in PATH alongside `ffmpeg.exe`.

**`No space left on device`**
→ Change output directory: `python run.py config --output-dir /path/with/space`

**Download is slow**
→ Try `--quality 720p` or lower if you don't need the highest resolution. Alternatively, increase `concurrent_fragments` in config (default: 4).

**Playlist stops mid-way**
→ Use `--start N` to resume from the last successful video index.

---

## Dependency Management

```bash
# check dependency status
python run.py check

# update yt-dlp (keeps up with YouTube changes)
python run.py update

# print version info
python run.py version
```

It is recommended to update yt-dlp regularly since YouTube frequently changes
its internal API and yt-dlp releases patches to keep up.

---

## Building a Standalone Executable

Uses **PyInstaller**. Install it first:
```bash
pip install pyinstaller
```

### Linux / macOS

```bash
pyinstaller \
  --onefile \
  --name ytdl \
  --add-data "app:app" \
  run.py
```

The executable will be at `dist/ytdl`. Copy it anywhere in your `PATH`:
```bash
sudo cp dist/ytdl /usr/local/bin/ytdl
```

### Windows

Run in a Command Prompt or PowerShell inside the project directory:
```bat
pyinstaller ^
  --onefile ^
  --name ytdl ^
  --add-data "app;app" ^
  --icon assets\icon.ico ^
  run.py
```

The executable will be at `dist\ytdl.exe`.

### macOS .app bundle

```bash
pyinstaller \
  --windowed \
  --onefile \
  --name ytdl \
  --add-data "app:app" \
  run.py
```

> **Note:** PyInstaller bundles Python but not ffmpeg. Distribute ffmpeg
> separately or document that users must install it. On macOS you can bundle
> ffmpeg into the `.app` by adding:
> `--add-binary "$(which ffmpeg):."` to the PyInstaller command.

---

## Project Layout

```
ytdl-cli/
│
├── app/
│   ├── __init__.py      Package metadata and version string
│   ├── cli.py           Typer commands (get, audio, playlist, formats, batch, history, config, update, check)
│   ├── downloader.py    DownloadManager — yt-dlp wrappers, progress hooks, retry logic
│   ├── formats.py       Quality/FPS mapping, format selector builder, format list fetcher
│   ├── ui.py            All Rich terminal rendering (progress bars, tables, panels, prompts)
│   ├── utils.py         Dependency checks, filename sanitizer, size/speed formatters, user-agent pool
│   └── config.py        Persistent config (~/.ytdl/config.toml) and history (~/.ytdl/history.json)
│
├── downloads/           Default output directory (git-tracked, contents ignored)
├── assets/              Icons and other static assets for builds
│
├── requirements.txt     Runtime dependencies (pip install -r requirements.txt)
├── pyproject.toml       PEP 517/518 build config, project metadata, tool config
├── setup.py             Legacy pip compatibility shim
├── run.py               Entry point — dependency check, logging init, CLI dispatch
├── README.md            This file
├── .gitignore
└── LICENSE              MIT
```

---

## Command Reference

```
python run.py [COMMAND] [OPTIONS] [ARGS]

Commands:
  get        Download a single video
  audio      Extract audio (mp3/flac/m4a/wav/opus)
  playlist   Download a full playlist
  formats    List available formats for a URL
  batch      Batch download from a file of URLs
  history    Show / clear download history
  config     View / edit persistent configuration
  update     Update yt-dlp to latest version
  check      Verify dependencies
  version    Print version information

get options:
  URL                     YouTube URL (required)
  -q, --quality TEXT      144p/240p/360p/480p/720p/1080p/2K/4K/8K/best
  -f, --fps TEXT          30/60/best
  -o, --output TEXT       Output directory
  -s, --subs              Download subtitles
  -t, --thumb             Save thumbnail
  -b, --browser TEXT      Cookie browser (chrome/firefox/edge/brave/...)
  -c, --cookies TEXT      Path to cookies.txt
  -a, --auto              Use best quality automatically

audio options:
  URL
  -f, --format TEXT       mp3/m4a/flac/wav/opus  [default: mp3]
  -q, --quality TEXT      VBR quality 0 (best) to 9 (worst)  [default: 0]
  -o, --output TEXT
  -b, --browser TEXT
  -c, --cookies TEXT
  -t, --thumb             Embed thumbnail

playlist options:
  URL
  -q, --quality TEXT
  -f, --fps TEXT
  -o, --output TEXT
  -p, --parallel INT      1–4 concurrent downloads  [default: 1]
  --start INT             Start index (1-based)  [default: 1]
  --end INT               End index (inclusive)
  -b, --browser TEXT
  -c, --cookies TEXT

batch options:
  FILE                    Path to text file with one URL per line
  -q, --quality TEXT
  -f, --fps TEXT
  -o, --output TEXT
  -a, --audio             Audio-only batch
  -b, --browser TEXT
```

---

## Contributing

Pull requests are welcome. For major changes please open an issue first.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m 'add my feature'`
4. Push to the branch: `git push origin feature/my-feature`
5. Open a pull request

Please run `ruff check .` and `black --check .` before submitting.

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

## Legal

This tool is intended for downloading content you have the right to download
(your own uploads, Creative Commons content, or content explicitly permitted
by the rights holder). Respect the YouTube Terms of Service and applicable
copyright law in your jurisdiction.
