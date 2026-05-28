# ytdl-cli

> Terminal-based YouTube downloader. Fast, clean, minimal.



Powered by yt-dlp.

---

# Quick Start

```bash
git clone https://github.com/kvxrlixd/ytdl-cli.git
cd ytdl-cli
python3 run.py
```

That's it.

Dependencies install automatically on first launch.

---

# Download Video

```bash
python3 run.py get "YOUTUBE_URL"
```

Example:

```bash
python3 run.py get "https://youtube.com/watch?v=dQw4w9WgXcQ"
```

The CLI asks for quality before every download.

---

# Download Audio

```bash
python3 run.py audio "URL"
```

---

# Playlist Download

```bash
python3 run.py playlist "URL"
```

---

# Show Available Formats

```bash
python3 run.py formats "URL"
```

---

# Features

* Video downloads
* Audio extraction
* Playlist downloads
* Interactive quality selector
* Auto dependency installer
* ffmpeg support
* Subtitle support
* Thumbnail embedding
* Browser cookie import
* Download history
* Batch downloads
* SponsorBlock support
* Retry logic
* Parallel downloads
* Clean terminal UI

---

# Commands

## Video

```bash
python3 run.py get "URL"
```

Specific quality:

```bash
python3 run.py get "URL" -q 1080p
```

60 FPS:

```bash
python3 run.py get "URL" -q 1080p -f 60
```

---

## Audio

```bash
python3 run.py audio "URL"
```

MP3:

```bash
python3 run.py audio "URL" -f mp3
```

FLAC:

```bash
python3 run.py audio "URL" -f flac
```

---

## Playlist

```bash
python3 run.py playlist "URL"
```

Parallel downloads:

```bash
python3 run.py playlist "URL" -p 2
```

---

## Formats

```bash
python3 run.py formats "URL"
```

---

## Batch Download

Create `urls.txt`

```text
https://youtube.com/watch?v=VIDEO1
https://youtube.com/watch?v=VIDEO2
```

Run:

```bash
python3 run.py batch urls.txt
```

---

# Cookies / Browser Import

Chrome:

```bash
python3 run.py get "URL" -b chrome
```

Firefox:

```bash
python3 run.py get "URL" -b firefox
```

Cookies file:

```bash
python3 run.py get "URL" -c cookies.txt
```

---

# Config

Show config:

```bash
python3 run.py config --show
```

Set default quality:

```bash
python3 run.py config --quality 1080p
```

Set output folder:

```bash
python3 run.py config --output-dir ~/Videos
```

---

# History

Show history:

```bash
python3 run.py history
```

Clear history:

```bash
python3 run.py history --clear
```

---

# Dependency Management

Check dependencies:

```bash
python3 run.py check
```

Update yt-dlp:

```bash
python3 run.py update
```

Version:

```bash
python3 run.py version
```

---

# ffmpeg

ffmpeg is required for merging audio/video and audio extraction.

Ubuntu / Debian:

```bash
sudo apt install ffmpeg
```

Arch Linux:

```bash
sudo pacman -S ffmpeg
```

Fedora:

```bash
sudo dnf install ffmpeg
```

macOS:

```bash
brew install ffmpeg
```

---

# Example

```bash
python3 run.py get "https://youtube.com/watch?v=dQw4w9WgXcQ" -q 1080p
```

---

# License

MIT
