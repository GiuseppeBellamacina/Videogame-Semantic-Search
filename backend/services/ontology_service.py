"""
Service for loading and querying the RDF ontology using rdflib.
"""

import logging
from typing import Optional

from rdflib import Graph, Namespace

from backend.config import ONTOLOGY_FILE, ONTOLOGY_NS

logger = logging.getLogger(__name__)

VG = Namespace(ONTOLOGY_NS)


class OntologyService:
    """Singleton service that holds the loaded RDF graph."""

    _graph: Optional[Graph] = None
    _triple_count: int = 0
    _label_cache: dict[str, str] = {}
    _type_cache: dict[str, str] = {}

    @classmethod
    def load(cls):
        """Load the ontology file into an rdflib Graph."""
        cls._graph = Graph()
        cls._graph.bind("vg", VG)

        logger.info(f"Loading ontology from {ONTOLOGY_FILE}")
        cls._graph.parse(str(ONTOLOGY_FILE))
        cls._triple_count = len(cls._graph)
        logger.info(f"Ontology loaded: {cls._triple_count} triples")

    @classmethod
    def get_graph(cls) -> Graph:
        """Return the loaded graph."""
        if cls._graph is None:
            cls.load()
        assert cls._graph is not None
        return cls._graph

    @classmethod
    def execute_sparql(cls, query: str) -> list[dict]:
        """
        Execute a SPARQL query on the local ontology and return results
        as a list of dicts. Deduplicates rows with identical values.
        """
        g = cls.get_graph()
        results = g.query(query)

        rows = []
        seen = set()
        for row in results:
            row_dict = {}
            for var in results.vars or []:
                val = getattr(row, str(var), None)
                row_dict[str(var)] = str(val) if val is not None else None
            # Deduplicate based on frozen dict contents
            row_key = tuple(sorted(row_dict.items()))
            if row_key not in seen:
                seen.add(row_key)
                rows.append(row_dict)

        return rows

    @classmethod
    def get_node_details(cls, uri: str) -> dict:
        """
        Get all triples related to a specific URI (as subject or object).
        Returns properties and relations for a node detail panel.
        """
        from rdflib import URIRef

        g = cls.get_graph()
        node = URIRef(uri)

        properties = {}
        outgoing_relations = []
        incoming_relations = []

        # Triples where this node is the subject
        _SKIP_PREDICATES = {
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "http://www.w3.org/2000/01/rdf-schema#label",
            "http://www.w3.org/2000/01/rdf-schema#subClassOf",
            "http://www.w3.org/2002/07/owl#sameAs",
            "http://www.w3.org/2002/07/owl#equivalentClass",
            "http://www.w3.org/2002/07/owl#equivalentProperty",
        }
        _SKIP_NS = (
            "http://www.w3.org/2002/07/owl#",
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "http://www.w3.org/2000/01/rdf-schema#",
        )

        seen_out: set[tuple] = set()
        seen_in: set[tuple] = set()

        for s, p, o in g.triples((node, None, None)):
            pred_label = cls._get_local_name(str(p))
            if str(p) in _SKIP_PREDICATES or any(
                str(p).startswith(ns) for ns in _SKIP_NS
            ):
                continue
            from rdflib import Literal

            if isinstance(o, Literal):
                # Datatype property
                properties[pred_label] = str(o)
            elif str(o).startswith("http"):
                target_type = cls._get_node_type(str(o))
                target_label = cls._get_node_label(str(o))
                key = (pred_label, str(o))
                if key not in seen_out:
                    seen_out.add(key)
                    outgoing_relations.append(
                        {
                            "predicate": pred_label,
                            "target_uri": str(o),
                            "target_label": target_label,
                            "target_type": target_type,
                        }
                    )

        # Triples where this node is the object
        for s, p, o in g.triples((None, None, node)):
            pred_label = cls._get_local_name(str(p))
            if str(p) in _SKIP_PREDICATES or any(
                str(p).startswith(ns) for ns in _SKIP_NS
            ):
                continue
            source_type = cls._get_node_type(str(s))
            source_label = cls._get_node_label(str(s))
            key = (pred_label, str(s))
            if key not in seen_in:
                seen_in.add(key)
                incoming_relations.append(
                    {
                        "predicate": pred_label,
                        "source_uri": str(s),
                        "source_label": source_label,
                        "source_type": source_type,
                    }
                )

        return {
            "uri": uri,
            "label": cls._get_node_label(uri),
            "type": cls._get_node_type(uri),
            "properties": properties,
            "outgoing_relations": outgoing_relations,
            "incoming_relations": incoming_relations,
        }

    @classmethod
    def get_stats(cls) -> dict:
        """Return statistics about the ontology."""
        g = cls.get_graph()
        from rdflib import RDF

        stats = {"total_triples": len(g)}

        class_counts = {
            "games": VG.VideoGame,
            "developers": VG.Developer,
            "publishers": VG.Publisher,
            "genres": VG.Genre,
            "platforms": VG.Platform,
            "characters": VG.Character,
            "franchises": VG.Franchise,
            "awards": VG.Award,
        }

        for name, cls_uri in class_counts.items():
            count = len(list(g.triples((None, RDF.type, cls_uri))))
            stats[name] = count

        return stats

    @classmethod
    def _get_node_label(cls, uri: str) -> str:
        """Get the best label for a node URI."""
        if uri in cls._label_cache:
            return cls._label_cache[uri]

        from rdflib import URIRef

        g = cls.get_graph()
        node = URIRef(uri)

        # Try name properties
        for name_prop in [
            VG.gameName,
            VG.developerName,
            VG.publisherName,
            VG.genreName,
            VG.platformName,
            VG.characterName,
            VG.franchiseName,
            VG.awardName,
            VG.engineName,
        ]:
            for _, _, o in g.triples((node, name_prop, None)):
                cls._label_cache[uri] = str(o)
                return str(o)

        # Fallback: extract from URI
        label = cls._get_local_name(uri)
        cls._label_cache[uri] = label
        return label

    @classmethod
    def _get_node_type(cls, uri: str) -> str:
        """Get the type of a node."""
        if uri in cls._type_cache:
            return cls._type_cache[uri]

        from rdflib import RDF, URIRef

        g = cls.get_graph()
        node = URIRef(uri)

        for _, _, o in g.triples((node, RDF.type, None)):
            local = cls._get_local_name(str(o))
            # Skip OWL/RDF meta-types that are not meaningful for display
            if local in (
                "Thing",
                "Class",
                "NamedIndividual",
                "Ontology",
                "ObjectProperty",
                "DatatypeProperty",
            ):
                continue
            if "owl" in str(o) or "rdf-schema" in str(o):
                continue
            cls._type_cache[uri] = local
            return local

        cls._type_cache[uri] = "Unknown"
        return "Unknown"

    @classmethod
    def _get_local_name(cls, uri: str) -> str:
        """Extract the local name from a URI."""
        if "#" in uri:
            return uri.split("#")[-1]
        return uri.split("/")[-1]

    @classmethod
    def get_ontology_schema(cls) -> str:
        """Return a human-readable description of the ontology schema for the agent."""
        return """
ONTOLOGY SCHEMA (namespace prefix: vg = <http://www.videogame-ontology.org/ontology#>)

CLASSES:
- vg:VideoGame — A video game
- vg:Developer — A game development studio
- vg:Publisher — A game publisher company
- vg:Genre — A game genre (e.g., RPG, FPS, Action)
- vg:Platform — A gaming platform (e.g., PlayStation 5, PC, Nintendo Switch)
- vg:Character — A character in a game
- vg:Franchise — A game series/franchise (e.g., Zelda, Dark Souls)
- vg:Award — An award given to a game
- vg:GameEngine — A game engine (e.g., Unreal Engine, Unity, GameMaker)

OBJECT PROPERTIES (domain → range):
- vg:developedBy (VideoGame → Developer) — inverse: vg:developerOf
- vg:publishedBy (VideoGame → Publisher) — inverse: vg:publisherOf
- vg:hasGenre (VideoGame → Genre)
- vg:availableOn (VideoGame → Platform)
- vg:hasCharacter (VideoGame → Character) — inverse: vg:appearsIn
- vg:belongsTo (VideoGame → Franchise) — inverse: vg:includes
- vg:wonAward (VideoGame → Award)
- vg:sequelOf (VideoGame → VideoGame)
- vg:madeWith (VideoGame → GameEngine)
- vg:hasGameMode (VideoGame → literal string, e.g., "single-player", "multiplayer")

DATA PROPERTIES:
- vg:gameName (VideoGame → xsd:string) — the name of the game
- vg:gameDescription (VideoGame → xsd:string) — short description/abstract
- vg:releaseDate (VideoGame → xsd:date) — format "YYYY-MM-DD"
- vg:metacriticScore (VideoGame → xsd:integer) — 0-100
- vg:officialWebsite (VideoGame → xsd:anyURI) — official game website
- vg:countryOfOrigin (VideoGame → xsd:string) — country where the game was made
- vg:developerName (Developer → xsd:string)
- vg:publisherName (Publisher → xsd:string)
- vg:genreName (Genre → xsd:string)
- vg:platformName (Platform → xsd:string)
- vg:characterName (Character → xsd:string)
- vg:franchiseName (Franchise → xsd:string)
- vg:awardName (Award → xsd:string)
- vg:awardYear (Award → xsd:integer)
- vg:engineName (GameEngine → xsd:string)

IMPORTANT SPARQL NOTES:
- Always use PREFIX vg: <http://www.videogame-ontology.org/ontology#>
- Always use PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
- Always use PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
- Use FILTER with CONTAINS or regex for text matching (names may vary)
- releaseDate is xsd:date, use YEAR(?date), comparison operators
- Use OPTIONAL for properties that may not exist for all games
- Use DISTINCT to avoid duplicates
- Add ORDER BY and LIMIT for manageable results
"""
