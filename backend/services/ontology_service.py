"""
Service for loading and querying the RDF ontology using pyoxigraph (Rust-based, memory-efficient).
"""

import logging
from typing import Optional

import pyoxigraph as ox

from backend.config import ONTOLOGY_FILE, ONTOLOGY_NS
from backend.services.image_cache import get_label, get_type, set_label, set_type

logger = logging.getLogger(__name__)

VG_NS = ONTOLOGY_NS
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"


class OntologyService:
    """Singleton service that holds the loaded RDF graph using pyoxigraph."""

    _store: Optional[ox.Store] = None
    _triple_count: int = 0

    @classmethod
    def load(cls):
        """Load the ontology file into a pyoxigraph Store."""
        cls._store = ox.Store()

        logger.info(f"Loading ontology from {ONTOLOGY_FILE}")
        cls._store.load(
            ONTOLOGY_FILE.read_bytes(),
            ox.RdfFormat.RDF_XML,
        )
        cls._triple_count = len(cls._store)
        logger.info(f"Ontology loaded: {cls._triple_count} triples")

    @classmethod
    def get_store(cls) -> ox.Store:
        """Return the loaded store."""
        if cls._store is None:
            cls.load()
        assert cls._store is not None
        return cls._store

    @classmethod
    def execute_sparql(cls, query: str) -> list[dict]:
        """
        Execute a SPARQL query on the local ontology and return results
        as a list of dicts. Deduplicates rows with identical values.
        """
        store = cls.get_store()
        results = store.query(query)

        variables = [v.value for v in results.variables]
        rows = []
        seen = set()
        for solution in results:
            row_dict = {}
            for var_name in variables:
                val = solution[var_name]
                if val is not None:
                    row_dict[var_name] = (
                        val.value if hasattr(val, "value") else str(val)
                    )
                else:
                    row_dict[var_name] = None
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
        store = cls.get_store()
        node = ox.NamedNode(uri)

        properties = {}
        outgoing_relations = []
        incoming_relations = []

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

        for quad in store.quads_for_pattern(node, None, None):
            p_str = quad.predicate.value
            pred_label = cls._get_local_name(p_str)
            if p_str in _SKIP_PREDICATES or any(
                p_str.startswith(ns) for ns in _SKIP_NS
            ):
                continue

            obj = quad.object
            if isinstance(obj, ox.Literal):
                properties[pred_label] = obj.value
            elif isinstance(obj, ox.NamedNode) and obj.value.startswith("http"):
                target_type = cls._get_node_type(obj.value)
                target_label = cls._get_node_label(obj.value)
                key = (pred_label, obj.value)
                if key not in seen_out:
                    seen_out.add(key)
                    outgoing_relations.append(
                        {
                            "predicate": pred_label,
                            "target_uri": obj.value,
                            "target_label": target_label,
                            "target_type": target_type,
                        }
                    )

        # Triples where this node is the object
        for quad in store.quads_for_pattern(None, None, node):
            p_str = quad.predicate.value
            pred_label = cls._get_local_name(p_str)
            if p_str in _SKIP_PREDICATES or any(
                p_str.startswith(ns) for ns in _SKIP_NS
            ):
                continue
            subj = quad.subject
            if isinstance(subj, ox.NamedNode):
                source_type = cls._get_node_type(subj.value)
                source_label = cls._get_node_label(subj.value)
                key = (pred_label, subj.value)
                if key not in seen_in:
                    seen_in.add(key)
                    incoming_relations.append(
                        {
                            "predicate": pred_label,
                            "source_uri": subj.value,
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
        store = cls.get_store()

        stats = {"total_triples": len(store)}

        rdf_type = ox.NamedNode(RDF_TYPE)
        class_counts = {
            "games": ox.NamedNode(VG_NS + "VideoGame"),
            "developers": ox.NamedNode(VG_NS + "Developer"),
            "publishers": ox.NamedNode(VG_NS + "Publisher"),
            "genres": ox.NamedNode(VG_NS + "Genre"),
            "platforms": ox.NamedNode(VG_NS + "Platform"),
            "characters": ox.NamedNode(VG_NS + "Character"),
            "franchises": ox.NamedNode(VG_NS + "Franchise"),
            "awards": ox.NamedNode(VG_NS + "Award"),
        }

        for name, cls_uri in class_counts.items():
            count = sum(1 for _ in store.quads_for_pattern(None, rdf_type, cls_uri))
            stats[name] = count

        return stats

    @classmethod
    def _get_node_label(cls, uri: str) -> str:
        """Get the best label for a node URI."""
        cached = get_label(uri)
        if cached is not None:
            return cached

        store = cls.get_store()
        node = ox.NamedNode(uri)

        # Try name properties
        name_props = [
            "gameName",
            "developerName",
            "publisherName",
            "genreName",
            "platformName",
            "characterName",
            "franchiseName",
            "awardName",
            "engineName",
        ]
        for prop_name in name_props:
            prop = ox.NamedNode(VG_NS + prop_name)
            for quad in store.quads_for_pattern(node, prop, None):
                label = (
                    quad.object.value
                    if hasattr(quad.object, "value")
                    else str(quad.object)
                )
                set_label(uri, label)
                return label

        # Fallback: extract from URI
        label = cls._get_local_name(uri)
        set_label(uri, label)
        return label

    @classmethod
    def _get_node_type(cls, uri: str) -> str:
        """Get the type of a node."""
        cached = get_type(uri)
        if cached is not None:
            return cached

        store = cls.get_store()
        node = ox.NamedNode(uri)
        rdf_type = ox.NamedNode(RDF_TYPE)

        for quad in store.quads_for_pattern(node, rdf_type, None):
            obj = quad.object
            if not isinstance(obj, ox.NamedNode):
                continue
            local = cls._get_local_name(obj.value)
            if local in (
                "Thing",
                "Class",
                "NamedIndividual",
                "Ontology",
                "ObjectProperty",
                "DatatypeProperty",
            ):
                continue
            if "owl" in obj.value or "rdf-schema" in obj.value:
                continue
            set_type(uri, local)
            return local

        set_type(uri, "Unknown")
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
- vg:releaseDate (VideoGame → xsd:date) — format "YYYY-MM-DD"
- vg:metacriticScore (VideoGame → xsd:integer) — 0-100
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
