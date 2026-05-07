import logging
from typing import Any

from aiogram import Router
from aiogram.types import ErrorEvent

from database.db import Database

router = Router()
logger = logging.getLogger(__name__)


@router.errors()
async def global_error_handler(event: ErrorEvent, db: Database | None = None) -> bool:
    logger.exception("Unhandled update error", exc_info=event.exception)
    user_id = _extract_user_id(event.update.model_dump(exclude_none=True))
    if db:
        await db.record_error(user_id, type(event.exception).__name__, str(event.exception))
    return True


def _extract_user_id(update: dict[str, Any]) -> int | None:
    for key in ("message", "callback_query"):
        payload = update.get(key)
        if not payload:
            continue
        user = payload.get("from")
        if user and user.get("id"):
            return int(user["id"])
    return None
