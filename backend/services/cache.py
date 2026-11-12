"""
Tiny persistent key/value cache on SQLite (stdlib only), with per-key TTL.
Used for Wikipedia cover images and natural-language query results.
"""

import asyncio
import logging
import sqlite3
import threading
import time

from backend.config import CACHE_DB_PATH

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def _db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        CACHE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(CACHE_DB_PATH, check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute(
            "CREATE TABLE IF NOT EXISTS cache "
            "(key TEXT PRIMARY KEY, value TEXT NOT NULL, expires REAL NOT NULL)"
        )
        _conn.execute("DELETE FROM cache WHERE expires < ?", (time.time(),))
        _conn.commit()
        logger.info(f"[CACHE] SQLite cache at {CACHE_DB_PATH}")
    return _conn


def get(key: str) -> str | None:
    with _lock:
        row = (
            _db()
            .execute(
                "SELECT value FROM cache WHERE key=? AND expires>=?", (key, time.time())
            )
            .fetchone()
        )
    return row[0] if row else None


def set(key: str, value: str, ttl: int) -> None:  # noqa: A001
    with _lock:
        db = _db()
        db.execute(
            "INSERT OR REPLACE INTO cache (key, value, expires) VALUES (?,?,?)",
            (key, value, time.time() + ttl),
        )
        db.commit()


def keys(prefix: str) -> list[str]:
    # substr instead of LIKE so '%'/'_' in the prefix are not wildcards
    with _lock:
        rows = (
            _db()
            .execute(
                "SELECT key FROM cache WHERE substr(key,1,?)=? AND expires>=?",
                (len(prefix), prefix, time.time()),
            )
            .fetchall()
        )
    return [r[0] for r in rows]


def close() -> None:
    global _conn
    with _lock:
        if _conn is not None:
            _conn.close()
            _conn = None


async def aget(key: str) -> str | None:
    return await asyncio.to_thread(get, key)


async def aset(key: str, value: str, ttl: int) -> None:
    await asyncio.to_thread(set, key, value, ttl)


async def akeys(prefix: str) -> list[str]:
    return await asyncio.to_thread(keys, prefix)
