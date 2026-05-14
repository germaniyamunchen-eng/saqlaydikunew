from html import escape
from pathlib import Path

from aiogram.exceptions import TelegramAPIError
from aiogram.types import FSInputFile, InlineKeyboardMarkup, Message

from services.downloader import MediaResult
from utils.texts import BOT_SIGNATURE

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".ogg", ".opus", ".wav", ".flac"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}


def detect_media_type(path: Path, fallback: str = "document") -> str:
    extension = path.suffix.lower()
    if extension in IMAGE_EXTENSIONS:
        return "photo"
    if extension in AUDIO_EXTENSIONS:
        return "audio"
    if extension in VIDEO_EXTENSIONS:
        return "video"
    return fallback


async def send_media_result(
    message: Message,
    result: MediaResult,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    caption = f"<b>{escape(result.title)}</b>\n\nManba: {escape(result.source)}\n\n{BOT_SIGNATURE}"
    input_file = FSInputFile(result.path)
    media_type = result.media_type or detect_media_type(result.path)

    if media_type == "photo":
        try:
            await message.answer_photo(input_file, caption=caption, reply_markup=reply_markup)
        except TelegramAPIError:
            await message.answer_document(input_file, caption=caption, reply_markup=reply_markup)
        return
    if media_type == "audio":
        try:
            await message.answer_audio(input_file, caption=caption, title=result.title, reply_markup=reply_markup)
        except TelegramAPIError:
            await message.answer_document(input_file, caption=caption, reply_markup=reply_markup)
        return
    if media_type == "video":
        try:
            await message.answer_video(input_file, caption=caption, supports_streaming=True, reply_markup=reply_markup)
        except TelegramAPIError:
            await message.answer_document(input_file, caption=caption, reply_markup=reply_markup)
        return

    try:
        await message.answer_document(input_file, caption=caption, reply_markup=reply_markup)
    except TelegramAPIError:
        raise
