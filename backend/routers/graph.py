"""
Graph router — handles knowledge graph visualization and node detail requests.
"""

import logging
from urllib.parse import unquote

import httpx
from fastapi import APIRouter, HTTPException

from backend.services.graph_builder import build_graph_from_node
from backend.services.ontology_service import OntologyService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/node/{uri:path}")
async def get_node_details(uri: str):
    """
    Get detailed information about a specific node (entity) in the ontology.
    Also returns a subgraph centered on this node for visualization.
    """
    decoded_uri = unquote(uri)

    if not decoded_uri.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid URI format")

    try:
        details = OntologyService.get_node_details(decoded_uri)
        subgraph = build_graph_from_node(decoded_uri, OntologyService)

        return {
            "details": details,
            "graph": subgraph,
        }

    except Exception as e:
        logger.exception(f"Failed to get node details for {decoded_uri}")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching node details: {str(e)}",
        )


@router.get("/image-search")
async def search_game_image(name: str):
    """
    Fallback image search: queries Wikipedia API for a game cover/screenshot
    when no image is stored in the ontology.
    """
    if not name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Use Wikipedia API to get page image by title
            resp = await client.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "titles": name,
                    "prop": "pageimages",
                    "format": "json",
                    "pithumbsize": 300,
                    "redirects": 1,
                },
            )
            data = resp.json()
            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                thumb = page.get("thumbnail", {}).get("source")
                if thumb:
                    return {"imageUrl": thumb, "source": "wikipedia"}

            # Fallback 2: try with " (video game)" suffix
            resp = await client.get(
                "https://en.wikipedia.org/w/api.php",
                params={
                    "action": "query",
                    "titles": f"{name} (video game)",
                    "prop": "pageimages",
                    "format": "json",
                    "pithumbsize": 300,
                    "redirects": 1,
                },
            )
            data = resp.json()
            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                thumb = page.get("thumbnail", {}).get("source")
                if thumb:
                    return {"imageUrl": thumb, "source": "wikipedia"}

        return {"imageUrl": None, "source": None}

    except Exception as e:
        logger.warning(f"Image search failed for '{name}': {e}")
        return {"imageUrl": None, "source": None}


@router.get("/stats")
async def get_ontology_stats():
    """Return statistics about the loaded ontology."""
    try:
        stats = OntologyService.get_stats()
        return stats
    except Exception as e:
        logger.exception("Failed to get ontology stats")
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching stats: {str(e)}",
        )
