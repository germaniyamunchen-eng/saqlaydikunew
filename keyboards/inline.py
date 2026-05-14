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

    number_buttons = []
    for index, _item in enumerate(results[start:end], start=start + 1):
        number_buttons.append(InlineKeyboardButton(text=str(index), callback_data=f"music_pick:{index - 1}"))
        if len(number_buttons) == 5:
            rows.append(number_buttons)
            number_buttons = []
    if number_buttons:
        rows.append(number_buttons)

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="Ortga", callback_data=f"music_page:{page - 1}"))
    nav.append(InlineKeyboardButton(text="Bosh sahifa", callback_data="home"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="Keyingisi", callback_data=f"music_page:{page + 1}"))
    rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def music_results_text(results: list[SearchResult], page: int = 0) -> str:
    total_pages = max(1, (len(results) + MUSIC_PAGE_SIZE - 1) // MUSIC_PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    start = page * MUSIC_PAGE_SIZE
    end = start + MUSIC_PAGE_SIZE

    lines = ["<b>Qo'shiqlardan birini tanlang:</b>", ""]
    for index, item in enumerate(results[start:end], start=start + 1):
        title = _get_value(item, "title")[:70]
        uploader = _get_value(item, "uploader")
        duration = _format_duration(int(_get_value(item, "duration") or 0))
        artist = f" - {uploader}" if uploader else ""
        lines.append(f"<b>{index}.</b> {title}{artist} ({duration})")
    lines.append("")
    lines.append("Pastdagi raqamlardan birini bosing.")
    return "\n".join(lines)


def url_audio_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Audiosini yuklash", callback_data="url_audio")],
            [InlineKeyboardButton(text="Bosh sahifa", callback_data="home")],
        ]
    )


def _get_value(item: SearchResult | dict, key: str) -> str:
    if isinstance(item, dict):
        value = item.get(key)
    else:
        value = getattr(item, key)
    return str(value or "")


def _format_duration(seconds: int) -> str:
    if not seconds:
        return "?"
    minutes, secs = divmod(seconds, 60)
    return f"{minutes}:{secs:02d}"
