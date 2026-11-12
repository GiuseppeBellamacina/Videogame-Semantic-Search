"""
Autosuggest and assisted query builder endpoints.
"""

import asyncio
import re

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.config import ONTOLOGY_NS
from backend.routers.query import QueryResponse
from backend.services import query_builder, search_index
from backend.services.graph_builder import build_graph
from backend.services.ontology_service import OntologyService
from backend.utils.sparql_validator import validate_sparql

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


# ───────────────────────────── free SPARQL editor ─────────────────────────────
STANDARD_PREFIXES = {
    "vg": ONTOLOGY_NS,
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "wd": "http://www.wikidata.org/entity/",
    "dcterms": "http://purl.org/dc/terms/",
}
EDITOR_MAX_ROWS = 1000
EDITOR_TIMEOUT = 30  # seconds


class SparqlRequest(BaseModel):
    query: str = Field(min_length=1, max_length=10000)


def _with_prefixes(query: str) -> str:
    """Prepend the standard prefixes the query uses but does not declare."""
    body = re.sub(r"#[^\n]*", "", query)  # comments do not count
    missing = [
        f"PREFIX {p}: <{iri}>"
        for p, iri in STANDARD_PREFIXES.items()
        if re.search(rf"(?<![\w:/]){p}:", body)
        and not re.search(rf"PREFIX\s+{p}\s*:", body, re.I)
    ]
    return ("\n".join(missing) + "\n" if missing else "") + query


@router.post("/sparql", response_model=QueryResponse)
async def run_sparql(body: SparqlRequest):
    """Run a query written by the user (read-only: SELECT, CONSTRUCT, ASK, DESCRIBE)."""
    sparql = _with_prefixes(body.query.strip())
    # ASK is recognised from the text, so the query is evaluated only once
    is_ask = bool(
        re.match(
            r"\s*(?:(?:PREFIX|BASE)[^\n]*\n\s*)*ASK\b",
            re.sub(r"#[^\n]*", "", sparql),
            re.I,
        )
    )

    def _run():
        store = OntologyService.get_store()
        if is_ask:
            return [{"result": "true" if bool(store.query(sparql)) else "false"}], False
        rows = OntologyService.execute_sparql(sparql, max_rows=EDITOR_MAX_ROWS)
        return rows, len(rows) >= EDITOR_MAX_ROWS

    # shortcut: a timed-out query keeps running in its thread (pyoxigraph cannot cancel it);
    # fine for one local user, a server would need a worker process to kill
    try:
        rows, truncated = await asyncio.wait_for(
            asyncio.to_thread(_run), timeout=EDITOR_TIMEOUT
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=408,
            detail=f"La query supera i {EDITOR_TIMEOUT} secondi: aggiungi dei filtri o un LIMIT.",
        )
    except (
        SyntaxError
    ) as e:  # pyoxigraph's parser (also rejects UPDATE: the editor is read-only)
        # rdflib words syntax errors better than pyoxigraph; it only runs on the failure path
        _, nicer = validate_sparql(sparql)
        raise HTTPException(status_code=400, detail=f"Sintassi non valida: {nicer or e}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Errore nell'esecuzione: {e}")

    try:
        graph = (
            build_graph(rows, OntologyService)
            if rows and "result" not in rows[0]
            else {"nodes": [], "links": []}
        )
    except Exception:
        graph = {"nodes": [], "links": []}
    return QueryResponse(
        results=rows,
        graph=graph,
        sparql=sparql,
        total_rows=len(rows),
        success=bool(rows),
        truncated=truncated,
    )
