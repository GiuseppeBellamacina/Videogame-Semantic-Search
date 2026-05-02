"""
Query router — handles natural language search requests.
"""

import asyncio
import json
import logging
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.agents.sparql_agent import SPARQLAgent
from backend.config import CACHE_TTL, UPSTASH_REDIS_REST_TOKEN, UPSTASH_REDIS_REST_URL
from backend.services.graph_builder import build_graph_from_results
from backend.services.ontology_service import OntologyService

logger = logging.getLogger(__name__)

router = APIRouter()

# Async Redis client — initialised at startup, None if env vars are not set
_redis = None

# In-memory fallback cache used when Redis is not configured
_memory_cache: dict[str, dict] = {}


def _normalise(question: str) -> str:
    """Lowercase, collapse whitespace — used as cache key."""
    return re.sub(r"\s+", " ", question.strip().lower())


async def init_cache() -> None:
    """Initialise Upstash AsyncRedis client. Falls back to in-memory if env vars are not set."""
    global _redis
    if not UPSTASH_REDIS_REST_URL or not UPSTASH_REDIS_REST_TOKEN:
        logger.info(
            "[CACHE] UPSTASH_REDIS_REST_URL/TOKEN not set — using in-memory fallback cache"
        )
        return
    try:
        from upstash_redis.asyncio import Redis as AsyncRedis  # type: ignore[import]

        _redis = AsyncRedis(url=UPSTASH_REDIS_REST_URL, token=UPSTASH_REDIS_REST_TOKEN)
        await _redis.ping()
        logger.info("[CACHE] Connected to Upstash AsyncRedis")
    except Exception as e:
        logger.warning(
            f"[CACHE] Upstash Redis connection failed, falling back to in-memory: {e}"
        )
        _redis = None


def close_cache() -> None:
    """No-op for Upstash (HTTP-based, no persistent connection)."""
    if _redis:
        logger.info("[CACHE] Upstash Redis client released")


async def _cache_get(key: str) -> dict | None:
    if _redis:
        try:
            value = await _redis.get(f"vg:query:{key}")
            return json.loads(value) if value else None
        except Exception as e:
            logger.warning(f"[CACHE] Redis get error: {e}")
    return _memory_cache.get(key)


async def _cache_set(key: str, value: dict) -> None:
    if _redis:
        try:
            await _redis.set(
                f"vg:query:{key}", json.dumps(value, ensure_ascii=False), ex=CACHE_TTL
            )
            return
        except Exception as e:
            logger.warning(f"[CACHE] Redis set error: {e}")
    _memory_cache[key] = value


class QueryRequest(BaseModel):
    question: str


class QueryResponse(BaseModel):
    results: list[dict]
    graph: dict
    sparql: str
    total_rows: int
    success: bool


@router.post("/query", response_model=QueryResponse)
async def query_ontology(request: QueryRequest):
    """
    Process a natural language question:
    1. Check cache (Redis or in-memory fallback)
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
        # Run blocking agent (OpenAI HTTP + rdflib CPU) off the event loop
        def _run_agent():
            agent = SPARQLAgent()
            state = agent.run(request.question)
            graph_data = {"nodes": [], "links": []}
            if state.results:
                graph_data = build_graph_from_results(state.results, OntologyService)
            return state, graph_data

        state, graph_data = await asyncio.to_thread(_run_agent)

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
