import logging
from contextlib import suppress
from html import escape

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from config import Config
from database.db import Database
from keyboards.inline import main_keyboard, music_results_keyboard, music_results_text
from services.cleanup import remove_file
from services.downloader import download_music, search_music
from services.recognizer import download_attachment, get_music_attachment, recognize_track
from services.responses import send_not_found
from states import MusicStates
from utils.exceptions import DownloadError, DownloadLimitError, NoResultsError
from utils.texts import BOT_SIGNATURE, DOWNLOAD_FAILED_TEXT, LIMIT_TEXT, MUSIC_PROMPT, NOT_FOUND_TEXT, WAIT_TEXT

router = Router()
logger = logging.getLogger(__name__)


async def show_music_results(message: Message, state: FSMContext, query: str, config: Config, intro: str | None = None) -> None:
    try:
        results = await search_music(query, config, limit=20)
    except NoResultsError:
        await send_not_found(message, config)
        return
    except DownloadError:
        logger.exception("Music search failed")
        await message.answer(DOWNLOAD_FAILED_TEXT)
        return

    await state.update_data(music_results=[item.__dict__ for item in results], music_query=query)
    await state.set_state(None)
    text = f"{intro}\n\n{music_results_text(results, page=0)}" if intro else music_results_text(results, page=0)
    await message.answer(text, reply_markup=music_results_keyboard(results, page=0))


@router.callback_query(F.data == "music_start")
async def music_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(MusicStates.waiting_for_query)
    await callback.message.edit_text(MUSIC_PROMPT)
    await callback.answer()


@router.message(MusicStates.waiting_for_query, F.text)
async def music_query(message: Message, state: FSMContext, config: Config) -> None:
    query = message.text.strip()
    if len(query) < 2:
        await message.answer("Qo'shiq nomi juda qisqa. To'liqroq yozing.")
        return

    await show_music_results(message, state, query, config)


@router.message(F.audio | F.voice | F.video | F.video_note)
async def recognize_music_message(message: Message, state: FSMContext, config: Config, db: Database) -> None:
    attachment = get_music_attachment(message)
    if not attachment:
        return

    status = await message.answer("Musiqani aniqlayapman...")
    media_path = None
    try:
        media_path = await download_attachment(message.bot, attachment, config)
        track = await recognize_track(media_path)
        lyrics_text = f"\n\n<b>Matn:</b>\n{escape(track.lyrics)}" if track.lyrics else ""
        await status.edit_text(
            f"<b>Topildi:</b> {escape(track.title)}\n"
            f"<b>Ijrochi:</b> {escape(track.artist)}{lyrics_text}\n\n"
            "Yuklab olish uchun natijalardan birini tanlang."
        )
        await show_music_results(
            message,
            state,
            track.query,
            config,
            intro=f"<b>{escape(track.artist)} - {escape(track.title)}</b>\n\nNatijalardan birini tanlang:",
        )
    except NoResultsError:
        with suppress(TelegramAPIError):
            await status.delete()
        await send_not_found(message, config)
    except DownloadError as exc:
        logger.exception("Music recognition failed")
        await status.edit_text("Musiqani aniqlashda xatolik bo'ldi. Keyinroq urinib ko'ring.")
        await db.record_error(message.from_user.id if message.from_user else None, type(exc).__name__, str(exc))
    except TelegramAPIError as exc:
        logger.exception("Telegram file download failed")
        await status.edit_text("Faylni Telegramdan yuklab olishda xatolik bo'ldi.")
        await db.record_error(message.from_user.id if message.from_user else None, type(exc).__name__, str(exc))
    finally:
        if media_path:
            remove_file(media_path)


@router.callback_query(F.data.startswith("music_pick:"))
async def music_pick(callback: CallbackQuery, state: FSMContext, config: Config, db: Database) -> None:
    data = await state.get_data()
    results = data.get("music_results") or []
    query = data.get("music_query")
    try:
        index = int(callback.data.split(":", 1)[1])
        selected = results[index]
    except (ValueError, IndexError, KeyError):
        await callback.answer("Natija topilmadi", show_alert=True)
        return

    await callback.message.edit_text(WAIT_TEXT)
    await callback.answer()
    result = None
    try:
        result = await download_music(selected["url"], config)
        await callback.message.answer_audio(
            FSInputFile(result.path),
            title=result.title,
            caption=f"<b>{escape(result.title)}</b>\n\nManba: YouTube\n\n{BOT_SIGNATURE}",
        )
        await db.record_download(
            user_id=callback.from_user.id,
            source="YouTube",
            media_type="music",
            success=True,
            query=query,
            title=result.title,
            file_size=result.file_size,
        )
        with suppress(TelegramAPIError):
            await callback.message.delete()
        await state.clear()
    except DownloadLimitError:
        await callback.message.edit_text(
            LIMIT_TEXT.format(max_mb=config.max_file_mb, max_minutes=config.max_duration_seconds // 60),
            reply_markup=main_keyboard(),
        )
        await db.record_download(
            user_id=callback.from_user.id,
            source="YouTube",
            media_type="music",
            success=False,
            query=query,
            error="limit",
        )
    except DownloadError as exc:
        logger.exception("Music download failed")
        await callback.message.edit_text(DOWNLOAD_FAILED_TEXT, reply_markup=main_keyboard())
        await db.record_download(
            user_id=callback.from_user.id,
            source="YouTube",
            media_type="music",
            success=False,
            query=query,
            error=str(exc)[:500],
        )
        await db.record_error(callback.from_user.id, type(exc).__name__, str(exc))
    except TelegramAPIError as exc:
        logger.exception("Telegram refused the audio file")
        await callback.message.edit_text(
            "Audio Telegram orqali yuborilmadi. Boshqa qo'shiq bilan urinib ko'ring.",
            reply_markup=main_keyboard(),
        )
        await db.record_download(
            user_id=callback.from_user.id,
            source="YouTube",
            media_type="music",
            success=False,
            query=query,
            error=str(exc)[:500],
        )
        await db.record_error(callback.from_user.id, type(exc).__name__, str(exc))
    finally:
        if result:
            remove_file(result.path)


@router.callback_query(F.data.startswith("music_page:"))
async def music_page(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    results = data.get("music_results") or []
    if not results:
        await callback.answer("Natijalar eskirgan", show_alert=True)
        return
    page = int(callback.data.split(":", 1)[1])
    await callback.message.edit_text(
        music_results_text(results, page=page),
        reply_markup=music_results_keyboard(results, page=page),
    )
    await callback.answer()


@router.callback_query(F.data == "music_cancel")
async def music_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Bekor qilindi.", reply_markup=main_keyboard())
    await callback.answer()
