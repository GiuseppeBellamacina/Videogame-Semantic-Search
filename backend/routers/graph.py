"""
Graph router — handles knowledge graph visualization and node detail requests.
"""

import logging
import re
from pathlib import Path
from urllib.parse import quote, unquote

import httpx
from fastapi import APIRouter, HTTPException

IMAGE_DEBUG_DIR = Path(__file__).parent.parent.parent / "debug_images"

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

    logger.info(f"[IMG] Searching image for: '{name}'")

    # Skip Wikidata QIDs (Q followed by digits) — no useful image can be found
    if re.fullmatch(r"Q\d+", name.strip()):
        logger.warning(f"[IMG] Skipping QID label: '{name}'")
        return {"imageUrl": None, "source": None}

    try:
        headers = {
            "User-Agent": "VideogameSemanticSearch/1.0 (https://github.com/GiuseppeBellamacina/Videogame-Semantic-Search; educational project)"
        }
        async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
            # Attempt 1: Wikipedia REST summary API (most reliable for thumbnails)
            for title in [name, f"{name} (video game)"]:
                encoded_title = quote(title, safe="")
                resp = await client.get(
                    f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_title}",
                )
                if resp.status_code == 200:
                    data = resp.json()
                    thumb = data.get("thumbnail", {}).get("source")
                    if thumb:
                        logger.info(
                            f"[IMG] FOUND via REST summary (title='{title}') for '{name}': {thumb}"
                        )
                        await _save_debug_image(client, name, thumb)
                        return {"imageUrl": thumb, "source": "wikipedia"}
                else:
                    logger.info(
                        f"[IMG] REST summary returned {resp.status_code} for title='{title}'"
                    )

            logger.warning(f"[IMG] NOT FOUND for '{name}'")
            return {"imageUrl": None, "source": None}

    except Exception as e:
        logger.warning(f"[IMG] ERROR for '{name}': {e}")
        return {"imageUrl": None, "source": None}


async def _save_debug_image(client: httpx.AsyncClient, name: str, url: str) -> None:
    """Download and save image locally for debug purposes."""
    try:
        IMAGE_DEBUG_DIR.mkdir(exist_ok=True)
        safe_name = re.sub(r'[<>:"/\\|?*]', "_", name)
        ext = url.rsplit(".", 1)[-1].split("?")[0] or "jpg"
        dest = IMAGE_DEBUG_DIR / f"{safe_name}.{ext}"
        img_resp = await client.get(url)
        img_resp.raise_for_status()
        dest.write_bytes(img_resp.content)
        logger.info(f"[IMG] Saved debug image: {dest}")
    except Exception as e:
        logger.warning(f"[IMG] Could not save debug image for '{name}': {e}")


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
