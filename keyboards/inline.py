from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from services.downloader import SearchResult

BOT_USERNAME = "saqlaydiku_bot"
MUSIC_PAGE_SIZE = 10


def main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Guruhga qo'shish", url=f"https://t.me/{BOT_USERNAME}?startgroup=true")]
        ]
    )


def start_keyboard() -> InlineKeyboardMarkup:
    return main_keyboard()


def admin_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Statistika", callback_data="admin_stats")],
            [InlineKeyboardButton(text="Broadcast yuborish", callback_data="admin_broadcast")],
            [InlineKeyboardButton(text="Yopish", callback_data="admin_close")],
        ]
    )


def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Yuborish", callback_data="broadcast_confirm"),
                InlineKeyboardButton(text="Bekor qilish", callback_data="broadcast_cancel"),
            ]
        ]
    )


def music_results_keyboard(results: list[SearchResult], page: int = 0) -> InlineKeyboardMarkup:
    rows = []
    total_pages = max(1, (len(results) + MUSIC_PAGE_SIZE - 1) // MUSIC_PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    start = page * MUSIC_PAGE_SIZE
    end = start + MUSIC_PAGE_SIZE

    for index, item in enumerate(results[start:end], start=start + 1):
        duration = _format_duration(item.duration)
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{index}. {item.title[:45]} ({duration})",
                    callback_data=f"music_pick:{index - 1}",
                )
            ]
        )

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="Ortga", callback_data=f"music_page:{page - 1}"))
    nav.append(InlineKeyboardButton(text="Bosh sahifa", callback_data="home"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="Keyingisi", callback_data=f"music_page:{page + 1}"))
    rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _format_duration(seconds: int) -> str:
    if not seconds:
        return "?"
    minutes, secs = divmod(seconds, 60)
    return f"{minutes}:{secs:02d}"
