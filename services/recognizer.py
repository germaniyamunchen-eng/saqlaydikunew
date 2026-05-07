from __future__ import annotations

import asyncio
import logging
import shutil
import uuid
from dataclasses import dataclass
from pathlib import Path

from aiogram import Bot
from aiogram.types import Audio, Message, Video, VideoNote, Voice

from config import Config
from utils.exceptions import DownloadError, NoResultsError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RecognizedTrack:
    title: str
    artist: str
    query: str
    lyrics: str | None = None


def _extension_for_attachment(attachment: Audio | Voice | Video | VideoNote) -> str:
    if isinstance(attachment, Audio) and attachment.file_name:
        suffix = Path(attachment.file_name).suffix
        if suffix:
            return suffix
    if isinstance(attachment, Voice):
        return ".ogg"
    if isinstance(attachment, VideoNote):
        return ".mp4"
    return ".mp4"


def get_music_attachment(message: Message) -> Audio | Voice | Video | VideoNote | None:
    return message.audio or message.voice or message.video or message.video_note


async def download_attachment(bot: Bot, attachment: Audio | Voice | Video | VideoNote, config: Config) -> Path:
    config.download_dir.mkdir(parents=True, exist_ok=True)
    target = config.download_dir / f"recognize-{uuid.uuid4().hex}{_extension_for_attachment(attachment)}"
    file = await bot.get_file(attachment.file_id)
    await bot.download_file(file.file_path, destination=target)
    return target


async def recognize_track(path: Path) -> RecognizedTrack:
    prepared_path = await _prepare_audio(path)
    try:
        try:
            from shazamio import Shazam
        except ImportError as exc:
            raise DownloadError("shazamio is not installed") from exc

        shazam = Shazam()
        result = await shazam.recognize(str(prepared_path))
        track = result.get("track") or {}
        title = track.get("title")
        artist = track.get("subtitle")
        if not title or not artist:
            raise NoResultsError("Song was not recognized")

        return RecognizedTrack(
            title=str(title),
            artist=str(artist),
            query=f"{artist} {title}",
            lyrics=_extract_lyrics(track),
        )
    finally:
        if prepared_path != path:
            prepared_path.unlink(missing_ok=True)


async def _prepare_audio(path: Path) -> Path:
    if path.suffix.lower() in {".mp3", ".wav", ".m4a", ".ogg", ".opus"}:
        return path

    if not shutil.which("ffmpeg"):
        return path

    target = path.with_suffix(".mp3")
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(path),
        "-vn",
        "-t",
        "40",
        "-ac",
        "1",
        "-ar",
        "44100",
        str(target),
    ]
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    code = await process.wait()
    if code != 0 or not target.exists():
        logger.warning("ffmpeg conversion failed for recognition, using original file")
        return path
    return target


def _extract_lyrics(track: dict) -> str | None:
    for section in track.get("sections") or []:
        lines = section.get("text")
        if not lines:
            continue
        text = "\n".join(str(line) for line in lines if line)
        if text.strip():
            return text.strip()[:1200]
    return None
