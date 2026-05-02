"""
FastAPI application entry point for Videogame Semantic Search.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import CORS_ORIGINS
from backend.routers import graph, query
from backend.services.ontology_service import OntologyService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ontology and initialise cache on startup; close cache on shutdown."""
    logging.basicConfig(level=logging.INFO)
    OntologyService.load()
    await query.init_cache()
    yield
    query.close_cache()


app = FastAPI(
    title="Videogame Semantic Search",
    description="Natural language search over a video game knowledge graph",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query.router, prefix="/api")
app.include_router(graph.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
