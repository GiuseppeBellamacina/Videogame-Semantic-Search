"""
Games router — allows adding new games to the ontology at runtime.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from rdflib import RDF, XSD, Literal, URIRef

from backend.services.ontology_service import VG, OntologyService

logger = logging.getLogger(__name__)

router = APIRouter()


class NewGameRequest(BaseModel):
    name: str
    release_date: str | None = None
    developer: str | None = None
    publisher: str | None = None
    genres: list[str] = []
    platforms: list[str] = []
    description: str | None = None


def _make_uri(base: str, label: str) -> URIRef:
    """Create a safe URI from a label."""
    safe = label.strip().replace(" ", "_").replace("'", "").replace('"', "")
    safe = "".join(c for c in safe if c.isalnum() or c in "_-.")
    return URIRef(f"{base}{safe}")


@router.post("/games")
async def add_game(req: NewGameRequest):
    """
    Add a new game to the ontology. The game will be available
    for queries immediately (in-memory) without re-populating.
    """
    if not req.name.strip():
        raise HTTPException(status_code=400, detail="Game name cannot be empty")

    g = OntologyService.get_graph()
    ns = str(VG)
    game_uri = _make_uri(ns, req.name)

    # Check if game already exists
    if (game_uri, RDF.type, VG.VideoGame) in g:
        raise HTTPException(status_code=409, detail=f"Game '{req.name}' already exists")

    # Add game
    g.add((game_uri, RDF.type, VG.VideoGame))
    g.add((game_uri, VG.gameName, Literal(req.name, datatype=XSD.string)))

    if req.release_date:
        g.add((game_uri, VG.releaseDate, Literal(req.release_date, datatype=XSD.date)))

    if req.description:
        g.add(
            (
                game_uri,
                VG.gameDescription,
                Literal(req.description, datatype=XSD.string),
            )
        )

    if req.developer:
        dev_uri = _make_uri(ns + "dev/", req.developer)
        g.add((dev_uri, RDF.type, VG.Developer))
        g.add((dev_uri, VG.developerName, Literal(req.developer, datatype=XSD.string)))
        g.add((game_uri, VG.developedBy, dev_uri))

    if req.publisher:
        pub_uri = _make_uri(ns + "pub/", req.publisher)
        g.add((pub_uri, RDF.type, VG.Publisher))
        g.add((pub_uri, VG.publisherName, Literal(req.publisher, datatype=XSD.string)))
        g.add((game_uri, VG.publishedBy, pub_uri))

    for genre_name in req.genres:
        genre_uri = _make_uri(ns + "genre/", genre_name)
        g.add((genre_uri, RDF.type, VG.Genre))
        g.add((genre_uri, VG.genreName, Literal(genre_name, datatype=XSD.string)))
        g.add((game_uri, VG.hasGenre, genre_uri))

    for platform_name in req.platforms:
        platform_uri = _make_uri(ns + "platform/", platform_name)
        g.add((platform_uri, RDF.type, VG.Platform))
        g.add(
            (platform_uri, VG.platformName, Literal(platform_name, datatype=XSD.string))
        )
        g.add((game_uri, VG.availableOn, platform_uri))

    logger.info(f"Added game '{req.name}' to ontology")

    return {
        "success": True,
        "message": f"Game '{req.name}' added successfully",
        "uri": str(game_uri),
    }


@router.get("/games")
async def list_games():
    """List all games in the ontology (name + URI)."""
    g = OntologyService.get_graph()
    games = []
    for s, _, _ in g.triples((None, RDF.type, VG.VideoGame)):
        name = None
        for _, _, o in g.triples((s, VG.gameName, None)):
            name = str(o)
            break
        games.append({"uri": str(s), "name": name or str(s).split("#")[-1]})

    games.sort(key=lambda x: x["name"].lower())
    return {"games": games, "total": len(games)}
