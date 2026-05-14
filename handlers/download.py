import logging

from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import Config
from database.db import Database
from keyboards.inline import music_results_keyboard, music_results_text, url_audio_keyboard
from services.cleanup import remove_file
from services.downloader import download_music, download_video, search_music
from services.responses import send_not_found
from services.sender import send_media_result
from utils.exceptions import DownloadError, DownloadLimitError, NoResultsError
from utils.texts import DOWNLOAD_FAILED_TEXT, INVALID_URL_TEXT, LIMIT_TEXT, NOT_FOUND_TEXT
from utils.validators import extract_url, get_supported_platform, is_supported_url

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text)
async def download_url_handler(message: Message, config: Config, db: Database, state: FSMContext) -> None:
    url = extract_url(message.text)
    if not url:
        if message.chat.type != ChatType.PRIVATE:
            return
        query = message.text.strip()
        if len(query) < 2:
            await message.answer("Havola yoki qo'shiq nomini yuboring.")
            return
        try:
            results = await search_music(query, config, limit=20)
            await state.update_data(music_results=[item.__dict__ for item in results], music_query=query)
            await message.answer(music_results_text(results, page=0), reply_markup=music_results_keyboard(results, page=0))
        except NoResultsError:
            await send_not_found(message, config)
        except DownloadError as exc:
            logger.exception("Text music search failed")
            await message.answer(DOWNLOAD_FAILED_TEXT)
            await db.record_error(message.from_user.id if message.from_user else None, type(exc).__name__, str(exc))
        return

    if not is_supported_url(url):
        await message.answer(INVALID_URL_TEXT)
        return

    result = None
    platform = get_supported_platform(url) or "Unknown"
    try:
        result = await download_video(url, config)
        await state.update_data(last_media_url=url, last_media_platform=platform)
        reply_markup = url_audio_keyboard() if result.media_type in {"video", "document"} else None
        await send_media_result(message, result, reply_markup=reply_markup)
        await db.record_download(
            user_id=message.from_user.id if message.from_user else None,
            source=result.source,
            media_type=result.media_type,
            success=True,
            title=result.title,
            file_size=result.file_size,
        )
    except DownloadLimitError:
        await message.answer(
            NOT_FOUND_TEXT + "\n\n" + LIMIT_TEXT.format(max_mb=config.max_file_mb, max_minutes=config.max_duration_seconds // 60)
        )
        await db.record_download(
            user_id=message.from_user.id if message.from_user else None,
            source=platform,
            media_type="media",
            success=False,
            error="limit",
        )
    except DownloadError as exc:
        logger.exception("Download failed")
        await send_not_found(message, config)
        await db.record_download(
            user_id=message.from_user.id if message.from_user else None,
            source=platform,
            media_type="media",
            success=False,
            error=str(exc)[:500],
        )
        await db.record_error(message.from_user.id if message.from_user else None, type(exc).__name__, str(exc))
    except TelegramAPIError as exc:
        logger.exception("Telegram refused the downloaded file")
        await message.answer("Fayl Telegram orqali yuborilmadi. Boshqa havola bilan urinib ko'ring.")
        await db.record_download(
            user_id=message.from_user.id if message.from_user else None,
            source=platform,
            media_type="media",
            success=False,
            error=str(exc)[:500],
        )
        await db.record_error(message.from_user.id if message.from_user else None, type(exc).__name__, str(exc))
    finally:
        if result:
            remove_file(result.path)


@router.callback_query(F.data == "url_audio")
async def download_url_audio(callback: CallbackQuery, config: Config, db: Database, state: FSMContext) -> None:
    data = await state.get_data()
    url = data.get("last_media_url")
    platform = data.get("last_media_platform") or "Media"
    if not url:
        await callback.answer("Havolani qayta yuboring", show_alert=True)
        return

    await callback.answer("Audio yuklanmoqda...")
    result = None
    try:
        result = await download_music(url, config, source=platform)
        await send_media_result(callback.message, result)
        await db.record_download(
            user_id=callback.from_user.id,
            source=platform,
            media_type="audio",
            success=True,
            title=result.title,
            file_size=result.file_size,
        )
    except DownloadLimitError:
        await callback.message.answer(NOT_FOUND_TEXT)
        await db.record_download(
            user_id=callback.from_user.id,
            source=platform,
            media_type="audio",
            success=False,
            error="limit",
        )
    except DownloadError as exc:
        logger.exception("URL audio download failed")
        await send_not_found(callback.message, config)
        await db.record_download(
            user_id=callback.from_user.id,
            source=platform,
            media_type="audio",
            success=False,
            error=str(exc)[:500],
        )
        await db.record_error(callback.from_user.id, type(exc).__name__, str(exc))
    except TelegramAPIError as exc:
        logger.exception("Telegram refused the audio file")
        await callback.message.answer("Audio Telegram orqali yuborilmadi. Boshqa havola bilan urinib ko'ring.")
        await db.record_error(callback.from_user.id, type(exc).__name__, str(exc))
    finally:
        if result:
            remove_file(result.path)
