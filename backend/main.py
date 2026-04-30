"""
FastAPI application entry point for Videogame Semantic Search.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import games, graph, query
from backend.services.ontology_service import OntologyService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ontology on startup."""
    OntologyService.load()
    yield


app = FastAPI(
    title="Videogame Semantic Search",
    description="Natural language search over a video game knowledge graph",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query.router, prefix="/api")
app.include_router(graph.router, prefix="/api")
app.include_router(games.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
