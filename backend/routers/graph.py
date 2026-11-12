"""
Graph router — handles knowledge graph visualization and node detail requests.
"""

import logging
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from backend.services.graph_builder import build_graph_from_node, find_cross_links
from backend.services import image_store
from backend.services.ontology_service import OntologyService

logger = logging.getLogger(__name__)

router = APIRouter()


class CrossLinksRequest(BaseModel):
    existing_uris: list[str]
    new_uris: list[str]


@router.post("/cross-links")
async def get_cross_links(body: CrossLinksRequest):
    """
    Given a set of URIs already on the canvas (existing_uris) and newly added
    URIs (new_uris), return all direct relationships between them so the
    frontend can draw the missing edges automatically.
    """
    if not body.new_uris:
        return {"links": []}

    try:
        links = find_cross_links(
            existing_uris=body.existing_uris,
            new_uris=body.new_uris,
            ontology_service=OntologyService,
        )
        return {"links": links}
    except Exception as e:
        logger.exception("Failed to compute cross-links")
        raise HTTPException(status_code=500, detail=str(e))


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
async def search_game_image(name: str, type: str = "VideoGame"):
    """Image for one entity (local file, stored URL or Wikipedia search, see image_store)."""
    if not name.strip():
        raise HTTPException(status_code=400, detail="Name cannot be empty")
    return await image_store.resolve(name, type)


class ImageItem(BaseModel):
    name: str
    type: str = "VideoGame"


class ImagesRequest(BaseModel):
    items: list[ImageItem] = Field(max_length=60)


@router.post("/images")
async def images(body: ImagesRequest):
    """Batch lookup, resolved concurrently. Keys are "<type>|<name>"."""
    found = await image_store.resolve_many([(i.name, i.type) for i in body.items])
    return {
        "images": {f"{i.type}|{i.name}": r["imageUrl"] for i, r in zip(body.items, found)}
    }


@router.get("/image-file/{file}")
async def image_file(file: str):
    path = image_store.image_path(file)
    if path is None or not path.exists():
        raise HTTPException(status_code=404)
    return FileResponse(
        path, headers={"Cache-Control": "public, max-age=31536000, immutable"}
    )


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
