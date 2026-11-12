"""
Autosuggest and assisted query builder endpoints.
"""

import asyncio

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.routers.query import QueryResponse
from backend.services import query_builder, search_index
from backend.services.graph_builder import build_graph
from backend.services.ontology_service import OntologyService

router = APIRouter()


@router.get("/suggest")
async def suggest(
    q: str = Query(..., max_length=100),
    type: str | None = Query(None, description="Comma-separated entity types"),
    limit: int = Query(8, ge=1, le=25),
):
    types = [
        t
        for t in (type or "").split(",")
        if t in search_index.NAME_PROPS or t == "GameMode"
    ]
    return search_index.suggest_text(q, types or None, limit)


@router.get("/builder/schema")
async def builder_schema():
    return query_builder.schema()


class BuilderFilter(BaseModel):
    field: str
    op: str
    value: str | int


class BuilderRequest(BaseModel):
    filters: list[BuilderFilter] = Field(default_factory=list, max_length=12)
    order_by: str = "name"
    limit: int = 50
    output: str = "table"  # table = SELECT, graph = CONSTRUCT


@router.post("/builder/count")
async def builder_count(body: BuilderRequest):
    """How many games match: powers the live preview in the builder."""
    try:
        sparql = query_builder.build(
            [f.model_dump() for f in body.filters], output="count"
        )
    except (query_builder.BuilderError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    rows = await asyncio.to_thread(OntologyService.execute_sparql, sparql)
    return {"count": int(rows[0]["n"]) if rows else 0}


@router.post("/builder/query", response_model=QueryResponse)
async def builder_query(body: BuilderRequest):
    if body.output not in ("table", "graph"):
        raise HTTPException(status_code=400, detail=f"Unknown output '{body.output}'")
    try:
        sparql = query_builder.build(
            [f.model_dump() for f in body.filters], body.order_by, body.limit
        )
    except (query_builder.BuilderError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    def _run():
        nonlocal sparql
        rows = OntologyService.execute_sparql(sparql)
        if body.output == "graph" and rows:
            # relations of the games found: a second, indexed query
            sparql = query_builder.graph_query([r["game"] for r in rows])
            rows = OntologyService.execute_sparql(sparql)
        graph = (
            build_graph(rows, OntologyService) if rows else {"nodes": [], "links": []}
        )
        return rows, graph

    try:
        rows, graph = await asyncio.to_thread(_run)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query failed: {e}")
    return QueryResponse(
        results=rows,
        graph=graph,
        sparql=sparql,
        total_rows=len(rows),
        success=bool(rows),
    )
