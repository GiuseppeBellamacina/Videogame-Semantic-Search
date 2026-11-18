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
import time
import unicodedata
from pathlib import Path
from urllib.parse import quote

import httpx

from backend.config import CACHE_TTL_IMAGE, IMAGE_DIR, IMAGE_MISS_TTL, ONTOLOGY_NS
from backend.services import cache

logger = logging.getLogger(__name__)

USER_AGENT = (
    "VideogameSemanticSearch/1.0 "
    "(https://github.com/GiuseppeBellamacina/Videogame-Semantic-Search; educational project)"
)
KEY_PREFIX = "img:"
FILE_RE = re.compile(r"^[0-9a-f]{16}(-\d+)?\.(jpg|png|webp|gif)$")
MAX_BYTES = 2_000_000
EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
}

_client: httpx.AsyncClient | None = None

# Politeness towards Wikimedia, all of it asynchronous. Two pools of workers: the API calls
# (searches, titles: the expensive ones; Wikimedia asks for 3 at a time at most) and the picture
# downloads (static files from the CDN: a few more in parallel). Each pool also spaces the start of
# its requests. After a 429 *nothing* is sent, by any pool, until the cooldown is over (it doubles
# while 429s keep coming), so a burst of nodes can never turn into a ban.
class _Pool:
    def __init__(self, workers: int, interval: float):
        self.sem = asyncio.Semaphore(workers)
        self.interval = interval
        self.lock = asyncio.Lock()
        self.next_slot = 0.0

    async def pace(self) -> None:
        async with self.lock:
            now = time.monotonic()
            self.next_slot = max(self.next_slot, now) + self.interval
            wait = self.next_slot - self.interval - now
        if wait > 0:
            await asyncio.sleep(wait)


POOLS = {"api": _Pool(3, 0.25), "img": _Pool(5, 0.12)}
COOLDOWN_START, COOLDOWN_MAX = 30.0, 300.0
_cooldown_until = 0.0
_cooldown = COOLDOWN_START


class Transient(Exception):
    """The request could not be answered (rate limit, server error, network): it says nothing
    about whether the picture exists, so it must never be remembered as "not found"."""

    def __init__(self, retry_after: float = 5.0):
        super().__init__(f"transient, retry in {retry_after:.0f}s")
        self.retry_after = retry_after


def cooldown_left() -> float:
    return max(0.0, _cooldown_until - time.monotonic())
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
    if t in ("AwardWinningGame", "FranchiseGame"):
        return "VideoGame"
    return "Developer" if t == "Company" else t  # a company is searched as the developer was


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


async def _get(url: str, pool: str = "api", **kw) -> httpx.Response:
    """GET with the shared client, the semaphore and the pacing. A definite answer (200, 404...)
    is returned; 429, server errors and network failures raise Transient."""
    global _cooldown_until, _cooldown
    workers = POOLS[pool]
    async with workers.sem:
        left = cooldown_left()
        if left > 0:  # in cooldown after a 429: do not even try
            raise Transient(left)
        await workers.pace()
        try:
            resp = await _http().get(url, **kw)
        except httpx.HTTPError as e:
            logger.warning(f"[IMG] {url[:80]}: {e}")
            raise Transient(10) from e
    if resp.status_code == 429:
        wait = resp.headers.get("Retry-After", "")
        pause = max(float(wait) if wait.isdigit() else 0.0, _cooldown)
        _cooldown_until = time.monotonic() + pause
        _cooldown = min(_cooldown * 2, COOLDOWN_MAX)
        logger.warning(f"[IMG] 429 from Wikimedia: pausing every request for {pause:.0f}s")
        raise Transient(pause)
    if resp.status_code in (403, 500, 502, 503, 504):
        raise Transient(15)
    _cooldown = COOLDOWN_START  # a good answer: the backoff starts over
    return resp


def _years_sync(name: str) -> list[str]:
    from backend.services.ontology_service import OntologyService

    lit = name.replace(chr(92), chr(92) * 2).replace('"', chr(92) + '"')
    rows = OntologyService.execute_sparql(
        f'SELECT DISTINCT ?d WHERE {{ ?g <{ONTOLOGY_NS}gameName> "{lit}" ; <{ONTOLOGY_NS}releaseDate> ?d }}',
        max_rows=10,
    )
    return sorted({str(r["d"])[:4] for r in rows if r.get("d")})


async def _years(name: str, etype: str) -> list[str]:
    """Release years of the games with this name: Wikipedia titles a homonym "God of War (2018 video game)"."""
    if etype != "VideoGame":
        return []
    try:
        return await asyncio.to_thread(_years_sync, name)
    except Exception:  # the ontology is not loaded (tools, tests): search by name only
        return []


def _titles(name: str, etype: str, years: list[str]) -> list[str]:
    dated = [f"{name} ({y} video game)" for y in years]
    return dated + [tpl.format(n=name) for tpl in _VARIANTS.get(etype, ["{n}"])]


async def _wikidata_logo(qid: str) -> str | None:
    """Commons render (320 px) of the entity's logo image (Wikidata P154)."""
    resp = await _get(
        "https://www.wikidata.org/w/api.php",
        params={"action": "wbgetclaims", "entity": qid, "property": "P154", "format": "json"},
    )
    if resp.status_code != 200:
        return None
    for claim in (resp.json().get("claims") or {}).get("P154", []):
        file = ((claim.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if file:
            return f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(file)}?width=320"
    return None


async def _title_thumbs(titles: list[str], etype: str) -> list[str | None]:
    """One API call for all the title variants of an entity (instead of one call per title):
    the thumbnail of each title, in the same order, None where the page is missing, is a
    disambiguation page or is not about a game."""
    resp = await _get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "format": "json",
            "redirects": 1,
            "titles": "|".join(titles),
            "prop": "pageimages|pageprops|extracts|description",
            "piprop": "thumbnail",
            "pilicense": "any",
            "pithumbsize": 320,
            "ppprop": "disambiguation|wikibase_item",
            "exintro": 1,
            "explaintext": 1,
            "exchars": 300,
            "exlimit": "max",
        },
    )
    if resp.status_code != 200:
        return [None] * len(titles)
    q = resp.json().get("query") or {}
    norm = {x["from"]: x["to"] for x in q.get("normalized", [])}
    redir = {x["from"]: x["to"] for x in q.get("redirects", [])}
    pages = {p.get("title"): p for p in (q.get("pages") or {}).values()}
    out: list[str | None] = []
    for t in titles:
        page = pages.get(redir.get(norm.get(t, t), norm.get(t, t)))
        thumb = None
        if page and "missing" not in page and "disambiguation" not in (page.get("pageprops") or {}):
            thumb = (page.get("thumbnail") or {}).get("source")
            qid = (page.get("pageprops") or {}).get("wikibase_item")
            if not thumb and etype != "VideoGame" and qid:
                # companies, platforms and series often have no page image: use the Wikidata logo
                thumb = await _wikidata_logo(qid)
            elif thumb and etype == "VideoGame" and "video game)" not in t:
                # a bare title may be a film, a person or a franchise: require a game in the blurb
                blurb = f"{page.get('description', '')} {page.get('extract', '')}".lower()
                if "game" not in blurb:
                    thumb = None
        out.append(thumb)
    return out


_STOP = {"the", "a", "an", "of", "and", "video", "game", "games", "series"}


def _words(text: str) -> set[str]:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return {w for w in re.findall(r"[a-z0-9]+", ascii_text) if w not in _STOP and not re.fullmatch(r"(?:19|20)\d\d", w)}


def match(name: str, title: str) -> tuple[bool, float]:
    """How a Wikipedia title relates to an entity name: (related, similarity).

    Related = the words of one contain the words of the other (the page of "Grand Theft Auto: San Andreas"
    for the game "Grand Theft Auto: San Andreas - The Definitive Edition"); the similarity (Jaccard of the
    words) ranks the related pages, so a sibling page ("Grand Theft Auto III") comes after the right one.
    """
    a, b = _words(name), _words(title)
    if not a or not b:  # names in another script: plain containment
        low = name.lower().split(" (")[0]
        hit = bool(low) and low in title.lower()
        return hit, 1.0 if hit else 0.0
    return (a <= b or b <= a), len(a & b) / len(a | b)


async def _search_ranked(name: str, etype: str, years: list[str]) -> list[tuple[bool, str]]:
    """Search hits with a picture, best match first: [(related, thumbnail url)]."""
    resp = await _get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "generator": "search",
            "gsrlimit": 6,
            "format": "json",
            "gsrsearch": f"{name} {years[0] if years else ''} {_HINT.get(etype, '')}".strip(),
            "prop": "pageimages",
            "piprop": "thumbnail",
            "pilicense": "any",
            "pithumbsize": 320,
        },
    )
    if resp.status_code != 200:
        return []
    pages = (resp.json().get("query") or {}).get("pages") or {}
    hits = []
    for p in pages.values():
        thumb = (p.get("thumbnail") or {}).get("source")
        if thumb:
            related, score = match(name, p.get("title", ""))
            hits.append((not related, -score, p.get("index", 99), thumb))
    hits.sort()
    return [(not not_related, thumb) for not_related, _, _, thumb in hits]


async def _search_thumb(name: str, etype: str, years: list[str]) -> str | None:
    """The best search hit, only if its title is related to the name searched."""
    for related, thumb in await _search_ranked(name, etype, years):
        return thumb if related else None
    return None


async def _find_thumb(name: str, etype: str) -> str | None:
    years = await _years(name, etype)
    for thumb in await _title_thumbs(_titles(name, etype, years), etype):
        if thumb:
            return thumb
    return await _search_thumb(name, etype, years)


async def _download(url: str, stem: str) -> str | None:
    """Fetch the thumbnail into IMAGE_DIR; returns the file name."""
    resp = await _get(url, "img")
    if resp.status_code != 200:
        raise Transient(60)  # a thumbnail the API listed but does not serve: try again much later
    ext = EXT.get(resp.headers.get("content-type", "").split(";")[0].strip())
    if not ext or len(resp.content) > MAX_BYTES:
        raise Transient(600)
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
        # 2. stored URL, file lost or never saved
        entry["file"] = await _download(entry["url"], stem)
        await cache.aset(key, json.dumps(entry), CACHE_TTL_IMAGE)
        return {"imageUrl": local_url(entry["file"]), "source": entry.get("source")}

    # 3. search: only a search that ran to the end without a hitch may end in "not found"
    thumb = await _find_thumb(name, _norm_type(etype))
    if not thumb:
        await cache.aset(key, json.dumps({"miss": True}), IMAGE_MISS_TTL)
        return {"imageUrl": None, "source": None}
    file = await _download(thumb, stem)
    entry = {"url": thumb, "file": file, "source": "wikipedia"}
    await cache.aset(key, json.dumps(entry), CACHE_TTL_IMAGE)
    return {"imageUrl": local_url(file), "source": "wikipedia"}


async def _search_thumbs(name: str, etype: str, years: list[str]) -> list[str]:
    return [thumb for _, thumb in await _search_ranked(name, etype, years)]


async def _candidates(name: str, etype: str) -> list[str]:
    """Every picture Wikipedia offers for this entity: the title variants, then the best search hits
    (all asked at the same time)."""
    years = await _years(name, etype)
    found = await asyncio.gather(
        _title_thumbs(_titles(name, etype, years), etype),
        _search_thumbs(name, etype, years),
        return_exceptions=True,
    )
    for item in found:
        if isinstance(item, Transient):
            raise item  # an incomplete list would hide good candidates
        if isinstance(item, BaseException):
            raise item
    out: list[str] = []
    for item in found:
        for thumb in item if isinstance(item, list) else [item]:
            if thumb and thumb not in out:
                out.append(thumb)
    return out


async def retry(name: str, etype: str = "VideoGame") -> dict:
    """Pick another picture for an entity (the stored one was missing or wrong).

    Each call moves to the next candidate, so repeated retries cycle through them.
    The file gets a new name, so the browser does not keep showing the old one.
    """
    name = name.strip()
    etype = _norm_type(etype)
    key = key_for(name, etype)
    stem = file_stem(key)
    raw = await cache.aget(key)
    entry = json.loads(raw) if raw else {}
    try:
        cands = entry.get("cands") or await _candidates(name, etype)  # kept: later retries are instant
    except Transient as t:
        return {"imageUrl": None, "source": None, "changed": False, "retryAfter": t.retry_after}
    if not cands:
        return {"imageUrl": None, "source": None, "changed": False}
    attempt = int(entry.get("attempt", 0)) + 1
    start = cands.index(entry["url"]) + 1 if entry.get("url") in cands else attempt
    thumb = cands[start % len(cands)]
    try:
        file = await _download(thumb, f"{stem}-{attempt}")
    except Transient as t:
        return {"imageUrl": None, "source": None, "changed": False, "retryAfter": t.retry_after}
    old = entry.get("file")
    if file and old and old != file and (IMAGE_DIR / old).exists():
        await asyncio.to_thread((IMAGE_DIR / old).unlink)
    entry = {
        "url": thumb,
        "file": file,
        "source": "wikipedia",
        "attempt": attempt,
        "cands": cands,
    }
    await cache.aset(key, json.dumps(entry), CACHE_TTL_IMAGE)
    return {
        "imageUrl": local_url(file),
        "source": "wikipedia",
        "changed": True,
    }


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
    except Transient as t:  # nothing was learned: no "not found" is stored, the client asks again later
        return {"imageUrl": None, "source": None, "retryAfter": t.retry_after}
    except Exception as e:  # anything unexpected must never break the graph, nor be remembered
        logger.warning(f"[IMG] {etype} '{name}': {e}")
        return {"imageUrl": None, "source": None, "retryAfter": 30.0}


async def resolve_many(items: list[tuple[str, str]]) -> list[dict]:
    return await asyncio.gather(*(resolve(n, t) for n, t in items))
