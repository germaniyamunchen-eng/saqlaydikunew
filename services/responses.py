from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message

from config import Config
from utils.texts import NOT_FOUND_TEXT


async def send_not_found(message: Message, config: Config) -> None:
    if config.sad_sticker_id:
        try:
            await message.answer_sticker(config.sad_sticker_id)
        except TelegramAPIError:
            pass
    await message.answer(NOT_FOUND_TEXT)
