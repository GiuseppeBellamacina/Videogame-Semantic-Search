"""
Cover images for entities (games, publishers, platforms...).

Lookup order for a (type, name):
  1. a local file in IMAGE_DIR           -> served by /api/image-file/<file>
  2. the thumbnail URL stored in SQLite  -> downloaded to a local file
  3. a Wikipedia search                  -> URL and file are both stored
"Not found" is stored too (short TTL) so Wikipedia is not asked again for every node.

All network and disk work is async: one shared httpx client, a semaphore that caps the
concurrent Wikipedia calls, and one in-flight request per key.
"""

import asyncio
import hashlib
import json
import logging
import re
from pathlib import Path
from urllib.parse import quote

import httpx

from backend.config import CACHE_TTL_IMAGE, IMAGE_DIR, IMAGE_MISS_TTL
from backend.services import cache

logger = logging.getLogger(__name__)

USER_AGENT = (
    "VideogameSemanticSearch/1.0 "
    "(https://github.com/GiuseppeBellamacina/Videogame-Semantic-Search; educational project)"
)
KEY_PREFIX = "img:"
FILE_RE = re.compile(r"^[0-9a-f]{16}\.(jpg|png|webp|gif)$")
MAX_BYTES = 2_000_000
EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp", "image/gif": "gif"}

_client: httpx.AsyncClient | None = None
_sem = asyncio.Semaphore(6)
_inflight: dict[str, asyncio.Future] = {}

# Wikipedia title variants and search hint per entity type
_VARIANTS = {
    "VideoGame": ["{n} (video game)", "{n}"],
    "Developer": ["{n}", "{n} (company)", "{n} (video game company)"],
    "Publisher": ["{n}", "{n} (company)", "{n} (video game company)"],
    "Platform": ["{n}", "{n} (console)", "{n} (video game console)"],
    "Franchise": ["{n} (series)", "{n} (video game series)", "{n} (franchise)", "{n}"],
    "GameEngine": ["{n}", "{n} (game engine)"],
    "Character": ["{n}", "{n} (character)", "{n} (video game character)"],
}
_HINT = {
    "VideoGame": "video game",
    "Developer": "video game developer",
    "Publisher": "video game publisher",
    "Platform": "video game console",
    "Franchise": "video game series",
    "GameEngine": "game engine",
    "Character": "video game character",
}


def _norm_type(t: str) -> str:
    return "VideoGame" if t in ("AwardWinningGame", "FranchiseGame") else t


def key_for(name: str, etype: str) -> str:
    return f"{KEY_PREFIX}{_norm_type(etype)}|{name.strip().lower()}"


def file_stem(key: str) -> str:
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def local_url(file: str) -> str:
    return f"/api/image-file/{file}"


def image_path(file: str) -> Path | None:
    """Path of a stored image, or None for a name that is not one of ours."""
    return IMAGE_DIR / file if FILE_RE.match(file) else None


def _http() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(
            timeout=10.0,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        )
    return _client


async def close() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None


async def _get(url: str, **kw) -> httpx.Response | None:
    """GET with the shared client, the semaphore and a short retry on 429/5xx."""
    async with _sem:
        for attempt in range(3):
            try:
                resp = await _http().get(url, **kw)
            except httpx.HTTPError as e:
                logger.warning(f"[IMG] {url[:80]}: {e}")
                return None
            if resp.status_code in (429, 500, 502, 503):
                wait = resp.headers.get("Retry-After", "")
                await asyncio.sleep(min(int(wait) if wait.isdigit() else 1.5 * (attempt + 1), 5))
                continue
            return resp
    return None


async def _summary_thumb(title: str, etype: str) -> str | None:
    resp = await _get(
        f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title.replace(' ', '_'), safe='')}"
    )
    if resp is None or resp.status_code != 200:
        return None
    data = resp.json()
    if data.get("type") == "disambiguation":
        return None
    thumb = (data.get("thumbnail") or {}).get("source")
    if not thumb:
        return None
    if etype == "VideoGame" and "(video game)" not in title:
        # a bare title may be a film, a person or a franchise: require a game in the blurb
        blurb = f"{data.get('description', '')} {data.get('extract', '')}".lower()
        if "game" not in blurb:
            return None
    return thumb


async def _search_thumb(name: str, etype: str) -> str | None:
    resp = await _get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query", "generator": "search", "gsrlimit": 1, "format": "json",
            "gsrsearch": f"{name} {_HINT.get(etype, '')}".strip(),
            "prop": "pageimages", "piprop": "thumbnail", "pithumbsize": 320,
        },
    )
    if resp is None or resp.status_code != 200:
        return None
    pages = (resp.json().get("query") or {}).get("pages") or {}
    for page in pages.values():
        thumb = (page.get("thumbnail") or {}).get("source")
        # accept only a page whose title is close to the name searched
        title = page.get("title", "").lower()
        if thumb and name.lower().split(" (")[0] in title:
            return thumb
    return None


async def _find_thumb(name: str, etype: str) -> str | None:
    for tpl in _VARIANTS.get(etype, ["{n}"]):
        thumb = await _summary_thumb(tpl.format(n=name), etype)
        if thumb:
            return thumb
    return await _search_thumb(name, etype)


async def _download(url: str, stem: str) -> str | None:
    """Fetch the thumbnail into IMAGE_DIR; returns the file name."""
    resp = await _get(url)
    if resp is None or resp.status_code != 200:
        return None
    ext = EXT.get(resp.headers.get("content-type", "").split(";")[0].strip())
    if not ext or len(resp.content) > MAX_BYTES:
        return None
    name = f"{stem}.{ext}"

    def write() -> None:
        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        (IMAGE_DIR / name).write_bytes(resp.content)

    await asyncio.to_thread(write)
    return name


async def _resolve(name: str, etype: str) -> dict:
    key = key_for(name, etype)
    stem = file_stem(key)
    raw = await cache.aget(key)
    entry = json.loads(raw) if raw else None

    if entry and entry.get("miss"):
        return {"imageUrl": None, "source": None}

    if entry:
        file = entry.get("file")
        if file and (IMAGE_DIR / file).exists():  # 1. local file
            return {"imageUrl": local_url(file), "source": entry.get("source")}
        file = await _download(entry["url"], stem)  # 2. stored URL, file lost or never saved
        if file:
            entry["file"] = file
            await cache.aset(key, json.dumps(entry), CACHE_TTL_IMAGE)
            return {"imageUrl": local_url(file), "source": entry.get("source")}
        return {"imageUrl": entry["url"], "source": entry.get("source")}

    thumb = await _find_thumb(name, _norm_type(etype))  # 3. search
    if not thumb:
        await cache.aset(key, json.dumps({"miss": True}), IMAGE_MISS_TTL)
        return {"imageUrl": None, "source": None}
    file = await _download(thumb, stem)
    entry = {"url": thumb, "file": file, "source": "wikipedia"}
    await cache.aset(key, json.dumps(entry), CACHE_TTL_IMAGE)
    return {"imageUrl": local_url(file) if file else thumb, "source": "wikipedia"}


async def resolve(name: str, etype: str = "VideoGame") -> dict:
    """Image for one entity: {"imageUrl": str | None, "source": str | None}."""
    name = name.strip()
    if not name or re.fullmatch(r"Q\d+", name):
        return {"imageUrl": None, "source": None}
    key = key_for(name, etype)
    fut = _inflight.get(key)
    if fut is None:
        fut = _inflight[key] = asyncio.ensure_future(_resolve(name, etype))
        fut.add_done_callback(lambda _: _inflight.pop(key, None))
    try:
        return await asyncio.shield(fut)
    except Exception as e:  # network trouble must never break the graph
        logger.warning(f"[IMG] {etype} '{name}': {e}")
        return {"imageUrl": None, "source": None}


async def resolve_many(items: list[tuple[str, str]]) -> list[dict]:
    return await asyncio.gather(*(resolve(n, t) for n, t in items))
