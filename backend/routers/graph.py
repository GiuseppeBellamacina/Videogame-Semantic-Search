"""
Graph router — handles knowledge graph visualization and node detail requests.
"""

import logging
import re
from urllib.parse import quote, unquote

import httpx
from fastapi import APIRouter, HTTPException

from backend.services.graph_builder import build_graph_from_node
from backend.services.image_cache import get_image, set_image
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


# In-memory cache kept for backward compatibility (image_cache.py is the source of truth)


@router.get("/image-search")
async def search_game_image(name: str):
    """
    Image search via Wikipedia REST summary API.
    Tries the exact title first, then with '(video game)' suffix.
    Results are stored in Upstash Redis (cloud) with local in-memory fallback.
    """
    if not name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty")

    # Skip Wikidata QIDs — no useful image can be found
    if re.fullmatch(r"Q\d+", name.strip()):
        return {"imageUrl": None, "source": None}

    # 1. Check cache (Redis → local)
    cached = await get_image(name)
    if cached is not None:
        logger.debug(f"[IMG] Cache hit for '{name}'")
        return cached

    # 2. Fetch from Wikipedia
    headers = {
        "User-Agent": "VideogameSemanticSearch/1.0 (https://github.com/GiuseppeBellamacina/Videogame-Semantic-Search; educational project)"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
            for title in [name, f"{name} (video game)"]:
                encoded_title = quote(title, safe="")
                resp = await client.get(
                    f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_title}",
                )
                if resp.status_code == 200:
                    thumb = resp.json().get("thumbnail", {}).get("source")
                    if thumb:
                        logger.info(f"[IMG] Found for '{name}': {thumb}")
                        result = {"imageUrl": thumb, "source": "wikipedia"}
                        await set_image(name, result)
                        return result

        logger.info(f"[IMG] Not found for '{name}'")
        return {"imageUrl": None, "source": None}

    except Exception as e:
        logger.warning(f"[IMG] Error for '{name}': {e}")
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
