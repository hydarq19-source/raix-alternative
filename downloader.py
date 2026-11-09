#!/usr/bin/env python3
"""Authorized YouTube downloader using pip-installed yt-dlp and FFmpeg."""
from __future__ import annotations

import logging
import os
import random
from pathlib import Path
from urllib.parse import urlparse

import imageio_ffmpeg
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError

LOG = logging.getLogger("authorized-downloader")
ROOT = Path(__file__).resolve().parent
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtu.be"}


def load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE entries without requiring python-dotenv."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def is_youtube_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
        host = (parsed.hostname or "").lower().removeprefix("www.")
        return parsed.scheme in {"http", "https"} and host in {
            h.removeprefix("www.") for h in YOUTUBE_HOSTS
        }
    except ValueError:
        return False


def env_int(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}")
    return value


def progress_hook(event: dict) -> None:
    if event.get("status") == "downloading":
        percent = event.get("_percent_str", "?").strip()
        speed = event.get("_speed_str", "?").strip()
        eta = event.get("_eta", "?")
        print(f"\rDownloading: {percent} | {speed} | ETA {eta}s", end="", flush=True)
    elif event.get("status") == "finished":
        print("\nDownload stream finished; post-processing...", flush=True)


def available_qualities(info: dict) -> list[int]:
    heights: set[int] = set()
    for fmt in info.get("formats", []):
        height = fmt.get("height")
        if height and fmt.get("vcodec") not in {None, "none"}:
            heights.add(int(height))
    return sorted(heights)


def build_options(output_dir: Path, format_selector: str, ffmpeg_path: str) -> dict:
    return {
        "format": format_selector,
        "merge_output_format": os.getenv("MERGE_FORMAT", "mp4"),
        "ffmpeg_location": ffmpeg_path,
        "outtmpl": str(output_dir / "%(title).180B [%(id)s].%(ext)s"),
        "noplaylist": True,
        "retries": env_int("MAX_RETRIES", 3),
        "fragment_retries": env_int("MAX_RETRIES", 3),
        "socket_timeout": env_int("SOCKET_TIMEOUT", 30),
        "continuedl": True,
        "overwrites": False,
        "quiet": False,
        "restrictfilenames": True,
        "windowsfilenames": True,
        "logger": LOG,
        "progress_hooks": [progress_hook],
    }


def main() -> int:
    load_env_file(ROOT / ".env")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    url = os.getenv("VIDEO_URL", "").strip()
    if not url:
        LOG.error("VIDEO_URL is missing. Copy .env.example to .env and set it.")
        return 2
    if not is_youtube_url(url):
        LOG.error("Only YouTube URLs are accepted by this example.")
        return 2

    try:
        output_dir = Path(os.getenv("OUTPUT_DIR", "downloads")).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
        LOG.info("Output directory: %s", output_dir)
        LOG.info("Using FFmpeg supplied by imageio-ffmpeg: %s", ffmpeg_path)
        LOG.info("Downloading only content you own or are authorized to save.")

        initial_selector = os.getenv("FORMAT", "bestvideo*+bestaudio/best")
        with YoutubeDL(build_options(output_dir, initial_selector, ffmpeg_path)) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get("title") or info.get("id") or "video"
            qualities = available_qualities(info)
            if not qualities:
                LOG.error("No downloadable video qualities were reported.")
                return 1

            LOG.info("Selected: %s", title)
            LOG.info("Available qualities: %s", ", ".join(f"{q}p" for q in qualities))
            chosen_height = random.SystemRandom().choice(qualities)
            LOG.info("Randomly selected quality: %sp", chosen_height)
            ydl.params["format"] = (
                f"bestvideo[height={chosen_height}]+bestaudio/"
                f"best[height={chosen_height}]/best[height<={chosen_height}]"
            )
            ydl.download([url])
    except DownloadError as exc:
        LOG.error("yt-dlp failed: %s", exc)
        return 1
    except (OSError, ValueError, RuntimeError) as exc:
        LOG.error("%s", exc)
        return 1

    LOG.info("Finished successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
