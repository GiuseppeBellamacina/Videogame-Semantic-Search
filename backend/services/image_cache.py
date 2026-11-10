"""
Caches for the application:
  - "img:"   image URLs for VideoGame nodes — persistent (SQLite, see services/cache.py)
  - "label:" node labels by URI — in-memory only (derived from the in-memory RDF store)
  - "type:"  node types by URI  — in-memory only

Public API:
    from backend.services.image_cache import get_image, set_image   # async
    from backend.services.image_cache import get_label, set_label   # sync
    from backend.services.image_cache import get_type, set_type     # sync
"""

import json

from backend.config import CACHE_TTL_IMAGE
from backend.services import cache

_local_label: dict[str, str] = {}
_local_type: dict[str, str] = {}


# ── Image cache (async) ───────────────────────────────────────────────────────


async def get_image(name: str) -> dict | None:
    raw = await cache.aget(f"img:{name.strip().lower()}")
    return json.loads(raw) if raw is not None else None


async def set_image(name: str, result: dict) -> None:
    await cache.aset(f"img:{name.strip().lower()}", json.dumps(result), CACHE_TTL_IMAGE)


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
