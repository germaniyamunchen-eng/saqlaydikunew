import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import Config
from database.db import Database
from handlers import admin, download, errors, music, user
from middlewares.throttling import ThrottlingMiddleware
from middlewares.user_tracking import UserTrackingMiddleware
from services.commands import setup_bot_commands
from utils.logger import setup_logging


async def main() -> None:
    config = Config.from_env()
    setup_logging(config.log_level)
    logger = logging.getLogger(__name__)

    db = Database(config.database_path)
    await db.connect()
    await db.init_schema()

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp["config"] = config
    dp["db"] = db

    dp.message.middleware(UserTrackingMiddleware())
    dp.callback_query.middleware(UserTrackingMiddleware())
    dp.message.middleware(ThrottlingMiddleware())

    dp.include_router(user.router)
    dp.include_router(admin.router)
    dp.include_router(music.router)
    dp.include_router(download.router)
    dp.include_router(errors.router)

    try:
        logger.info("Bot started in polling mode")
        await bot.delete_webhook(drop_pending_updates=True)
        await setup_bot_commands(bot, config)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        logger.info("Shutting down bot")
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
