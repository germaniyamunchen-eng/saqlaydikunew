from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from config import Config


async def setup_bot_commands(bot: Bot, config: Config) -> None:
    default_commands = [
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="help", description="Yordam"),
    ]
    admin_commands = [
        *default_commands,
        BotCommand(command="admin", description="Admin panel"),
    ]

    await bot.set_my_commands(default_commands, scope=BotCommandScopeDefault())
    for admin_id in config.admin_ids:
        await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
