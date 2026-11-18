"""
Query router — handles natural language search requests.
"""

import asyncio
import json
import logging
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.agents.sparql_agent import SPARQLAgent
from backend.config import CACHE_TTL_QUERY, ONTOLOGY_FILE
from backend.services import cache
from backend.services.graph_builder import build_graph
from backend.services.ontology_service import OntologyService

logger = logging.getLogger(__name__)

router = APIRouter()

# Keys are namespaced by the ontology build time, so rebuilding the ontology
# invalidates cached answers automatically.
_PREFIX = (
    f"vg:query:v2:{int(ONTOLOGY_FILE.stat().st_mtime) if ONTOLOGY_FILE.exists() else 0}:"  # v2: node type Company
)

# Normalised questions already cached, for fuzzy matching
_cached_keys: set[str] = set()

# Ready-made questions (backend/presets.json): answered with a stored SPARQL, no LLM call.
# They take part in the same fuzzy matching as the cached questions.
_PRESETS_FILE = Path(__file__).resolve().parent.parent / "presets.json"


def _load_presets() -> dict[str, str]:
    try:
        items = json.loads(_PRESETS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {_normalise(i["question"]): i["sparql"] for i in items}


def _normalise(question: str) -> str:
    """Lowercase, collapse whitespace — used as cache key."""
    return re.sub(r"\s+", " ", question.strip().lower())


PRESETS: dict[str, str] = _load_presets()
_cached_keys.update(PRESETS)

# Max Levenshtein distance for fuzzy matching (relative to query length)
_FUZZY_THRESHOLD_RATIO = 0.2  # 20% of query length


def _levenshtein(s1: str, s2: str) -> int:
    """Compute Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)

    prev_row = list(range(len(s2) + 1))
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            cost = 0 if c1 == c2 else 1
            curr_row.append(
                min(curr_row[j] + 1, prev_row[j + 1] + 1, prev_row[j] + cost)
            )
        prev_row = curr_row

    return prev_row[-1]


def _find_fuzzy_match(key: str) -> str | None:
    """Find the closest cached key within the threshold distance."""
    if not _cached_keys:
        return None

    max_dist = max(2, int(len(key) * _FUZZY_THRESHOLD_RATIO))
    best_key: str | None = None
    best_dist = max_dist + 1

    for cached_key in _cached_keys:
        # Quick length check to skip obvious mismatches
        if abs(len(cached_key) - len(key)) > max_dist:
            continue
        dist = _levenshtein(key, cached_key)
        # a preset is a hand-written question: only typos match, not "serie Halo" -> "serie Zelda"
        if cached_key in PRESETS and dist > 2:
            continue
        if dist < best_dist:
            best_dist = dist
            best_key = cached_key

    return best_key if best_dist <= max_dist else None


async def init_cache() -> None:
    """Load the cached questions (for fuzzy matching) from the SQLite cache."""
    keys = await cache.akeys(_PREFIX)
    _cached_keys.update(k.removeprefix(_PREFIX) for k in keys)
    logger.info(f"[CACHE] Loaded {len(_cached_keys)} cached queries for fuzzy matching")


def close_cache() -> None:
    cache.close()


def _run_preset(sparql: str) -> dict:
    """Execute a stored query like the agent would (rows -> graph)."""
    rows = OntologyService.execute_sparql(sparql)
    graph = build_graph(rows, OntologyService) if rows else {"nodes": [], "links": []}
    return {
        "results": rows,
        "graph": graph,
        "sparql": sparql,
        "total_rows": len(rows),
        "success": bool(rows),
        "truncated": False,
    }


async def _cache_get(key: str) -> dict | None:
    fuzzy_key = None
    for k in (key, None):
        if k is None:
            k = fuzzy_key = _find_fuzzy_match(key)
            if k is None:
                return None
            logger.info(f"[CACHE] Fuzzy hit: '{key}' → '{k}'")
        value = await cache.aget(_PREFIX + k)
        if value:
            return json.loads(value)
        if k in PRESETS:  # first use of a preset: run it, then keep the answer
            response = await asyncio.to_thread(_run_preset, PRESETS[k])
            if response["success"]:
                await _cache_set(k, response)
            return response
    return None


async def _cache_set(key: str, value: dict) -> None:
    _cached_keys.add(key)
    await cache.aset(
        _PREFIX + key, json.dumps(value, ensure_ascii=False), CACHE_TTL_QUERY
    )


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    results: list[dict]
    graph: dict
    sparql: str
    total_rows: int
    success: bool
    truncated: bool = False


def _run_agent(question: str, emit=lambda event: None):
    """Blocking agent run (LLM HTTP + store CPU): call it from a thread."""
    state = SPARQLAgent().run(question, emit)
    graph_data = {"nodes": [], "links": []}
    if state.results:
        emit({"type": "phase", "phase": "building_graph"})
        graph_data = build_graph(state.results, OntologyService)
    return state, graph_data


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


@router.post("/query/stream")
async def query_stream(request: QueryRequest):
    """Same as /query, but streams the agent's progress as server-sent events."""
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    async def events():
        key = _normalise(request.question)
        cached = await _cache_get(key)
        if cached:
            yield _sse({"type": "done", "cached": True, "result": cached})
            return

        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()
        emit = lambda e: loop.call_soon_threadsafe(queue.put_nowait, e)  # noqa: E731
        task = asyncio.create_task(
            asyncio.to_thread(_run_agent, request.question, emit)
        )
        task.add_done_callback(lambda _: queue.put_nowait(None))

        while (event := await queue.get()) is not None:
            yield _sse(event)
        try:
            state, graph_data = task.result()
        except Exception as e:  # incl. missing API key
            logger.exception("Query processing failed")
            yield _sse({"type": "error", "detail": str(e)})
            return

        response = QueryResponse(
            results=state.results,
            graph=graph_data,
            sparql=state.sparql_query,
            total_rows=len(state.results),
            success=state.success,
        ).model_dump()
        if state.success and state.results:
            await _cache_set(key, response)
        yield _sse({"type": "done", "cached": False, "result": response})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/query", response_model=QueryResponse)
async def query_ontology(request: QueryRequest):
    """
    Process a natural language question:
    1. Check cache (SQLite)
    2. Use SPARQL agent to convert NL → SPARQL (run in thread — blocking I/O + CPU)
    3. Execute query on local ontology
    4. Build knowledge graph from results
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    cache_key = _normalise(request.question)
    cached = await _cache_get(cache_key)
    if cached:
        logger.info(f"[CACHE] Hit for: '{cache_key}'")
        return cached

    try:
        state, graph_data = await asyncio.to_thread(_run_agent, request.question)

        response = QueryResponse(
            results=state.results,
            graph=graph_data,
            sparql=state.sparql_query,
            total_rows=len(state.results),
            success=state.success,
        )

        if state.success and state.results:
            await _cache_set(cache_key, response.model_dump())
            logger.info(f"[CACHE] Stored for: '{cache_key}'")
        else:
            logger.info(f"[CACHE] Skipped (no results or failed): '{cache_key}'")
        return response

    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Query processing failed")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error processing query: {str(e)}",
        )
