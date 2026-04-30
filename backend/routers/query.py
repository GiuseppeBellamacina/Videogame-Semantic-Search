"""
Query router — handles natural language search requests.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.agents.sparql_agent import SPARQLAgent
from backend.services.graph_builder import build_graph_from_results
from backend.services.ontology_service import OntologyService

logger = logging.getLogger(__name__)

router = APIRouter()


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
    1. Use SPARQL agent to convert NL → SPARQL
    2. Execute query on local ontology
    3. Build knowledge graph from results
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        agent = SPARQLAgent()
        state = agent.run(request.question)

        # Build graph visualization data
        graph_data = {"nodes": [], "links": []}
        if state.results:
            graph_data = build_graph_from_results(state.results, OntologyService)

        return QueryResponse(
            results=state.results,
            graph=graph_data,
            sparql=state.sparql_query,
            total_rows=len(state.results),
            success=state.success,
        )

    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception("Query processing failed")
        raise HTTPException(
            status_code=500,
            detail=f"Internal error processing query: {str(e)}",
        )
