import asyncio
from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import Config
from database.db import Database
from keyboards.inline import admin_keyboard, broadcast_confirm_keyboard
from states import BroadcastStates
from utils.texts import ADMIN_ONLY_TEXT

router = Router()


def _is_admin(user_id: int, config: Config) -> bool:
    return user_id in config.admin_ids


def _format_stats(stats: dict) -> str:
    return (
        "<b>Admin statistikasi</b>\n\n"
        f"Jami foydalanuvchilar: <b>{stats['total_users']}</b>\n"
        f"Faol foydalanuvchilar (7 kun): <b>{stats['active_users']}</b>\n"
        f"Jami yuklashlar: <b>{stats['total_downloads']}</b>\n"
        f"Video yuklashlar: <b>{stats['video_downloads']}</b>\n"
        f"Musiqa yuklashlar: <b>{stats['music_downloads']}</b>\n"
        f"Xatoliklar: <b>{stats['errors']}</b>"
    )


@router.message(Command("admin"))
async def admin_command(message: Message, config: Config) -> None:
    if not message.from_user or not _is_admin(message.from_user.id, config):
        await message.answer("Buyruq topilmadi. /start ni bosing.")
        return
    await message.answer("<b>Admin panel</b>", reply_markup=admin_keyboard())


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery, config: Config, db: Database) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer(ADMIN_ONLY_TEXT, show_alert=True)
        return
    stats = await db.get_stats()
    await callback.message.edit_text(_format_stats(stats), reply_markup=admin_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, config: Config, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer(ADMIN_ONLY_TEXT, show_alert=True)
        return
    await state.set_state(BroadcastStates.waiting_for_text)
    await callback.message.edit_text("Broadcast matnini yuboring.")
    await callback.answer()


@router.message(BroadcastStates.waiting_for_text, F.text)
async def broadcast_text(message: Message, state: FSMContext, config: Config) -> None:
    if not message.from_user or not _is_admin(message.from_user.id, config):
        await state.clear()
        await message.answer(ADMIN_ONLY_TEXT)
        return
    text = message.text.strip()
    if len(text) < 2:
        await message.answer("Matn juda qisqa.")
        return
    await state.update_data(broadcast_text=text)
    await state.set_state(BroadcastStates.confirming)
    await message.answer(
        f"<b>Broadcast tasdiqlash</b>\n\n{escape(text)}",
        reply_markup=broadcast_confirm_keyboard(),
    )


@router.callback_query(F.data == "broadcast_cancel")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Broadcast bekor qilindi.", reply_markup=admin_keyboard())
    await callback.answer()


@router.callback_query(F.data == "broadcast_confirm")
async def broadcast_confirm(callback: CallbackQuery, state: FSMContext, config: Config, db: Database) -> None:
    if not _is_admin(callback.from_user.id, config):
        await callback.answer(ADMIN_ONLY_TEXT, show_alert=True)
        return

    data = await state.get_data()
    text = data.get("broadcast_text")
    if not text:
        await callback.message.edit_text("Broadcast matni topilmadi.", reply_markup=admin_keyboard())
        await state.clear()
        return

    await callback.message.edit_text("Broadcast yuborilmoqda...")
    user_ids = await db.get_all_user_ids()
    sent = 0
    failed = 0

    bot = callback.bot
    for user_id in user_ids:
        try:
            await bot.send_message(user_id, escape(text))
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1

    await db.record_broadcast(callback.from_user.id, text, sent, failed)
    await state.clear()
    await callback.message.edit_text(
        f"Broadcast tugadi.\n\nYuborildi: <b>{sent}</b>\nXatolik: <b>{failed}</b>",
        reply_markup=admin_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_close")
async def admin_close(callback: CallbackQuery) -> None:
    await callback.message.delete()
    await callback.answer()
