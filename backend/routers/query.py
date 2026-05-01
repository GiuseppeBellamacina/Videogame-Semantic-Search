"""
Query router — handles natural language search requests.
"""

import json
import logging
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.agents.sparql_agent import SPARQLAgent
from backend.config import UPSTASH_REDIS_REST_TOKEN, UPSTASH_REDIS_REST_URL
from backend.services.graph_builder import build_graph_from_results
from backend.services.ontology_service import OntologyService

logger = logging.getLogger(__name__)

router = APIRouter()

# Redis client — initialised at startup, None if REDIS_URL is not set
_redis = None

# In-memory fallback cache used when Redis is not configured
_memory_cache: dict[str, dict] = {}

CACHE_TTL = 60 * 60 * 24 * 7  # 7 days in seconds


def _normalise(question: str) -> str:
    """Lowercase, collapse whitespace — used as cache key."""
    return re.sub(r"\s+", " ", question.strip().lower())


def init_cache() -> None:
    """Initialise Upstash Redis client. Falls back to in-memory if env vars are not set."""
    global _redis
    if not UPSTASH_REDIS_REST_URL or not UPSTASH_REDIS_REST_TOKEN:
        logger.info("[CACHE] UPSTASH_REDIS_REST_URL/TOKEN not set — using in-memory fallback cache")
        return
    try:
        from upstash_redis import Redis
        _redis = Redis(url=UPSTASH_REDIS_REST_URL, token=UPSTASH_REDIS_REST_TOKEN)
        _redis.ping()
        logger.info("[CACHE] Connected to Upstash Redis")
    except Exception as e:
        logger.warning(f"[CACHE] Upstash Redis connection failed, falling back to in-memory: {e}")
        _redis = None


def close_cache() -> None:
    """No-op for Upstash (HTTP-based, no persistent connection)."""
    if _redis:
        logger.info("[CACHE] Upstash Redis client released")


def _cache_get(key: str) -> dict | None:
    if _redis:
        try:
            value = _redis.get(f"vg:query:{key}")
            return json.loads(value) if value else None
        except Exception as e:
            logger.warning(f"[CACHE] Redis get error: {e}")
    return _memory_cache.get(key)


def _cache_set(key: str, value: dict) -> None:
    if _redis:
        try:
            _redis.set(f"vg:query:{key}", json.dumps(value, ensure_ascii=False), ex=CACHE_TTL)
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
    2. Use SPARQL agent to convert NL → SPARQL
    3. Execute query on local ontology
    4. Build knowledge graph from results
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    cache_key = _normalise(request.question)
    cached = _cache_get(cache_key)
    if cached:
        logger.info(f"[CACHE] Hit for: '{cache_key}'")
        return cached

    try:
        agent = SPARQLAgent()
        state = agent.run(request.question)

        graph_data = {"nodes": [], "links": []}
        if state.results:
            graph_data = build_graph_from_results(state.results, OntologyService)

        response = QueryResponse(
            results=state.results,
            graph=graph_data,
            sparql=state.sparql_query,
            total_rows=len(state.results),
            success=state.success,
        )

        if state.success and state.results:
            _cache_set(cache_key, response.model_dump())
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
