import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _parse_admin_ids(raw_value: str) -> set[int]:
    admin_ids: set[int] = set()
    for item in raw_value.split(","):
        item = item.strip()
        if not item:
            continue
        if not item.isdigit():
            raise ValueError("ADMIN_IDS must contain comma-separated Telegram numeric IDs")
        admin_ids.add(int(item))
    return admin_ids


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: set[int]
    database_path: Path
    download_dir: Path
    log_level: str
    cooldown_seconds: int
    max_file_mb: int
    max_duration_seconds: int
    sad_sticker_id: str | None = None
    railway_environment: str | None = None

    @property
    def max_file_bytes(self) -> int:
        return self.max_file_mb * 1024 * 1024

    @classmethod
    def from_env(cls) -> "Config":
        load_dotenv()

        bot_token = os.getenv("BOT_TOKEN", "").strip()
        if not bot_token:
            raise RuntimeError("BOT_TOKEN is required. Copy .env.example to .env and add your Telegram bot token.")

        admin_ids = _parse_admin_ids(os.getenv("ADMIN_IDS", ""))

        database_path = Path(os.getenv("DATABASE_PATH", "data/bot.db"))
        download_dir = Path(os.getenv("DOWNLOAD_DIR", "downloads"))

        cooldown_seconds = int(os.getenv("COOLDOWN_SECONDS", "10"))
        max_file_mb = int(os.getenv("MAX_FILE_MB", "45"))
        max_duration_seconds = int(os.getenv("MAX_DURATION_SECONDS", "900"))

        database_path.parent.mkdir(parents=True, exist_ok=True)
        download_dir.mkdir(parents=True, exist_ok=True)
        Path("logs").mkdir(parents=True, exist_ok=True)

        return cls(
            bot_token=bot_token,
            admin_ids=admin_ids,
            database_path=database_path,
            download_dir=download_dir,
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            cooldown_seconds=cooldown_seconds,
            max_file_mb=max_file_mb,
            max_duration_seconds=max_duration_seconds,
            sad_sticker_id=os.getenv("SAD_STICKER_ID") or None,
            railway_environment=os.getenv("RAILWAY_ENVIRONMENT"),
        )
