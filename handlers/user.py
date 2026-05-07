from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from database.db import Database
from keyboards.inline import main_keyboard, start_keyboard
from utils.texts import HELP_TEXT, MUSIC_PROMPT, WELCOME_TEXT

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    await message.answer(WELCOME_TEXT, reply_markup=start_keyboard())


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=main_keyboard())


@router.callback_query(F.data == "help")
async def help_callback(callback: CallbackQuery) -> None:
    await callback.message.edit_text(HELP_TEXT, reply_markup=main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "home")
async def home_callback(callback: CallbackQuery) -> None:
    await callback.message.edit_text(WELCOME_TEXT, reply_markup=start_keyboard())
    await callback.answer()


@router.callback_query(F.data == "help_video")
async def help_video_callback(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "Media yuklash uchun TikTok, Instagram, YouTube, Facebook, Twitter/X, Snapchat, Likee, Pinterest, Threads yoki VK havolasini yuboring.",
        reply_markup=main_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "my_stats")
async def my_stats_callback(callback: CallbackQuery, db: Database) -> None:
    stats = await db.get_user_stats(callback.from_user.id)
    await callback.message.edit_text(
        f"<b>Sizning statistikangiz</b>\n\nYuklangan fayllar: <b>{stats['downloads']}</b>",
        reply_markup=main_keyboard(),
    )
    await callback.answer()
