"""
Service for loading and querying the RDF ontology using pyoxigraph (Rust-based, memory-efficient).
"""

import logging
from typing import Optional

import pyoxigraph as ox

from backend.config import ONTOLOGY_FILE, ONTOLOGY_NS
from backend.services import search_index
from backend.services.image_cache import get_label, get_type, set_label, set_type

logger = logging.getLogger(__name__)

VG_NS = ONTOLOGY_NS
MAX_CONSTRUCT_TRIPLES = 3000
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"


def _derived_first(quad) -> bool:
    """Sort key: False (a real relation) before True (derived by the reasoner: shares.../shared...)."""
    local = quad.predicate.value.rsplit("#", 1)[-1]
    return local.startswith(("shares", "shared"))


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
        cls._build_class_map()
        search_index.build(cls._store)

    # Base types shown in the graph, in priority order (most specific entity first)
    BASE_TYPES = [
        "VideoGame",
        "Company",  # Developer and Publisher are roles of the same individual
        "Genre",
        "Platform",
        "Character",
        "Franchise",
        "Award",
        "GameEngine",
        "GameMode",
        "Review",
        "GameEvent",
    ]
    # Defined game classes (SinglePlayerGame, HighlyRatedGame...) are query
    # shortcuts, not visual types: they always display as VideoGame.
    _DEFINED_GAME_CLASSES = {
        "AwardWinningGame",
        "FranchiseGame",
        "SinglePlayerGame",
        "MultiplayerGame",
        "CoopGame",
        "PCGame",
        "ConsoleGame",
        "MobileGame",
        "NintendoGame",
        "PlayStationGame",
        "XboxGame",
        "SequelGame",
        "StandaloneGame",
        "HighlyRatedGame",
        "RecentGame",
        "MultiConsoleGame",
        "NintendoPublishedGame",
        "GameWithSingleDeveloper",
        "ExclusiveRelease",
    }
    _class_to_base: dict[str, str] = {}

    @classmethod
    def _build_class_map(cls) -> None:
        """Map every subclass (transitively, via rdfs:subClassOf) to its base type."""
        store = cls.get_store()
        sub = ox.NamedNode("http://www.w3.org/2000/01/rdf-schema#subClassOf")
        mapping: dict[str, str] = {}
        for base in reversed(cls.BASE_TYPES):  # higher priority overwrites
            stack = [base]
            while stack:
                parent = stack.pop()
                for quad in store.quads_for_pattern(
                    None, sub, ox.NamedNode(VG_NS + parent)
                ):
                    if isinstance(quad.subject, ox.NamedNode):
                        name = cls._get_local_name(quad.subject.value)
                        if name not in mapping or mapping[name] != base:
                            mapping[name] = base
                            stack.append(name)
            mapping[base] = base
        for name in cls._DEFINED_GAME_CLASSES:
            mapping[name] = "VideoGame"
        cls._class_to_base = mapping

    @classmethod
    def get_store(cls) -> ox.Store:
        """Return the loaded store."""
        if cls._store is None:
            cls.load()
        assert cls._store is not None
        return cls._store

    @classmethod
    def execute_sparql(cls, query: str, max_rows: int | None = None) -> list[dict]:
        """
        Execute a SPARQL query on the local ontology and return results
        as a list of dicts. Deduplicates rows with identical values.
        """
        store = cls.get_store()
        results = store.query(query)

        if isinstance(results, ox.QueryTriples):
            # CONSTRUCT: one row per triple; the graph is built from these in graph_builder
            triples, seen = [], set()
            for t in results:
                row = (
                    t.subject.value,
                    cls._get_local_name(t.predicate.value),
                    t.object.value,
                )
                if row not in seen:
                    seen.add(row)
                    triples.append(
                        {"subject": row[0], "predicate": row[1], "object": row[2]}
                    )
                    if len(triples) >= MAX_CONSTRUCT_TRIPLES:
                        break
            return triples

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
                if max_rows and len(rows) >= max_rows:
                    break

        return rows

    @classmethod
    def get_node_details(cls, uri: str, max_relations: int = 200) -> dict:
        """
        Get triples related to a specific URI (as subject or object).
        Returns properties and relations for a node detail panel.
        Limits outgoing and incoming relations to max_relations each to prevent
        memory issues on highly-connected nodes.
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

        # the real relations (publishedBy...) come first: the derived ones (sharesPublisherWith...) are
        # hundreds for a famous game and must not fill the cap before them
        for quad in sorted(store.quads_for_pattern(node, None, None), key=_derived_first):
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
                if len(outgoing_relations) >= max_relations:
                    continue
                target_type = cls._type_from_predicate(
                    pred_label
                ) or cls._get_node_type(obj.value)
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
        total_incoming = 0
        for quad in sorted(store.quads_for_pattern(None, None, node), key=_derived_first):
            p_str = quad.predicate.value
            pred_label = cls._get_local_name(p_str)
            if p_str in _SKIP_PREDICATES or any(
                p_str.startswith(ns) for ns in _SKIP_NS
            ):
                continue
            subj = quad.subject
            if isinstance(subj, ox.NamedNode):
                total_incoming += 1
                if len(incoming_relations) >= max_relations:
                    continue
                source_type = cls._type_from_predicate(
                    pred_label, inverse=True
                ) or cls._get_node_type(subj.value)
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

        # most specific classes only: drop any class that is an ancestor of another one the node has
        # (the store holds the closure of the instance types, not of the authored TBox)
        sub = ox.NamedNode("http://www.w3.org/2000/01/rdf-schema#subClassOf")

        def ancestors(c: ox.NamedNode) -> set[str]:
            seen: set[str] = set()
            todo = [c]
            while todo:
                for q in store.quads_for_pattern(todo.pop(), sub, None):
                    if isinstance(q.object, ox.NamedNode) and q.object.value not in seen:
                        seen.add(q.object.value)
                        todo.append(q.object)
            seen.discard(c.value)  # a reflexive subClassOf must not hide the class itself
            return seen

        types = {
            q.object
            for q in store.quads_for_pattern(node, ox.NamedNode(RDF_TYPE), None)
            if isinstance(q.object, ox.NamedNode) and q.object.value.startswith(VG_NS)
        }
        covered = set().union(*(ancestors(t) for t in types)) if types else set()
        classes = sorted(
            cls._get_local_name(t.value) for t in types if t.value not in covered
        )

        return {
            "uri": uri,
            "label": cls._get_node_label(uri),
            "type": cls._get_node_type(uri),
            "classes": classes,
            "properties": properties,
            "outgoing_relations": outgoing_relations,
            "incoming_relations": incoming_relations,
            "total_incoming": total_incoming,
            "truncated": total_incoming > max_relations,
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
            "engines": ox.NamedNode(VG_NS + "GameEngine"),
            "game_modes": ox.NamedNode(VG_NS + "GameMode"),
        }

        for name, cls_uri in class_counts.items():
            count = sum(1 for _ in store.quads_for_pattern(None, rdf_type, cls_uri))
            stats[name] = count

        # Derived/inferred class counts
        inferred_counts = {
            "award_winning_games": ox.NamedNode(VG_NS + "AwardWinningGame"),
            "franchise_games": ox.NamedNode(VG_NS + "FranchiseGame"),
            "highly_rated_games": ox.NamedNode(VG_NS + "HighlyRatedGame"),
            "sequel_games": ox.NamedNode(VG_NS + "SequelGame"),
            "multiplayer_games": ox.NamedNode(VG_NS + "MultiplayerGame"),
            "single_player_games": ox.NamedNode(VG_NS + "SinglePlayerGame"),
        }
        for name, cls_uri in inferred_counts.items():
            count = sum(1 for _ in store.quads_for_pattern(None, rdf_type, cls_uri))
            if count > 0:
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
            "reviewerName",
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

        # rdfs:label (GameMode individuals and schema classes)
        rdfs_label = ox.NamedNode("http://www.w3.org/2000/01/rdf-schema#label")
        for quad in store.quads_for_pattern(node, rdfs_label, None):
            label = quad.object.value
            set_label(uri, label)
            return label

        # Fallback: extract from URI
        label = cls._get_local_name(uri)
        set_label(uri, label)
        return label

    @classmethod
    def _get_node_type(cls, uri: str) -> str:
        """Get the type of a node. When multiple types exist, uses priority order."""
        cached = get_type(uri)
        if cached is not None:
            return cached

        store = cls.get_store()
        node = ox.NamedNode(uri)
        rdf_type = ox.NamedNode(RDF_TYPE)

        found_types: list[str] = []
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
            found_types.append(local)

        if not found_types:
            set_type(uri, "Unknown")
            return "Unknown"

        # Collapse every subclass (platform families, genre kinds, defined game
        # classes...) to its base type; pick the highest-priority base type.
        bases = {cls._class_to_base.get(t, t) for t in found_types}
        for t in cls.BASE_TYPES:
            if t in bases:
                set_type(uri, t)
                return t

        result = found_types[0]
        set_type(uri, result)
        return result

    # Map predicate → expected type of target (outgoing) or source (incoming)
    _PRED_TO_TYPE = {
        "hasGenre": "Genre",
        "availableOn": "Platform",
        "hasCharacter": "Character",
        "belongsTo": "Franchise",
        "partOfFranchise": "Franchise",
        "wonAward": "Award",
        "madeWith": "GameEngine",
        "hasGameMode": "GameMode",
        "sequelOf": "VideoGame",
        "hasSequel": "VideoGame",
        "sharedFranchiseWith": "VideoGame",
        "sharesDeveloperWith": "VideoGame",
        "sharesPublisherWith": "VideoGame",
        "sharedGenreWith": "VideoGame",
        "sharedEngineWith": "VideoGame",
        # inverse properties point back to games
        "developerOf": "VideoGame",
        "publisherOf": "VideoGame",
        "appearsIn": "VideoGame",
        "includes": "VideoGame",
        "genreOf": "VideoGame",
        "platformFor": "VideoGame",
        "awardWonBy": "VideoGame",
        "engineUsedIn": "VideoGame",
        "modeInGame": "VideoGame",
    }
    _PRED_TO_SOURCE_TYPE = {
        "appearsIn": "Character",
        "includes": "Franchise",
        "genreOf": "Genre",
        "platformFor": "Platform",
        "awardWonBy": "Award",
        "engineUsedIn": "GameEngine",
        "modeInGame": "GameMode",
        "developedBy": "VideoGame",
        "publishedBy": "VideoGame",
        "hasGenre": "VideoGame",
        "availableOn": "VideoGame",
        "hasCharacter": "VideoGame",
        "belongsTo": "VideoGame",
        "wonAward": "VideoGame",
        "madeWith": "VideoGame",
        "hasGameMode": "VideoGame",
        "sequelOf": "VideoGame",
        "hasSequel": "VideoGame",
        "sharedFranchiseWith": "VideoGame",
        "sharesDeveloperWith": "VideoGame",
        "sharesPublisherWith": "VideoGame",
        "sharedGenreWith": "VideoGame",
        "sharedEngineWith": "VideoGame",
    }

    @classmethod
    def _type_from_predicate(cls, pred_label: str, inverse: bool = False) -> str | None:
        """Infer entity type from the predicate name. Returns None if unknown."""
        if inverse:
            return cls._PRED_TO_SOURCE_TYPE.get(pred_label)
        return cls._PRED_TO_TYPE.get(pred_label)

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

BASE CLASSES:
- vg:VideoGame — A video game
- vg:Company — A company or studio; Developer and Publisher are ROLES of the same individual (a company
  that develops and publishes, like FromSoftware, is ONE individual typed vg:Developer and vg:Publisher)
- vg:Developer — Role of a company that develops games (has vg:developerName)
- vg:Publisher — Role of a company that publishes games (has vg:publisherName)
- vg:Genre — A game genre (e.g., RPG, FPS, Action)
- vg:Platform — A gaming platform (e.g., PlayStation 5, PC, Nintendo Switch)
- vg:Character — A character in a game
- vg:Franchise — A game series/franchise (e.g., Zelda, Dark Souls)
- vg:Award — An award given to a game
- vg:GameEngine — A game engine (e.g., Unreal Engine, Unity)
- vg:GameMode — A mode of play; individuals are typed with one of:
  vg:SinglePlayerMode, vg:MultiplayerMode, vg:CoopMode, vg:MMOMode

PLATFORM / GENRE SUBCLASSES (assigned to platform and genre individuals):
- Platforms: vg:ConsolePlatform (vg:PlayStationPlatform, vg:XboxPlatform, vg:NintendoPlatform),
  vg:PCPlatform (vg:WindowsPlatform, vg:MacOSPlatform, vg:LinuxPlatform),
  vg:MobilePlatform (vg:IOSPlatform, vg:AndroidPlatform), vg:BrowserPlatform, vg:ArcadePlatform,
  vg:RetroComputerPlatform (C64, ZX Spectrum, Atari ST...), vg:VRPlatform
- Genres: vg:ActionGenre, vg:RPGGenre, vg:StrategyGenre, vg:PuzzleGenre, vg:SimulationGenre,
  vg:SportsGenre, vg:RacingGenre, vg:AdventureGenre, vg:HorrorGenre, vg:PlatformerGenre,
  vg:ShooterGenre, vg:CasualGenre, vg:VisualNovelGenre (a genre can have several)
- vg:UnrealEngineFamily (engines), vg:GameOfTheYearAward (awards)

DEFINED / INFERRED GAME CLASSES (already materialised: query them with `?game a vg:Class`,
they are subclasses of VideoGame and much faster than manual joins):
- vg:AwardWinningGame — has won at least one award
- vg:FranchiseGame — belongs to a franchise/series
- vg:SinglePlayerGame / vg:MultiplayerGame / vg:CoopGame — has a game mode of that kind
- vg:PCGame / vg:ConsoleGame / vg:MobileGame — available on that kind of platform
- vg:NintendoGame / vg:PlayStationGame / vg:XboxGame — available on that platform family
- vg:HighlyRatedGame — metacriticScore >= 85
- vg:RecentGame — releaseDate >= 2020-01-01
- vg:SequelGame — is a sequel of another game; vg:StandaloneGame — is not a sequel
- vg:MultiConsoleGame — available on at least two different console platforms
- vg:MultiPlatformGame — available on at least three platforms
- By operating system / platform kind: vg:WindowsGame, vg:MacOSGame, vg:LinuxGame, vg:AndroidGame,
  vg:BrowserGame, vg:ArcadeGame, vg:RetroComputerGame, vg:VRGame
- By publisher: vg:NintendoPublishedGame, vg:SonyPublishedGame (Sony Interactive Entertainment),
  vg:XboxPublishedGame (Xbox Game Studios), vg:BandaiNamcoPublishedGame, vg:SquareEnixPublishedGame,
  vg:ElectronicArtsPublishedGame, vg:KonamiPublishedGame, vg:CapcomPublishedGame
- By genre: vg:ActionGame, vg:RPGGame, vg:StrategyGame, vg:SimulationGame, vg:AdventureGame,
  vg:SportsGame, vg:RacingGame, vg:PuzzleGame, vg:HorrorGame, vg:PlatformerGame, vg:ShooterGame,
  vg:CasualGame, vg:VisualNovelGame
- vg:UnrealEngineGame (made with Unreal Engine), vg:GOTYWinner (won a Game of the Year award),
  vg:JapaneseGame / vg:AmericanGame (countryOfOrigin Japan / United States)

OBJECT PROPERTIES (domain → range) and their inverses:
- vg:developedBy (VideoGame → Developer) — inverse: vg:developerOf
- vg:publishedBy (VideoGame → Publisher) — inverse: vg:publisherOf
- vg:hasGenre (VideoGame → Genre) — inverse: vg:genreOf
- vg:availableOn (VideoGame → Platform) — inverse: vg:platformFor
- vg:hasCharacter (VideoGame → Character) — inverse: vg:appearsIn
- vg:belongsTo (VideoGame → Franchise) — inverse: vg:includes
- vg:wonAward (VideoGame → Award) — inverse: vg:awardWonBy
- vg:madeWith (VideoGame → GameEngine) — inverse: vg:engineUsedIn
- vg:hasGameMode (VideoGame → GameMode individual, NOT a string) — inverse: vg:modeInGame
- vg:sequelOf (VideoGame → VideoGame) — transitive; inverse: vg:hasSequel
  (sequelOf is transitive: a game is a sequelOf all its predecessors)

- vg:subsidiaryOf (Company -> Company) — transitive: a company that belongs to a parent company

INFERRED OBJECT PROPERTIES (materialised; symmetric links between two games):
- vg:sharedFranchiseWith — same franchise (chain belongsTo ∘ includes)
- vg:sharesDeveloperWith — same developer (chain developedBy ∘ developerOf)
- vg:sharesPublisherWith — same publisher (chain publishedBy ∘ publisherOf)
NOTE: very large groups are capped, so these may be incomplete for huge franchises/studios.

DATA PROPERTIES:
- vg:gameName (VideoGame → xsd:string)
- vg:releaseDate (VideoGame → xsd:date) — format "YYYY-MM-DD"
- vg:metacriticScore (VideoGame → xsd:integer) — 0-100
- vg:countryOfOrigin (VideoGame → xsd:string)
- vg:developerName, vg:publisherName, vg:genreName, vg:platformName, vg:characterName,
  vg:franchiseName, vg:awardName, vg:engineName (→ xsd:string) — names of the respective entities
- GameMode individuals have a human-readable name in rdfs:label (e.g., "single-player video game")
- All the *Name properties are subproperties of vg:name

IMPORTANT SPARQL NOTES:
- Always use PREFIX vg: <http://www.videogame-ontology.org/ontology#>
- Always use PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
- Always use PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> when using rdfs:label
- Always use PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
- Use FILTER with CONTAINS or regex for text matching (names may vary)
- releaseDate is xsd:date, use YEAR(?date), MONTH(?date), comparison operators
- Use OPTIONAL for properties that may not exist for all games
- Use DISTINCT to avoid duplicates
- Add ORDER BY and LIMIT for manageable results
- Reasoning is already materialised in the store: inferred classes/properties can be queried directly
"""
