from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from config import Config
from services.cooldown import cooldown_store
from utils.texts import TOO_FAST_TEXT


class ThrottlingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or not event.from_user:
            return await handler(event, data)

        text = event.text or ""
        if text.startswith("/"):
            return await handler(event, data)

        config: Config = data["config"]
        if event.from_user.id in config.admin_ids:
            return await handler(event, data)

        remaining = cooldown_store.remaining(event.from_user.id, config.cooldown_seconds)
        if remaining:
            await event.answer(TOO_FAST_TEXT.format(seconds=remaining))
            return None

        return await handler(event, data)
