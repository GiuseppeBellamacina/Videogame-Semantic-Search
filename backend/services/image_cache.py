"""
Two-level cache for the application:
  1. Upstash AsyncRedis (cloud, persistent across restarts) — used if credentials are set
  2. In-memory dicts (local fallback, lost on restart)

Three namespaces:
  - "img:"    image URLs for VideoGame nodes (TTL 7 days) — async Redis
  - "label:"  node labels by URI — sync, in-memory only (derived from in-memory RDF graph)
  - "type:"   node types by URI  — sync, in-memory only (derived from in-memory RDF graph)

Public API:
    from backend.services.image_cache import get_image, set_image   # async
    from backend.services.image_cache import get_label, set_label   # sync
    from backend.services.image_cache import get_type, set_type     # sync
"""

import json
import logging
from typing import Any

from backend.config import CACHE_TTL, UPSTASH_REDIS_REST_TOKEN, UPSTASH_REDIS_REST_URL

logger = logging.getLogger(__name__)

# ── Local in-memory stores ────────────────────────────────────────────────────
_local_img: dict[str, dict] = {}
_local_label: dict[str, str] = {}
_local_type: dict[str, str] = {}

# ── Async Upstash Redis client (lazy init) ────────────────────────────────────
_async_redis: Any = None
_redis_available: bool | None = None  # None = not yet tested


def _get_async_redis():
    """Return an AsyncRedis client, or None if credentials are missing / unavailable."""
    global _async_redis, _redis_available

    if _redis_available is False:
        return None
    if _async_redis is not None:
        return _async_redis

    if not UPSTASH_REDIS_REST_URL or not UPSTASH_REDIS_REST_TOKEN:
        logger.info("[CACHE] Upstash credentials not set — using in-memory cache only")
        _redis_available = False
        return None

    try:
        from upstash_redis.asyncio import Redis as AsyncRedis  # type: ignore[import]

        _async_redis = AsyncRedis(
            url=UPSTASH_REDIS_REST_URL, token=UPSTASH_REDIS_REST_TOKEN
        )
        _redis_available = True
        logger.info("[CACHE] Upstash AsyncRedis initialised")
    except Exception as e:
        logger.warning(
            f"[CACHE] Could not initialise Upstash AsyncRedis: {e} — falling back to in-memory"
        )
        _redis_available = False

    return _async_redis


# ── Async Redis helpers ───────────────────────────────────────────────────────


async def _aredis_get(key: str) -> str | None:
    redis = _get_async_redis()
    if redis is None:
        return None
    try:
        return await redis.get(key)
    except Exception as e:
        logger.warning(f"[CACHE] Redis GET error for '{key}': {e}")
        return None


async def _aredis_set(key: str, value: str, ttl: int | None = None) -> None:
    redis = _get_async_redis()
    if redis is None:
        return
    try:
        if ttl:
            await redis.set(key, value, ex=ttl)
        else:
            await redis.set(key, value)
    except Exception as e:
        logger.warning(f"[CACHE] Redis SET error for '{key}': {e}")


# ── Image cache (async) ───────────────────────────────────────────────────────


async def get_image(name: str) -> dict | None:
    k = f"img:{name.strip().lower()}"
    raw = await _aredis_get(k)
    if raw is not None:
        return json.loads(raw) if isinstance(raw, str) else raw
    return _local_img.get(k)


async def set_image(name: str, result: dict) -> None:
    k = f"img:{name.strip().lower()}"
    _local_img[k] = result
    await _aredis_set(k, json.dumps(result), ttl=CACHE_TTL)


# ── Label cache (sync, in-memory only) ───────────────────────────────────────
# Labels are derived from the in-memory RDF graph on first access and cached locally.
# No Redis needed: the data is already available in-memory and labels are static.


def get_label(uri: str) -> str | None:
    return _local_label.get(uri)


def set_label(uri: str, label: str) -> None:
    _local_label[uri] = label


# ── Type cache (sync, in-memory only) ────────────────────────────────────────


def get_type(uri: str) -> str | None:
    return _local_type.get(uri)


def set_type(uri: str, node_type: str) -> None:
    _local_type[uri] = node_type
