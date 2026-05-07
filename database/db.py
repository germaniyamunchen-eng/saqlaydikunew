from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import aiosqlite
from aiogram.types import User

logger = logging.getLogger(__name__)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.connection: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = await aiosqlite.connect(self.path)
        self.connection.row_factory = aiosqlite.Row
        await self.connection.execute("PRAGMA journal_mode=WAL")
        await self.connection.execute("PRAGMA foreign_keys=ON")
        await self.connection.commit()

    async def close(self) -> None:
        if self.connection:
            await self.connection.close()

    @property
    def db(self) -> aiosqlite.Connection:
        if not self.connection:
            raise RuntimeError("Database is not connected")
        return self.connection

    async def init_schema(self) -> None:
        await self.db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language_code TEXT,
                is_admin INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                last_seen TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS downloads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                source TEXT NOT NULL,
                media_type TEXT NOT NULL,
                query TEXT,
                title TEXT,
                file_size INTEGER DEFAULT 0,
                success INTEGER NOT NULL,
                error TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                error_type TEXT NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS broadcasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                sent_count INTEGER NOT NULL,
                failed_count INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        await self.db.commit()
        logger.info("Database schema is ready")

    async def upsert_user(self, user: User, is_admin: bool = False) -> None:
        now = utc_now()
        await self.db.execute(
            """
            INSERT INTO users (
                telegram_id, username, first_name, last_name, language_code,
                is_admin, created_at, last_seen
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                language_code = excluded.language_code,
                is_admin = excluded.is_admin,
                last_seen = excluded.last_seen
            """,
            (
                user.id,
                user.username,
                user.first_name,
                user.last_name,
                user.language_code,
                int(is_admin),
                now,
                now,
            ),
        )
        await self.db.commit()

    async def record_download(
        self,
        user_id: int | None,
        source: str,
        media_type: str,
        success: bool,
        query: str | None = None,
        title: str | None = None,
        file_size: int = 0,
        error: str | None = None,
    ) -> None:
        await self.db.execute(
            """
            INSERT INTO downloads (
                user_id, source, media_type, query, title, file_size,
                success, error, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, source, media_type, query, title, file_size, int(success), error, utc_now()),
        )
        await self.db.commit()

    async def record_error(self, user_id: int | None, error_type: str, message: str) -> None:
        await self.db.execute(
            "INSERT INTO errors (user_id, error_type, message, created_at) VALUES (?, ?, ?, ?)",
            (user_id, error_type, message[:1000], utc_now()),
        )
        await self.db.commit()

    async def record_broadcast(self, admin_id: int, text: str, sent_count: int, failed_count: int) -> None:
        await self.db.execute(
            """
            INSERT INTO broadcasts (admin_id, text, sent_count, failed_count, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (admin_id, text, sent_count, failed_count, utc_now()),
        )
        await self.db.commit()

    async def get_all_user_ids(self) -> list[int]:
        cursor = await self.db.execute("SELECT telegram_id FROM users")
        rows = await cursor.fetchall()
        return [int(row["telegram_id"]) for row in rows]

    async def get_stats(self) -> dict[str, Any]:
        active_since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        queries = {
            "total_users": "SELECT COUNT(*) AS value FROM users",
            "active_users": "SELECT COUNT(*) AS value FROM users WHERE last_seen >= ?",
            "total_downloads": "SELECT COUNT(*) AS value FROM downloads WHERE success = 1",
            "video_downloads": "SELECT COUNT(*) AS value FROM downloads WHERE success = 1 AND media_type = 'video'",
            "music_downloads": "SELECT COUNT(*) AS value FROM downloads WHERE success = 1 AND media_type = 'music'",
            "errors": "SELECT COUNT(*) AS value FROM errors",
        }
        stats: dict[str, Any] = {}
        for key, query in queries.items():
            if key == "active_users":
                cursor = await self.db.execute(query, (active_since,))
            else:
                cursor = await self.db.execute(query)
            row = await cursor.fetchone()
            stats[key] = int(row["value"]) if row else 0
        return stats

    async def get_user_stats(self, telegram_id: int) -> dict[str, int]:
        cursor = await self.db.execute(
            "SELECT COUNT(*) AS value FROM downloads WHERE user_id = ? AND success = 1",
            (telegram_id,),
        )
        downloads = await cursor.fetchone()
        return {"downloads": int(downloads["value"]) if downloads else 0}
