#!/usr/bin/env python3
"""Portable authorized YouTube downloader using bundled yt-dlp and ffmpeg."""
from __future__ import annotations

import json
import logging
import os
import random
import subprocess
from pathlib import Path
from urllib.parse import urlparse

LOG = logging.getLogger("authorized-downloader")
ROOT = Path(__file__).resolve().parent
BIN_DIR = ROOT / "bin"
YTDLP = BIN_DIR / ("yt-dlp.exe" if os.name == "nt" else "yt-dlp")
FFMPEG = BIN_DIR / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "www.youtu.be"}


def load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE entries without requiring external packages."""
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


def check_bundled_tools() -> None:
    missing = [str(path.relative_to(ROOT)) for path in (YTDLP, FFMPEG) if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing bundled tools: " + ", ".join(missing))
    if os.name != "nt":
        for path in (YTDLP, FFMPEG):
            if not os.access(path, os.X_OK):
                raise PermissionError(f"Tool is not executable: {path}")


def read_video_info(url: str) -> dict:
    command = [str(YTDLP), "--dump-single-json", "--no-warnings", "--no-playlist", url]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "yt-dlp could not inspect the URL")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("yt-dlp returned invalid metadata") from exc


def available_qualities(info: dict) -> list[int]:
    heights: set[int] = set()
    for fmt in info.get("formats", []):
        height = fmt.get("height")
        if height and fmt.get("vcodec") not in {None, "none"}:
            heights.add(int(height))
    return sorted(heights)


def quality_label(height: int) -> str:
    return f"{height}p"


def download(url: str, output_dir: Path, height: int) -> None:
    selector = (
        f"bestvideo[height={height}]+bestaudio/"
        f"best[height={height}]/best[height<={height}]"
    )
    command = [
        str(YTDLP),
        "--no-playlist",
        "--format", selector,
        "--merge-output-format", os.getenv("MERGE_FORMAT", "mp4"),
        "--ffmpeg-location", str(BIN_DIR),
        "--output", str(output_dir / "%(title).180B [%(id)s].%(ext)s"),
        "--retries", str(env_int("MAX_RETRIES", 3)),
        "--fragment-retries", str(env_int("MAX_RETRIES", 3)),
        "--socket-timeout", str(env_int("SOCKET_TIMEOUT", 30)),
        "--continue",
        "--no-overwrites",
        "--restrict-filenames",
        "--windows-filenames",
        "--newline",
        url,
    ]
    LOG.info("Using bundled yt-dlp: %s", YTDLP)
    LOG.info("Using bundled ffmpeg: %s", FFMPEG)
    result = subprocess.run(command, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp download failed with exit code {result.returncode}")


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
        check_bundled_tools()
        output_dir = Path(os.getenv("OUTPUT_DIR", "downloads")).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        LOG.info("Output directory: %s", output_dir)
        LOG.info("Downloading only content you own or are authorized to save.")

        info = read_video_info(url)
        title = info.get("title") or info.get("id") or "video"
        qualities = available_qualities(info)
        if not qualities:
            LOG.error("No downloadable video qualities were reported.")
            return 1

        LOG.info("Selected: %s", title)
        LOG.info("Available qualities: %s", ", ".join(quality_label(q) for q in qualities))
        chosen_height = random.SystemRandom().choice(qualities)
        LOG.info("Randomly selected quality: %s", quality_label(chosen_height))
        download(url, output_dir, chosen_height)
    except (OSError, ValueError, RuntimeError) as exc:
        LOG.error("%s", exc)
        return 1

    LOG.info("Finished successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
