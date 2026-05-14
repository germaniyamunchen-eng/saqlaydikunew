from __future__ import annotations

import asyncio
import logging
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError as YtdlpDownloadError

from config import Config
from utils.exceptions import DownloadError, DownloadLimitError, NoResultsError
from utils.validators import get_supported_platform, looks_like_playlist

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MediaResult:
    path: Path
    title: str
    source: str
    duration: int
    file_size: int
    media_type: str = "video"


@dataclass(frozen=True)
class SearchResult:
    id: str
    title: str
    url: str
    duration: int
    uploader: str | None = None


def _safe_filename(value: str) -> str:
    value = re.sub(r"[^\w\-. ]+", "", value, flags=re.UNICODE).strip()
    return value[:80] or "media"


def _estimate_size(info: dict[str, Any]) -> int:
    size = info.get("filesize") or info.get("filesize_approx")
    if size:
        return int(size)
    requested = info.get("requested_downloads") or []
    for item in requested:
        item_size = item.get("filesize") or item.get("filesize_approx")
        if item_size:
            return int(item_size)
    return 0


def _detect_media_type(path: Path, info: dict[str, Any]) -> str:
    extension = path.suffix.lower()
    if extension in {".jpg", ".jpeg", ".png", ".webp"}:
        return "photo"
    if extension in {".mp3", ".m4a", ".ogg", ".opus", ".wav", ".flac"}:
        return "audio"
    if info.get("vcodec") == "none":
        return "audio"
    if extension in {".mp4", ".mov", ".mkv", ".webm", ".avi"}:
        return "video"
    return "document"


def _check_limits(info: dict[str, Any], config: Config) -> None:
    duration = int(info.get("duration") or 0)
    if config.max_duration_seconds > 0 and duration and duration > config.max_duration_seconds:
        raise DownloadLimitError("Video duration exceeds limit")

    size = _estimate_size(info)
    if config.max_file_bytes > 0 and size and size > config.max_file_bytes:
        raise DownloadLimitError("File size exceeds limit")


def _base_options(config: Config, outtmpl: str | None = None) -> dict[str, Any]:
    options: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "restrictfilenames": True,
        "retries": 2,
        "socket_timeout": 25,
    }
    if outtmpl:
        options["outtmpl"] = outtmpl
    return options


def _download_video_sync(url: str, config: Config) -> MediaResult:
    if looks_like_playlist(url):
        raise DownloadLimitError("Playlist URLs are disabled")

    platform = get_supported_platform(url) or "Unknown"
    request_id = uuid.uuid4().hex
    output_template = str(config.download_dir / f"{request_id}.%(ext)s")

    with YoutubeDL(_base_options(config)) as ydl:
        info = ydl.extract_info(url, download=False)
        _check_limits(info, config)

    options = _base_options(config, output_template)
    if config.max_file_bytes > 0:
        format_selector = "best[filesize<={limit}]/best[filesize_approx<={limit}]/best".format(
            limit=config.max_file_bytes
        )
    else:
        format_selector = "bestvideo+bestaudio/best"
    options.update(
        {
            "format": format_selector,
            "merge_output_format": "mp4",
        }
    )

    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        _check_limits(info, config)
        prepared = Path(ydl.prepare_filename(info))
        candidates = sorted(config.download_dir.glob(f"{request_id}.*"))
        file_path = candidates[0] if candidates else prepared

    if not file_path.exists():
        raise DownloadError("Downloaded file was not found")

    file_size = file_path.stat().st_size
    if config.max_file_bytes > 0 and file_size > config.max_file_bytes:
        file_path.unlink(missing_ok=True)
        raise DownloadLimitError("Downloaded file exceeds limit")

    return MediaResult(
        path=file_path,
        title=info.get("title") or "Video",
        source=platform,
        duration=int(info.get("duration") or 0),
        file_size=file_size,
        media_type=_detect_media_type(file_path, info),
    )


def _search_music_sync(query: str, config: Config, limit: int = 5) -> list[SearchResult]:
    options = _base_options(config)
    options.update({"extract_flat": True, "default_search": "ytsearch"})

    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)

    entries = info.get("entries") or []
    results: list[SearchResult] = []
    for entry in entries:
        duration = int(entry.get("duration") or 0)
        if config.max_duration_seconds > 0 and duration and duration > config.max_duration_seconds:
            continue
        video_id = entry.get("id")
        url = entry.get("url") or entry.get("webpage_url")
        title = entry.get("title")
        if not video_id or not url or not title:
            continue
        if not str(url).startswith("http"):
            url = f"https://www.youtube.com/watch?v={video_id}"
        results.append(
            SearchResult(
                id=str(video_id),
                title=str(title),
                url=str(url),
                duration=duration,
                uploader=entry.get("uploader") or entry.get("channel"),
            )
        )
    if not results:
        raise NoResultsError("No music results found")
    return results


def _download_music_sync(url: str, config: Config, source: str = "YouTube") -> MediaResult:
    request_id = uuid.uuid4().hex
    output_template = str(config.download_dir / f"{request_id}.%(ext)s")
    options = _base_options(config, output_template)
    options.update(
        {
            "format": "bestaudio/best",
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }
    )

    with YoutubeDL(_base_options(config)) as ydl:
        info = ydl.extract_info(url, download=False)
        _check_limits(info, config)

    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
        _check_limits(info, config)
        prepared = Path(ydl.prepare_filename(info))
        file_path = prepared.with_suffix(".mp3")

    if not file_path.exists():
        candidates = sorted(config.download_dir.glob(f"{request_id}.*"))
        if not candidates:
            raise DownloadError("Downloaded audio was not found")
        file_path = candidates[0]

    file_size = file_path.stat().st_size
    if config.max_file_bytes > 0 and file_size > config.max_file_bytes:
        file_path.unlink(missing_ok=True)
        raise DownloadLimitError("Downloaded audio exceeds limit")

    return MediaResult(
        path=file_path,
        title=_safe_filename(info.get("title") or "Music"),
        source=source,
        duration=int(info.get("duration") or 0),
        file_size=file_size,
        media_type="audio",
    )


async def download_video(url: str, config: Config) -> MediaResult:
    try:
        return await asyncio.to_thread(_download_video_sync, url, config)
    except DownloadLimitError:
        raise
    except YtdlpDownloadError as exc:
        logger.exception("yt-dlp video download failed")
        raise DownloadError(str(exc)) from exc


async def search_music(query: str, config: Config, limit: int = 5) -> list[SearchResult]:
    try:
        return await asyncio.to_thread(_search_music_sync, query, config, limit)
    except NoResultsError:
        raise
    except YtdlpDownloadError as exc:
        logger.exception("yt-dlp music search failed")
        raise DownloadError(str(exc)) from exc


async def download_music(url: str, config: Config, source: str = "YouTube") -> MediaResult:
    try:
        return await asyncio.to_thread(_download_music_sync, url, config, source)
    except DownloadLimitError:
        raise
    except YtdlpDownloadError as exc:
        logger.exception("yt-dlp music download failed")
        raise DownloadError(str(exc)) from exc
