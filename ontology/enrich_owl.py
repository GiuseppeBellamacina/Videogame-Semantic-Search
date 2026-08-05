"""
Enrich existing OWL files with advanced ontology constructs:

  V1 (original):
  - AwardWinningGame   (defined class via equivalentClass + someValuesFrom)
  - FranchiseGame      (defined class via equivalentClass + someValuesFrom)
  - sharedFranchiseWith  (property chain: belongsTo ∘ includes)
  - sharesDeveloperWith  (property chain: developedBy ∘ developerOf)
  - sharesPublisherWith  (property chain: publishedBy ∘ publisherOf)

  V2 (new):
  - 30+ new primitive classes (Platform/Genre/Developer/Publisher subclasses,
    lifecycle states, GameMode, Review, GameEvent, etc.)
  - 15+ new object properties with inverses (genreOf, platformFor, hasSequel,
    awardWonBy, modeInGame, engineUsedIn, partOfFranchise, subsidiaryOf,
    reviewer, reviewedGame, hasReview, reviewOf, eventFor, hasEvent)
  - 8 new datatype properties (hasSteamAppId, hasWikidataId, hasIGDBId,
    reviewScore, reviewDate, reviewerName, eventDate, budgetTier, playerCount)
  - 13 new defined classes (SinglePlayerGame, MultiplayerGame, CoopGame,
    PCGame, ConsoleGame, MobileGame, NintendoGame, PlayStationGame, XboxGame,
    SequelGame, StandaloneGame, HighlyRatedGame, RecentGame,
    GameWithSingleDeveloper, ExclusiveRelease)
  - 12 AllDisjointClasses blocks
  - External alignment (Wikidata + Dublin Core equivalentClass/equivalentProperty)
  - 3 owl:hasKey constraints

These axioms enable OWL-RL reasoning to automatically infer:
  - which games have won awards
  - which games belong to a series
  - which games share a franchise, studio, or publisher
  - which games are single/multiplayer, co-op
  - which games are on PC/console/mobile, and which specific platform families
  - which games are sequels or standalone
  - which games are highly rated or recent (via targeted reasoning)

Usage
-----
    python enrich_owl.py                           # enriches all .owl files in this directory
    python enrich_owl.py videogames_pruned.owl     # enriches a single file
    python enrich_owl.py --reason videogames_pruned.owl
        # enriches AND materialises inferred triples via targeted reasoning
        # Much faster than full OWL-RL: only applies the rules our axioms define.
        # Use --max-group N to cap pairwise links per franchise/dev/pub (default 50).
    python enrich_owl.py --no-v2 video.owl
        # Enriches with V1 axioms only (skips V2 enrichments)
"""

from __future__ import annotations

import logging
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Optional, Union

from rdflib import BNode, Literal, OWL, RDF, RDFS, Graph, Namespace, URIRef
from rdflib.namespace import XSD
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

VG = Namespace("http://www.videogame-ontology.org/ontology#")
WD = Namespace("http://www.wikidata.org/entity/")
DCT = Namespace("http://purl.org/dc/terms/")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _lit(s: str) -> Literal:
    return Literal(s, datatype=XSD.string)


def _blank(g: Graph, props: list[tuple[URIRef, URIRef | BNode | Literal]]) -> BNode:
    """Create a blank node with the given (predicate, object) pairs."""
    bn = BNode()
    for p, o in props:
        g.add((bn, p, o))
    return bn


def _rdf_list(g: Graph, items: list[URIRef | BNode]) -> BNode:
    """Build an rdf:List and return its head blank node."""
    if not items:
        return RDF.nil  # type: ignore[return-value]
    head = BNode()
    current = head
    for i, item in enumerate(items):
        g.add((current, RDF.first, item))
        if i < len(items) - 1:
            nxt = BNode()
            g.add((current, RDF.rest, nxt))
            current = nxt
        else:
            g.add((current, RDF.rest, RDF.nil))
    return head


def _intersection(g: Graph, items: list[URIRef | BNode]) -> BNode:
    """Build an owl:intersectionOf blank node containing an rdf:List."""
    lst = _rdf_list(g, items)
    bn = BNode()
    g.add((bn, OWL.intersectionOf, lst))
    return bn


# ---------------------------------------------------------------------------
# Axiom enrichment
# ---------------------------------------------------------------------------


def _add_axioms(g: Graph) -> int:
    """
    Add the enrichment axioms (V1 + V2) to *g* if they are not already present.
    Returns the number of new triples added.
    """
    before = len(g)

    # ── 1. Defined class: AwardWinningGame ──────────────────────────────────
    awg = VG.AwardWinningGame
    if (awg, RDF.type, OWL.Class) not in g:
        g.add((awg, RDF.type, OWL.Class))
        g.add((awg, RDFS.subClassOf, VG.VideoGame))
        g.add((awg, RDFS.label, _lit("Award Winning Game")))
        g.add(
            (
                awg,
                RDFS.comment,
                _lit(
                    "A video game that has received at least one award. "
                    "Instances are inferred by OWL-RL reasoning."
                ),
            )
        )
        restriction = _blank(
            g,
            [
                (OWL.onProperty, VG.wonAward),
                (OWL.someValuesFrom, VG.Award),
            ],
        )
        intersection = _intersection(g, [VG.VideoGame, restriction])
        equiv_class = _blank(g, [(OWL.intersectionOf, intersection)])
        g.add((awg, OWL.equivalentClass, equiv_class))
        logger.info("  + AwardWinningGame class added")

    # ── 2. Defined class: FranchiseGame ─────────────────────────────────────
    fg = VG.FranchiseGame
    if (fg, RDF.type, OWL.Class) not in g:
        g.add((fg, RDF.type, OWL.Class))
        g.add((fg, RDFS.subClassOf, VG.VideoGame))
        g.add((fg, RDFS.label, _lit("Franchise Game")))
        g.add(
            (
                fg,
                RDFS.comment,
                _lit(
                    "A video game that is part of a franchise or series. "
                    "Instances are inferred by OWL-RL reasoning."
                ),
            )
        )
        restriction = _blank(
            g,
            [
                (OWL.onProperty, VG.belongsTo),
                (OWL.someValuesFrom, VG.Franchise),
            ],
        )
        intersection = _intersection(g, [VG.VideoGame, restriction])
        equiv_class = _blank(g, [(OWL.intersectionOf, intersection)])
        g.add((fg, OWL.equivalentClass, equiv_class))
        logger.info("  + FranchiseGame class added")

    # ── 3. Property: sharedFranchiseWith ────────────────────────────────────
    sfw = VG.sharedFranchiseWith
    if (sfw, RDF.type, OWL.ObjectProperty) not in g:
        g.add((sfw, RDF.type, OWL.ObjectProperty))
        g.add((sfw, RDF.type, OWL.SymmetricProperty))
        g.add((sfw, RDFS.domain, VG.VideoGame))
        g.add((sfw, RDFS.range, VG.VideoGame))
        g.add((sfw, RDFS.label, _lit("shared franchise with")))
        g.add(
            (
                sfw,
                RDFS.comment,
                _lit(
                    "Links two games that belong to the same franchise/series. "
                    "Inferred via property chain: belongsTo ∘ includes."
                ),
            )
        )
        chain = _rdf_list(g, [VG.belongsTo, VG.includes])
        g.add((sfw, OWL.propertyChainAxiom, chain))
        logger.info("  + sharedFranchiseWith property added")

    # ── 4. Property: sharesDeveloperWith ────────────────────────────────────
    sdw = VG.sharesDeveloperWith
    if (sdw, RDF.type, OWL.ObjectProperty) not in g:
        g.add((sdw, RDF.type, OWL.ObjectProperty))
        g.add((sdw, RDF.type, OWL.SymmetricProperty))
        g.add((sdw, RDFS.domain, VG.VideoGame))
        g.add((sdw, RDFS.range, VG.VideoGame))
        g.add((sdw, RDFS.label, _lit("shares developer with")))
        g.add(
            (
                sdw,
                RDFS.comment,
                _lit(
                    "Links two games developed by the same studio. "
                    "Inferred via property chain: developedBy ∘ developerOf."
                ),
            )
        )
        chain = _rdf_list(g, [VG.developedBy, VG.developerOf])
        g.add((sdw, OWL.propertyChainAxiom, chain))
        logger.info("  + sharesDeveloperWith property added")

    # ── 5. Property: sharesPublisherWith ────────────────────────────────────
    spw = VG.sharesPublisherWith
    if (spw, RDF.type, OWL.ObjectProperty) not in g:
        g.add((spw, RDF.type, OWL.ObjectProperty))
        g.add((spw, RDF.type, OWL.SymmetricProperty))
        g.add((spw, RDFS.domain, VG.VideoGame))
        g.add((spw, RDFS.range, VG.VideoGame))
        g.add((spw, RDFS.label, _lit("shares publisher with")))
        g.add(
            (
                spw,
                RDFS.comment,
                _lit(
                    "Links two games published by the same company. "
                    "Inferred via property chain: publishedBy ∘ publisherOf."
                ),
            )
        )
        chain = _rdf_list(g, [VG.publishedBy, VG.publisherOf])
        g.add((spw, OWL.propertyChainAxiom, chain))
        logger.info("  + sharesPublisherWith property added")

    # ── V2 axioms ───────────────────────────────────────────────────────────
    _add_axioms_v2(g)

    return len(g) - before


def _add_axioms_v2(g: Graph) -> int:
    """
    Add V2 enrichment axioms: new primitive classes, object & datatype
    properties, defined classes, disjointness, external alignment, and keys.

    Returns the number of new triples added.
    """
    before = len(g)

    _add_v2_classes(g)
    _add_v2_object_properties(g)
    _add_v2_datatype_properties(g)
    _add_v2_defined_classes(g)
    _add_v2_disjointness(g)
    _add_v2_alignment(g)
    _add_v2_keys(g)

    return len(g) - before


# ───────────────────────────────────────────────────────────────────────────
# V2 helpers
# ───────────────────────────────────────────────────────────────────────────


def _class_decl(
    g: Graph, uri: URIRef, parent: URIRef, label: str, comment: str
) -> None:
    """Declare a primitive class if missing."""
    if (uri, RDF.type, OWL.Class) in g:
        return
    g.add((uri, RDF.type, OWL.Class))
    g.add((uri, RDFS.subClassOf, parent))
    g.add((uri, RDFS.label, _lit(label)))
    g.add((uri, RDFS.comment, _lit(comment)))


def _objprop(
    g: Graph,
    uri: URIRef,
    *,
    domain: Optional[URIRef] = None,
    range_: Optional[URIRef] = None,
    label: str = "",
    comment: str = "",
    inverse_of: Optional[URIRef] = None,
    asymmetric: bool = False,
    irreflexive: bool = False,
    symmetric: bool = False,
    transitive: bool = False,
    functional: bool = False,
) -> None:
    """Declare an object property with type assertions if missing."""
    if (uri, RDF.type, OWL.ObjectProperty) in g:
        return
    g.add((uri, RDF.type, OWL.ObjectProperty))
    if asymmetric:
        g.add((uri, RDF.type, OWL.AsymmetricProperty))
    if irreflexive:
        g.add((uri, RDF.type, OWL.IrreflexiveProperty))
    if symmetric:
        g.add((uri, RDF.type, OWL.SymmetricProperty))
    if transitive:
        g.add((uri, RDF.type, OWL.TransitiveProperty))
    if functional:
        g.add((uri, RDF.type, OWL.FunctionalProperty))
    if domain is not None:
        g.add((uri, RDFS.domain, domain))
    if range_ is not None:
        g.add((uri, RDFS.range, range_))
    if label:
        g.add((uri, RDFS.label, _lit(label)))
    if comment:
        g.add((uri, RDFS.comment, _lit(comment)))
    if inverse_of is not None:
        g.add((uri, OWL.inverseOf, inverse_of))


def _dataprop(
    g: Graph,
    uri: URIRef,
    *,
    domain: Optional[URIRef] = None,
    range_: URIRef = XSD.string,
    label: str = "",
    comment: str = "",
    functional: bool = False,
    inverse_functional: bool = False,
    subproperty_of: Optional[URIRef] = None,
) -> None:
    """Declare a datatype property if missing."""
    if (uri, RDF.type, OWL.DatatypeProperty) in g:
        return
    g.add((uri, RDF.type, OWL.DatatypeProperty))
    if functional:
        g.add((uri, RDF.type, OWL.FunctionalProperty))
    if inverse_functional:
        g.add((uri, RDF.type, OWL.InverseFunctionalProperty))
    if domain is not None:
        g.add((uri, RDFS.domain, domain))
    g.add((uri, RDFS.range, range_))
    if label:
        g.add((uri, RDFS.label, _lit(label)))
    if comment:
        g.add((uri, RDFS.comment, _lit(comment)))
    if subproperty_of is not None:
        g.add((uri, RDFS.subPropertyOf, subproperty_of))


def _defined_class_svf(
    g: Graph, uri: URIRef, parent: URIRef, label: str, comment: str,
    on_prop: URIRef, value: URIRef,
) -> None:
    """Declare a defined class via equivalentClass: parent ∩ (on_prop some value)."""
    if (uri, RDF.type, OWL.Class) in g:
        return
    g.add((uri, RDF.type, OWL.Class))
    g.add((uri, RDFS.subClassOf, parent))
    g.add((uri, RDFS.label, _lit(label)))
    g.add((uri, RDFS.comment, _lit(comment)))
    restriction = _blank(g, [(OWL.onProperty, on_prop), (OWL.someValuesFrom, value)])
    intersection = _intersection(g, [parent, restriction])
    equiv_class = _blank(g, [(OWL.intersectionOf, intersection)])
    g.add((uri, OWL.equivalentClass, equiv_class))


def _disjoint(g: Graph, members: list[URIRef]) -> None:
    """Add an owl:AllDisjointClass block for the given member URIs."""
    member_uris: list[URIRef] = []
    for m in members:
        if isinstance(m, URIRef):
            member_uris.append(m)
    if not member_uris:
        return
    lst = _rdf_list(g, member_uris)
    bn = BNode()
    g.add((bn, RDF.type, OWL.AllDisjointClasses))
    g.add((bn, OWL.members, lst))


# ───────────────────────────────────────────────────────────────────────────
# V2 subsections
# ───────────────────────────────────────────────────────────────────────────


def _add_v2_classes(g: Graph) -> None:
    """Add all V2 primitive classes with hierarchy."""
    added = 0

    # New top-level
    for uri, parent, label, comment in [
        (VG.GameMode, OWL.Thing, "Game Mode", "A mode of play available in a video game"),
        (VG.Review, OWL.Thing, "Review", "A review or critical assessment of a video game"),
        (VG.GameEvent, OWL.Thing, "Game Event", "A lifecycle event pertaining to a video game"),
    ]:
        if (uri, RDF.type, OWL.Class) not in g:
            g.add((uri, RDF.type, OWL.Class))
            g.add((uri, RDFS.label, _lit(label)))
            g.add((uri, RDFS.comment, _lit(comment)))
            added += 1

    # VideoGame subclasses (primitive only)
    for uri, parent, label, comment in [
        (VG.ReleasedGame, VG.VideoGame, "Released Game", "A video game that has been officially released to the public"),
        (VG.EarlyAccessGame, VG.VideoGame, "Early Access Game", "A video game available in early access before full release"),
        (VG.CancelledGame, VG.VideoGame, "Cancelled Game", "A video game whose development was cancelled before release"),
        (VG.DelistedGame, VG.VideoGame, "Delisted Game", "A video game that has been removed from digital storefronts"),
        (VG.IndieGame, VG.VideoGame, "Indie Game", "A video game with a relatively small development budget"),
        (VG.AAAGame, VG.VideoGame, "AAA Game", "A video game produced with a large budget by a major publisher"),
        (VG.GOTYWinner, VG.AwardWinningGame, "Game of the Year Winner", "A video game that has won a Game of the Year award"),
    ]:
        _class_decl(g, uri, parent, label, comment)
        added += 1

    # Platform hierarchy
    platform_tree: list[tuple[URIRef, URIRef, str, str]] = [
        (VG.ConsolePlatform, VG.Platform, "Console Platform", "A dedicated video game console hardware platform"),
        (VG.PlayStationPlatform, VG.ConsolePlatform, "PlayStation Platform", "A platform in the Sony PlayStation family"),
        (VG.XboxPlatform, VG.ConsolePlatform, "Xbox Platform", "A platform in the Microsoft Xbox family"),
        (VG.NintendoPlatform, VG.ConsolePlatform, "Nintendo Platform", "A platform in the Nintendo family"),
        (VG.PCPlatform, VG.Platform, "PC Platform", "A personal computer platform"),
        (VG.WindowsPlatform, VG.PCPlatform, "Windows Platform", "A platform running Microsoft Windows"),
        (VG.MacOSPlatform, VG.PCPlatform, "macOS Platform", "A platform running Apple macOS"),
        (VG.LinuxPlatform, VG.PCPlatform, "Linux Platform", "A platform running Linux"),
        (VG.MobilePlatform, VG.Platform, "Mobile Platform", "A mobile device platform"),
        (VG.IOSPlatform, VG.MobilePlatform, "iOS Platform", "A platform running Apple iOS"),
        (VG.AndroidPlatform, VG.MobilePlatform, "Android Platform", "A platform running Android"),
    ]
    for uri, parent, label, comment in platform_tree:
        _class_decl(g, uri, parent, label, comment)
        added += 1

    # Genre subclasses
    for uri, parent, label, comment in [
        (VG.ActionGenre, VG.Genre, "Action Genre", "A genre emphasizing physical challenges and hand-eye coordination"),
        (VG.RPGGenre, VG.Genre, "RPG Genre", "A role-playing game genre with character progression and narrative focus"),
        (VG.StrategyGenre, VG.Genre, "Strategy Genre", "A genre emphasizing tactical and strategic thinking"),
        (VG.PuzzleGenre, VG.Genre, "Puzzle Genre", "A genre centred on logic puzzles and problem-solving"),
        (VG.SimulationGenre, VG.Genre, "Simulation Genre", "A genre that simulates real-world or fictional systems"),
        (VG.SportsGenre, VG.Genre, "Sports Genre", "A genre simulating traditional sports and athletic competitions"),
        (VG.RacingGenre, VG.Genre, "Racing Genre", "A genre focusing on vehicle-based competition"),
        (VG.AdventureGenre, VG.Genre, "Adventure Genre", "A genre emphasizing exploration and narrative-driven gameplay"),
        (VG.HorrorGenre, VG.Genre, "Horror Genre", "A genre designed to evoke fear, dread, and suspense"),
        (VG.PlatformerGenre, VG.Genre, "Platformer Genre", "A genre focused on navigating platforms and obstacles"),
    ]:
        _class_decl(g, uri, parent, label, comment)
        added += 1

    # Developer subclasses
    for uri, parent, label, comment in [
        (VG.FirstPartyDeveloper, VG.Developer, "First-Party Developer", "A studio owned by or exclusive to a platform holder"),
        (VG.ThirdPartyDeveloper, VG.Developer, "Third-Party Developer", "An independent studio not tied to a specific platform holder"),
        (VG.IndieDeveloper, VG.Developer, "Indie Developer", "A small independent developer without publisher backing"),
    ]:
        _class_decl(g, uri, parent, label, comment)
        added += 1

    # Publisher subclasses
    for uri, parent, label, comment in [
        (VG.FirstPartyPublisher, VG.Publisher, "First-Party Publisher", "A publishing division of a platform holder"),
        (VG.ThirdPartyPublisher, VG.Publisher, "Third-Party Publisher", "An independent publishing company"),
    ]:
        _class_decl(g, uri, parent, label, comment)
        added += 1

    # GameEngine subclasses
    for uri, parent, label, comment in [
        (VG.ProprietaryEngine, VG.GameEngine, "Proprietary Engine", "A privately owned game engine not publicly licensed"),
        (VG.OpenSourceEngine, VG.GameEngine, "Open-Source Engine", "A game engine whose source code is publicly available"),
    ]:
        _class_decl(g, uri, parent, label, comment)
        added += 1

    # Award subclasses
    for uri, parent, label, comment in [
        (VG.IndustryAward, VG.Award, "Industry Award", "An award granted by an industry body or trade association"),
        (VG.EditorialAward, VG.Award, "Editorial Award", "An award granted by an editorial outlet or publication"),
        (VG.UserAward, VG.Award, "User Award", "An award determined by popular user vote"),
    ]:
        _class_decl(g, uri, parent, label, comment)
        added += 1

    # Character subclasses
    for uri, parent, label, comment in [
        (VG.PlayerCharacter, VG.Character, "Player Character", "A character directly controlled by the player"),
        (VG.NonPlayerCharacter, VG.Character, "Non-Player Character", "A character controlled by the game's AI, not by the player"),
    ]:
        _class_decl(g, uri, parent, label, comment)
        added += 1

    # Franchise subclasses
    _class_decl(g, VG.SubFranchise, VG.Franchise, "Sub-Franchise", "A spin-off or sub-series within a larger franchise")
    added += 1

    # GameMode subclasses
    for uri, parent, label, comment in [
        (VG.SinglePlayerMode, VG.GameMode, "Single-Player Mode", "A game mode designed for a single player"),
        (VG.MultiplayerMode, VG.GameMode, "Multiplayer Mode", "A game mode supporting multiple simultaneous players"),
        (VG.CoopMode, VG.GameMode, "Co-op Mode", "A game mode supporting cooperative play among players"),
        (VG.MMOMode, VG.GameMode, "MMO Mode", "A massively multiplayer online game mode"),
    ]:
        _class_decl(g, uri, parent, label, comment)
        added += 1

    # GameEvent subclasses
    for uri, parent, label, comment in [
        (VG.AnnouncementEvent, VG.GameEvent, "Announcement Event", "An event marking the public announcement of a video game"),
        (VG.ReleaseEvent, VG.GameEvent, "Release Event", "An event marking the official release of a video game"),
        (VG.UpdateEvent, VG.GameEvent, "Update Event", "An event marking a major update or patch"),
        (VG.DelistingEvent, VG.GameEvent, "Delisting Event", "An event marking the removal of a game from digital storefronts"),
    ]:
        _class_decl(g, uri, parent, label, comment)
        added += 1

    logger.info(f"  [V2] +{added} new classes added")


def _add_v2_object_properties(g: Graph) -> None:
    """Add new object properties with inverses and type assertions."""
    added = 0

    # genreOf (inverse of hasGenre)
    _objprop(
        g, VG.genreOf, domain=VG.Genre, range_=VG.VideoGame,
        label="genre of", asymmetric=True, irreflexive=True,
        inverse_of=VG.hasGenre,
    ); added += 1

    # platformFor (inverse of availableOn)
    _objprop(
        g, VG.platformFor, domain=VG.Platform, range_=VG.VideoGame,
        label="platform for", asymmetric=True, irreflexive=True,
        inverse_of=VG.availableOn,
    ); added += 1

    # awardWonBy (inverse of wonAward)
    _objprop(
        g, VG.awardWonBy, domain=VG.Award, range_=VG.VideoGame,
        label="award won by", irreflexive=True,
        inverse_of=VG.wonAward,
    ); added += 1

    # hasSequel (inverse of sequelOf)
    _objprop(
        g, VG.hasSequel, domain=VG.VideoGame, range_=VG.VideoGame,
        label="has sequel", asymmetric=True, irreflexive=True,
        inverse_of=VG.sequelOf,
    ); added += 1

    # modeInGame (inverse of hasGameMode)
    _objprop(
        g, VG.modeInGame, domain=VG.GameMode, range_=VG.VideoGame,
        label="mode in game", irreflexive=True,
        inverse_of=VG.hasGameMode,
    ); added += 1

    # engineUsedIn (inverse of madeWith)
    _objprop(
        g, VG.engineUsedIn, domain=VG.GameEngine, range_=VG.VideoGame,
        label="engine used in", asymmetric=True, irreflexive=True,
        inverse_of=VG.madeWith,
    ); added += 1

    # partOfFranchise (transitive)
    _objprop(
        g, VG.partOfFranchise, domain=VG.Franchise, range_=VG.Franchise,
        label="part of franchise",
        comment="Relates a sub-franchise to its parent franchise. Transitive.",
        asymmetric=True, irreflexive=True, transitive=True,
    ); added += 1

    # subsidiaryOf (transitive)
    _objprop(
        g, VG.subsidiaryOf,
        label="subsidiary of",
        comment="Relates a subsidiary company to its parent organisation.",
        asymmetric=True, irreflexive=True, transitive=True,
    ); added += 1

    # Review-related
    _objprop(g, VG.reviewer, domain=VG.Review, label="reviewer",
             comment="The reviewer or outlet that authored the review"); added += 1
    _objprop(g, VG.reviewedGame, domain=VG.Review, range_=VG.VideoGame,
             label="reviewed game", comment="The video game that this review evaluates",
             functional=True, inverse_of=VG.hasReview); added += 1
    _objprop(g, VG.hasReview, domain=VG.VideoGame, range_=VG.Review,
             label="has review", comment="A review written about this video game"); added += 1
    _objprop(g, VG.reviewOf, domain=VG.Review, range_=VG.VideoGame,
             label="review of", comment="The video game this review is about"); added += 1

    # Event-related
    _objprop(g, VG.eventFor, domain=VG.GameEvent, range_=VG.VideoGame,
             label="event for", comment="The video game this event pertains to",
             inverse_of=VG.hasEvent); added += 1
    _objprop(g, VG.hasEvent, domain=VG.VideoGame, range_=VG.GameEvent,
             label="has event", comment="A lifecycle event associated with this game"); added += 1

    # hasGenre: add Asymmetric + inverseOf genreOf
    if (VG.hasGenre, OWL.inverseOf, VG.genreOf) not in g:
        g.add((VG.hasGenre, RDF.type, OWL.AsymmetricProperty))
        g.add((VG.hasGenre, OWL.inverseOf, VG.genreOf)); added += 2

    # hasGameMode: tighten range from rdfs:Resource to GameMode
    if (VG.hasGameMode, RDFS.range, VG.GameMode) not in g:
        g.set((VG.hasGameMode, RDFS.range, VG.GameMode)); added += 1

    # sequelOf: add TransitiveProperty + inverseOf hasSequel
    if (VG.sequelOf, RDF.type, OWL.TransitiveProperty) not in g:
        g.add((VG.sequelOf, RDF.type, OWL.TransitiveProperty)); added += 1
    if (VG.sequelOf, OWL.inverseOf, VG.hasSequel) not in g:
        g.add((VG.sequelOf, OWL.inverseOf, VG.hasSequel)); added += 1

    # wonAward: add inverseOf awardWonBy
    if (VG.wonAward, OWL.inverseOf, VG.awardWonBy) not in g:
        g.add((VG.wonAward, OWL.inverseOf, VG.awardWonBy)); added += 1

    # availableOn: add inverseOf platformFor
    if (VG.availableOn, OWL.inverseOf, VG.platformFor) not in g:
        g.add((VG.availableOn, OWL.inverseOf, VG.platformFor)); added += 1

    # madeWith: add Asymmetric + inverseOf engineUsedIn
    if (VG.madeWith, RDF.type, OWL.AsymmetricProperty) not in g:
        g.add((VG.madeWith, RDF.type, OWL.AsymmetricProperty)); added += 1
    if (VG.madeWith, OWL.inverseOf, VG.engineUsedIn) not in g:
        g.add((VG.madeWith, OWL.inverseOf, VG.engineUsedIn)); added += 1

    # hasGameMode: add inverseOf modeInGame
    if (VG.hasGameMode, OWL.inverseOf, VG.modeInGame) not in g:
        g.add((VG.hasGameMode, OWL.inverseOf, VG.modeInGame)); added += 1

    logger.info(f"  [V2] +{added} object property axioms added")


def _add_v2_datatype_properties(g: Graph) -> None:
    """Add new datatype properties."""
    added = 0

    props: list[tuple[URIRef, Optional[URIRef], URIRef, str, str, bool, bool, Optional[URIRef]]] = [
        (VG.hasSteamAppId, VG.VideoGame, XSD.string, "Steam App ID",
         "The unique Steam application identifier", True, True, None),
        (VG.hasWikidataId, None, XSD.string, "Wikidata ID",
         "The Wikidata entity identifier", False, True, None),
        (VG.hasIGDBId, VG.VideoGame, XSD.string, "IGDB ID",
         "The Internet Game Database identifier", False, True, None),
        (VG.reviewScore, VG.Review, XSD.integer, "review score",
         "The numerical score given by this review", True, False, None),
        (VG.reviewDate, VG.Review, XSD.date, "review date",
         "The date on which this review was published", False, False, None),
        (VG.reviewerName, VG.Review, XSD.string, "reviewer name",
         "The name of the reviewer or outlet", False, False, None),
        (VG.eventDate, VG.GameEvent, XSD.date, "event date",
         "The date on which this lifecycle event occurred", False, False, None),
        (VG.budgetTier, VG.VideoGame, XSD.string, "budget tier",
         "The budget tier classification (e.g. indie, AA, AAA)", False, False, None),
        (VG.playerCount, VG.VideoGame, XSD.integer, "player count",
         "The estimated total number of players", False, False, None),
    ]
    for uri, dom, rng, lbl, cmt, func, invfunc, sup in props:
        _dataprop(g, uri, domain=dom, range_=rng, label=lbl, comment=cmt,
                   functional=func, inverse_functional=invfunc, subproperty_of=sup)
        added += 1

    # releaseDate: add FunctionalProperty
    if (VG.releaseDate, RDF.type, OWL.FunctionalProperty) not in g:
        g.add((VG.releaseDate, RDF.type, OWL.FunctionalProperty)); added += 1

    # metacriticScore: add FunctionalProperty
    if (VG.metacriticScore, RDF.type, OWL.FunctionalProperty) not in g:
        g.add((VG.metacriticScore, RDF.type, OWL.FunctionalProperty)); added += 1

    logger.info(f"  [V2] +{added} datatype property axioms added")


def _add_v2_defined_classes(g: Graph) -> None:
    """Add defined classes with equivalentClass (or subClassOf for necessary-only)."""
    added = 0

    # --- someValuesFrom defined classes (equivalentClass) ---
    defined: list[tuple[URIRef, str, str, URIRef, URIRef]] = [
        (VG.MultiplayerGame, "Multiplayer Game",
         "A video game that supports a multiplayer game mode",
         VG.hasGameMode, VG.MultiplayerMode),
        (VG.SinglePlayerGame, "Single-Player Game",
         "A video game that supports a single-player game mode",
         VG.hasGameMode, VG.SinglePlayerMode),
        (VG.CoopGame, "Co-op Game",
         "A video game that supports a cooperative game mode",
         VG.hasGameMode, VG.CoopMode),
        (VG.PCGame, "PC Game",
         "A video game available on a PC platform",
         VG.availableOn, VG.PCPlatform),
        (VG.ConsoleGame, "Console Game",
         "A video game available on a console platform",
         VG.availableOn, VG.ConsolePlatform),
        (VG.MobileGame, "Mobile Game",
         "A video game available on a mobile platform",
         VG.availableOn, VG.MobilePlatform),
        (VG.NintendoGame, "Nintendo Game",
         "A video game available on a Nintendo platform",
         VG.availableOn, VG.NintendoPlatform),
        (VG.PlayStationGame, "PlayStation Game",
         "A video game available on a PlayStation platform",
         VG.availableOn, VG.PlayStationPlatform),
        (VG.XboxGame, "Xbox Game",
         "A video game available on an Xbox platform",
         VG.availableOn, VG.XboxPlatform),
        (VG.SequelGame, "Sequel Game",
         "A video game that is a sequel to another game",
         VG.sequelOf, VG.VideoGame),
    ]
    for uri, lbl, cmt, prop, val in defined:
        _defined_class_svf(g, uri, VG.VideoGame, lbl,
                           cmt + ". Inferred by OWL-RL reasoning.",
                           prop, val)
        added += 1

    # StandaloneGame: VideoGame ∩ ¬(∃sequelOf.VideoGame)
    sga = VG.StandaloneGame
    if (sga, RDF.type, OWL.Class) not in g:
        g.add((sga, RDF.type, OWL.Class))
        g.add((sga, RDFS.subClassOf, VG.VideoGame))
        g.add((sga, RDFS.label, _lit("Standalone Game")))
        g.add((sga, RDFS.comment,
               _lit("A video game that is not a sequel to any other game. Requires negation-as-failure in materialiser.")))
        restriction = _blank(g, [(OWL.onProperty, VG.sequelOf),
                                  (OWL.someValuesFrom, VG.VideoGame)])
        complement = _blank(g, [(OWL.complementOf, restriction)])
        intersection = _intersection(g, [VG.VideoGame, complement])
        equiv_class = _blank(g, [(OWL.intersectionOf, intersection)])
        g.add((sga, OWL.equivalentClass, equiv_class))
        added += 1

    # HighlyRatedGame: datatype restriction metacriticScore >= 85
    hrg = VG.HighlyRatedGame
    if (hrg, RDF.type, OWL.Class) not in g:
        g.add((hrg, RDF.type, OWL.Class))
        g.add((hrg, RDFS.subClassOf, VG.VideoGame))
        g.add((hrg, RDFS.label, _lit("Highly Rated Game")))
        g.add((hrg, RDFS.comment,
               _lit("A video game with a Metacritic score of 85 or above. Inferred via CONSTRUCT reasoning.")))
        facet_bn = _blank(g, [(XSD.minInclusive,
                                Literal(85, datatype=XSD.integer))])
        restrictions_list = _rdf_list(g, [facet_bn])
        dt_bn = _blank(g, [(OWL.onDatatype, XSD.integer),
                            (OWL.withRestrictions, restrictions_list)])
        restriction = _blank(g, [(OWL.onProperty, VG.metacriticScore),
                                  (OWL.someValuesFrom, dt_bn)])
        intersection = _intersection(g, [VG.VideoGame, restriction])
        equiv_class = _blank(g, [(OWL.intersectionOf, intersection)])
        g.add((hrg, OWL.equivalentClass, equiv_class))
        added += 1

    # RecentGame: datatype restriction releaseDate >= 2020-01-01
    rg = VG.RecentGame
    if (rg, RDF.type, OWL.Class) not in g:
        g.add((rg, RDF.type, OWL.Class))
        g.add((rg, RDFS.subClassOf, VG.VideoGame))
        g.add((rg, RDFS.label, _lit("Recent Game")))
        g.add((rg, RDFS.comment,
               _lit("A video game released on or after 2020-01-01. Inferred via CONSTRUCT reasoning.")))
        facet_bn = _blank(g, [(XSD.minInclusive,
                                Literal("2020-01-01", datatype=XSD.date))])
        restrictions_list = _rdf_list(g, [facet_bn])
        dt_bn = _blank(g, [(OWL.onDatatype, XSD.date),
                            (OWL.withRestrictions, restrictions_list)])
        restriction = _blank(g, [(OWL.onProperty, VG.releaseDate),
                                  (OWL.someValuesFrom, dt_bn)])
        intersection = _intersection(g, [VG.VideoGame, restriction])
        equiv_class = _blank(g, [(OWL.intersectionOf, intersection)])
        g.add((rg, OWL.equivalentClass, equiv_class))
        added += 1

    # GameWithSingleDeveloper (necessary only: subClassOf, maxCardinality 1)
    gsd = VG.GameWithSingleDeveloper
    if (gsd, RDF.type, OWL.Class) not in g:
        g.add((gsd, RDF.type, OWL.Class))
        g.add((gsd, RDFS.subClassOf, VG.VideoGame))
        g.add((gsd, RDFS.label, _lit("Game with Single Developer")))
        g.add((gsd, RDFS.comment,
               _lit("A video game developed by at most one developer studio. Necessary condition only.")))
        restriction = _blank(g, [(OWL.onProperty, VG.developedBy),
                                  (OWL.maxCardinality,
                                   Literal(1, datatype=XSD.nonNegativeInteger))])
        g.add((gsd, RDFS.subClassOf, restriction))
        added += 1

    # ExclusiveRelease (necessary only: subClassOf, maxCardinality 1)
    exr = VG.ExclusiveRelease
    if (exr, RDF.type, OWL.Class) not in g:
        g.add((exr, RDF.type, OWL.Class))
        g.add((exr, RDFS.subClassOf, VG.VideoGame))
        g.add((exr, RDFS.label, _lit("Exclusive Release")))
        g.add((exr, RDFS.comment,
               _lit("A video game available on at most one platform. Necessary condition only.")))
        restriction = _blank(g, [(OWL.onProperty, VG.availableOn),
                                  (OWL.maxCardinality,
                                   Literal(1, datatype=XSD.nonNegativeInteger))])
        g.add((exr, RDFS.subClassOf, restriction))
        added += 1

    logger.info(f"  [V2] +{added} defined class axioms added")


def _add_v2_disjointness(g: Graph) -> None:
    """Add AllDisjointClasses blocks."""
    added = 0

    blocks: list[list[URIRef]] = [
        # Top entity classes
        [VG.VideoGame, VG.Developer, VG.Publisher, VG.Genre, VG.Platform,
         VG.Character, VG.Franchise, VG.Award, VG.GameEngine, VG.GameMode,
         VG.Review, VG.GameEvent],
        # Platform partition
        [VG.ConsolePlatform, VG.PCPlatform, VG.MobilePlatform],
        # ConsolePlatform sub-partition
        [VG.PlayStationPlatform, VG.XboxPlatform, VG.NintendoPlatform],
        # PCPlatform sub-partition
        [VG.WindowsPlatform, VG.MacOSPlatform, VG.LinuxPlatform],
        # MobilePlatform sub-partition
        [VG.IOSPlatform, VG.AndroidPlatform],
        # Award partition
        [VG.IndustryAward, VG.EditorialAward, VG.UserAward],
        # Character partition
        [VG.PlayerCharacter, VG.NonPlayerCharacter],
        # GameEngine partition
        [VG.ProprietaryEngine, VG.OpenSourceEngine],
        # Lifecycle states
        [VG.ReleasedGame, VG.EarlyAccessGame, VG.CancelledGame, VG.DelistedGame],
        # Budget scope
        [VG.IndieGame, VG.AAAGame],
        # GameMode partition
        [VG.SinglePlayerMode, VG.MultiplayerMode, VG.CoopMode, VG.MMOMode],
        # GameEvent partition
        [VG.AnnouncementEvent, VG.ReleaseEvent, VG.UpdateEvent, VG.DelistingEvent],
    ]

    for members in blocks:
        # Check if any member is already in an AllDisjointClasses
        sample = members[0]
        already = any((None, OWL.members, None) in g for _ in [sample])
        if not already:
            _disjoint(g, members)
            added += 1

    logger.info(f"  [V2] +{added} AllDisjointClasses blocks added")


def _add_v2_alignment(g: Graph) -> None:
    """Add external alignment (Wikidata + Dublin Core)."""
    added = 0

    # Class alignments
    alignments: list[tuple[URIRef, URIRef]] = [
        (VG.VideoGame, WD.Q7889),
        (VG.Developer, WD.Q210167),
        (VG.GameEngine, WD.Q193564),
        (VG.Genre, WD.Q65956376),
    ]
    for vg_cls, wd_entity in alignments:
        t = (vg_cls, OWL.equivalentClass, wd_entity)
        if t not in g:
            g.add(t)
            added += 1

    # Property alignments
    prop_align: list[tuple[URIRef, URIRef]] = [
        (VG.releaseDate, DCT.issued),
        (VG.gameName, DCT.title),
        (VG.gameDescription, DCT.description),
    ]
    for vg_prop, dc_prop in prop_align:
        t = (vg_prop, OWL.equivalentProperty, dc_prop)
        if t not in g:
            g.add(t)
            added += 1

    logger.info(f"  [V2] +{added} external alignment axioms added")


def _add_v2_keys(g: Graph) -> None:
    """Add owl:hasKey constraints."""
    added = 0

    # VideoGame hasKey hasWikidataId
    key1 = (VG.VideoGame, OWL.hasKey, None)
    already1 = any(s == VG.VideoGame and p == OWL.hasKey for s, p, _ in g)
    if not already1:
        lst = _rdf_list(g, [VG.hasWikidataId])
        g.add((VG.VideoGame, OWL.hasKey, lst))
        added += 1

    # VideoGame hasKey hasSteamAppId
    # Check separately since hasKey creates blank nodes
    key2_present = False
    for s, p, o in g.triples((VG.VideoGame, OWL.hasKey, None)):
        items: list[URIRef] = []
        current = o
        while current and current != RDF.nil:
            first_val = list(g.objects(current, RDF.first))
            if first_val and first_val[0] == VG.hasSteamAppId:
                key2_present = True
                break
            rest = list(g.objects(current, RDF.rest))
            current = rest[0] if rest else None
    if not key2_present:
        lst = _rdf_list(g, [VG.hasSteamAppId])
        g.add((VG.VideoGame, OWL.hasKey, lst))
        added += 1

    # Review hasKey (reviewedGame, reviewerName)
    already_review_key = any(s == VG.Review and p == OWL.hasKey for s, p, _ in g)
    if not already_review_key:
        lst = _rdf_list(g, [VG.reviewedGame, VG.reviewerName])
        g.add((VG.Review, OWL.hasKey, lst))
        added += 1

    logger.info(f"  [V2] +{added} hasKey constraints added")


# ---------------------------------------------------------------------------
# DL-only axiom management (owlrl safety)
# ---------------------------------------------------------------------------


# Set of DatatypeProperty URIs that have FunctionalProperty in DL-only section
_DL_FUNCTIONAL_DATAPROPS: set[URIRef] = {
    VG.gameName,
    VG.developerName,
    VG.publisherName,
    VG.genreName,
    VG.platformName,
    VG.characterName,
    VG.franchiseName,
    VG.awardName,
    VG.engineName,
    VG.releaseDate,
    VG.metacriticScore,
    VG.hasSteamAppId,
    VG.reviewScore,
}

# Set of DatatypeProperty URIs that have InverseFunctionalProperty in DL-only section
_DL_INVERSE_FUNCTIONAL_DATAPROPS: set[URIRef] = {
    VG.hasSteamAppId,
    VG.hasWikidataId,
    VG.hasIGDBId,
}


def strip_dl_only_axioms(g: Graph) -> int:
    """Remove FunctionalProperty/InverseFunctionalProperty on DatatypeProperty
    and owl:hasKey axioms that cause false owl:sameAs in owlrl.

    These axioms are moved to the DL-only section of the OWL file and must be
    stripped before owlrl DeductiveClosure materialisation.

    Returns the number of triples removed.
    """
    removed = 0

    # Remove FunctionalProperty type assertions on datatype properties
    for prop in _DL_FUNCTIONAL_DATAPROPS:
        t = (prop, RDF.type, OWL.FunctionalProperty)
        if t in g:
            g.remove(t)
            removed += 1

    # Remove InverseFunctionalProperty type assertions on datatype properties
    for prop in _DL_INVERSE_FUNCTIONAL_DATAPROPS:
        t = (prop, RDF.type, OWL.InverseFunctionalProperty)
        if t in g:
            g.remove(t)
            removed += 1

    # Remove owl:hasKey on VideoGame and Review
    key_subjects = {VG.VideoGame, VG.Review}
    for s in key_subjects:
        for p, o in list(g.predicate_objects(s)):
            if p == OWL.hasKey:
                g.remove((s, OWL.hasKey, o))
                removed += 1

    if removed > 0:
        logger.info(f"  Stripped {removed} DL-only axioms (owlrl safety)")
    return removed


def restore_dl_only_axioms(g: Graph) -> int:
    """Re-add FunctionalProperty/InverseFunctionalProperty on DatatypeProperty
    and owl:hasKey axioms that were stripped by strip_dl_only_axioms.

    Idempotent: skips triples already present.

    Returns the number of triples added.
    """
    added = 0

    # Restore FunctionalProperty type assertions
    for prop in _DL_FUNCTIONAL_DATAPROPS:
        t = (prop, RDF.type, OWL.FunctionalProperty)
        if t not in g:
            g.add(t)
            added += 1

    # Restore InverseFunctionalProperty type assertions
    for prop in _DL_INVERSE_FUNCTIONAL_DATAPROPS:
        t = (prop, RDF.type, OWL.InverseFunctionalProperty)
        if t not in g:
            g.add(t)
            added += 1

    # Restore owl:hasKey on VideoGame (hasWikidataId)
    key1_exists = False
    for _s, _p, o in g.triples((VG.VideoGame, OWL.hasKey, None)):
        current = o
        while current and current != RDF.nil:
            first = list(g.objects(current, RDF.first))
            if first and first[0] == VG.hasWikidataId:
                key1_exists = True
                break
            rest = list(g.objects(current, RDF.rest))
            current = rest[0] if rest else None
    if not key1_exists:
        lst = _rdf_list(g, [VG.hasWikidataId])
        g.add((VG.VideoGame, OWL.hasKey, lst))
        added += 1

    # Restore owl:hasKey on VideoGame (hasSteamAppId)
    key2_exists = False
    for _s, _p, o in g.triples((VG.VideoGame, OWL.hasKey, None)):
        current = o
        while current and current != RDF.nil:
            first = list(g.objects(current, RDF.first))
            if first and first[0] == VG.hasSteamAppId:
                key2_exists = True
                break
            rest = list(g.objects(current, RDF.rest))
            current = rest[0] if rest else None
    if not key2_exists:
        lst = _rdf_list(g, [VG.hasSteamAppId])
        g.add((VG.VideoGame, OWL.hasKey, lst))
        added += 1

    # Restore owl:hasKey on Review (reviewedGame, reviewerName)
    key3_exists = False
    for _s, _p, o in g.triples((VG.Review, OWL.hasKey, None)):
        current = o
        while current and current != RDF.nil:
            first = list(g.objects(current, RDF.first))
            if first and first[0] == VG.reviewedGame:
                key3_exists = True
                break
            rest = list(g.objects(current, RDF.rest))
            current = rest[0] if rest else None
    if not key3_exists:
        lst = _rdf_list(g, [VG.reviewedGame, VG.reviewerName])
        g.add((VG.Review, OWL.hasKey, lst))
        added += 1

    if added > 0:
        logger.info(f"  Restored {added} DL-only axioms")
    return added


# ---------------------------------------------------------------------------
# Targeted materialiser (replaces full OWL-RL)
# ---------------------------------------------------------------------------


def _materialise(g: Graph, max_group: int = 50) -> int:
    """
    Apply inference rules with tqdm progress bars.

    Rules:
      1. AwardWinningGame  ← game wonAward _:x
      2. FranchiseGame     ← game belongsTo _:f
      3. sharedFranchiseWith (chain belongsTo ∘ includes)   — symmetric
      4. sharesDeveloperWith (chain developedBy ∘ developerOf) — symmetric
      5. sharesPublisherWith (chain publishedBy ∘ publisherOf) — symmetric
      6. MultiplayerGame / SinglePlayerGame / CoopGame ← game hasGameMode :Mode
      7. PCGame / ConsoleGame / MobileGame ← game availableOn :PlatformType
      8. NintendoGame / PlayStationGame / XboxGame ← finer platform classification
      9. HighlyRatedGame ← game metacriticScore >= 85
     10. RecentGame ← game releaseDate >= 2020-01-01
     11. SequelGame ← game sequelOf _:x
     12. StandaloneGame ← VideoGame without sequelOf

    Groups larger than *max_group* games (same franchise/dev/pub) are skipped
    for the pairwise rules to avoid combinatorial explosion; a warning is logged.
    """
    added = 0

    # ── 1 & 2: class membership (from existing rules) ──────────────────────
    award_games: set[URIRef] = set()
    franchise_games: set[URIRef] = set()
    multiplayer_games: set[URIRef] = set()
    singleplayer_games: set[URIRef] = set()
    coop_games: set[URIRef] = set()

    for s, p, o in g.triples((None, VG.wonAward, None)):
        if isinstance(s, URIRef):
            award_games.add(s)
    for s, p, o in g.triples((None, VG.belongsTo, None)):
        if isinstance(s, URIRef):
            franchise_games.add(s)

    # ── 6: GameMode classification ─────────────────────────────────────────
    for s, p, o in g.triples((None, VG.hasGameMode, None)):
        if isinstance(s, URIRef) and isinstance(o, URIRef):
            if o == VG.MultiplayerMode:
                multiplayer_games.add(s)
            elif o == VG.SinglePlayerMode:
                singleplayer_games.add(s)
            elif o == VG.CoopMode:
                coop_games.add(s)

    total_class = (len(award_games) + len(franchise_games) +
                   len(multiplayer_games) + len(singleplayer_games) +
                   len(coop_games))
    with tqdm(
        total=total_class, desc="  [1/5] Class membership",
        unit="game", ncols=80, leave=True,
    ) as pbar:
        for game in award_games:
            t = (game, RDF.type, VG.AwardWinningGame)
            if t not in g:
                g.add(t); added += 1
            pbar.update(1)
        for game in franchise_games:
            t = (game, RDF.type, VG.FranchiseGame)
            if t not in g:
                g.add(t); added += 1
            pbar.update(1)
        for game in multiplayer_games:
            t = (game, RDF.type, VG.MultiplayerGame)
            if t not in g:
                g.add(t); added += 1
            pbar.update(1)
        for game in singleplayer_games:
            t = (game, RDF.type, VG.SinglePlayerGame)
            if t not in g:
                g.add(t); added += 1
            pbar.update(1)
        for game in coop_games:
            t = (game, RDF.type, VG.CoopGame)
            if t not in g:
                g.add(t); added += 1
            pbar.update(1)

    # ── 7 & 8: Platform classification ─────────────────────────────────────
    platform_games: dict[URIRef, set[URIRef]] = {}
    for s, p, o in g.triples((None, VG.availableOn, None)):
        if isinstance(s, URIRef) and isinstance(o, URIRef):
            platform_games.setdefault(s, set()).add(o)

    # Determine which platforms belong to which families
    console_platforms: set[URIRef] = set()
    pc_platforms: set[URIRef] = set()
    mobile_platforms: set[URIRef] = set()
    nintendo_platforms: set[URIRef] = set()
    playstation_platforms: set[URIRef] = set()
    xbox_platforms: set[URIRef] = set()

    for plat in g.subjects(RDF.type, VG.ConsolePlatform):
        console_platforms.add(plat)
    for plat in g.subjects(RDF.type, VG.PCPlatform):
        pc_platforms.add(plat)
    for plat in g.subjects(RDF.type, VG.MobilePlatform):
        mobile_platforms.add(plat)
    for plat in g.subjects(RDF.type, VG.NintendoPlatform):
        nintendo_platforms.add(plat)
    for plat in g.subjects(RDF.type, VG.PlayStationPlatform):
        playstation_platforms.add(plat)
    for plat in g.subjects(RDF.type, VG.XboxPlatform):
        xbox_platforms.add(plat)

    # Also check rdfs:subClassOf hierarchy for platform instances
    for plat in g.subjects(RDF.type, VG.Platform):
        # Check explicit type assertions and subclass hierarchy
        pass  # simpler: just use direct type assertions

    platform_class_map: dict[str, tuple[set[URIRef], URIRef]] = {
        "ConsoleGame": (console_platforms, VG.ConsoleGame),
        "PCGame": (pc_platforms, VG.PCGame),
        "MobileGame": (mobile_platforms, VG.MobileGame),
        "NintendoGame": (nintendo_platforms, VG.NintendoGame),
        "PlayStationGame": (playstation_platforms, VG.PlayStationGame),
        "XboxGame": (xbox_platforms, VG.XboxGame),
    }

    platform_inferred = 0
    for game, plat_set in platform_games.items():
        for plat_type_set, class_uri in platform_class_map.values():
            if plat_set & plat_type_set:
                t = (game, RDF.type, class_uri)
                if t not in g:
                    g.add(t)
                    platform_inferred += 1

    added += platform_inferred
    logger.info(f"  [2/5] Platform classification: +{platform_inferred} class assertions")

    # ── 9: HighlyRatedGame (metacriticScore >= 85) ─────────────────────────
    hrg_inferred = 0
    for s, p, o in g.triples((None, VG.metacriticScore, None)):
        if isinstance(s, URIRef) and isinstance(o, Literal):
            try:
                if o.datatype and o.datatype == XSD.integer:
                    score = int(o.value)  # type: ignore[arg-type]
                else:
                    score = int(str(o.value))  # type: ignore[arg-type]
                if score >= 85:
                    t = (s, RDF.type, VG.HighlyRatedGame)
                    if t not in g:
                        g.add(t)
                        hrg_inferred += 1
            except (ValueError, TypeError):
                pass
    added += hrg_inferred
    logger.info(f"  [3/5] HighlyRatedGame: +{hrg_inferred} class assertions")

    # ── 10: RecentGame (releaseDate >= 2020-01-01) ─────────────────────────
    threshold = date(2020, 1, 1)
    rg_inferred = 0
    for s, p, o in g.triples((None, VG.releaseDate, None)):
        if isinstance(s, URIRef) and isinstance(o, Literal):
            try:
                val = str(o.value)  # type: ignore[arg-type]
                d = date.fromisoformat(val[:10])  # handle potential time parts
                if d >= threshold:
                    t = (s, RDF.type, VG.RecentGame)
                    if t not in g:
                        g.add(t)
                        rg_inferred += 1
            except (ValueError, TypeError):
                pass
    added += rg_inferred
    logger.info(f"  [4/5] RecentGame: +{rg_inferred} class assertions")

    # ── 11 & 12: SequelGame / StandaloneGame ────────────────────────────────
    sequel_games: set[URIRef] = set()
    all_game_uris: set[URIRef] = set()
    for s, p, o in g.triples((None, VG.sequelOf, None)):
        if isinstance(s, URIRef):
            sequel_games.add(s)

    for s, p, o in g.triples((None, RDF.type, VG.VideoGame)):
        if isinstance(s, URIRef):
            all_game_uris.add(s)
    # Also consider anything with gameName as a VideoGame
    for s, p, o in g.triples((None, VG.gameName, None)):
        if isinstance(s, URIRef):
            all_game_uris.add(s)

    seq_added = 0
    for game in sequel_games:
        t = (game, RDF.type, VG.SequelGame)
        if t not in g:
            g.add(t)
            seq_added += 1
            added += 1

    standalone_added = 0
    for game in all_game_uris:
        if game not in sequel_games:
            t = (game, RDF.type, VG.StandaloneGame)
            if t not in g:
                g.add(t)
                standalone_added += 1
                added += 1

    logger.info(
        f"  [5/5] SequelGame: +{seq_added}, StandaloneGame: +{standalone_added}"
    )

    # ── helper: build group map and generate symmetric pairs ────────────────
    def _pairwise(
        prop_fwd: URIRef,
        prop_chain_end: URIRef,
        result_prop: URIRef,
        label: str,
        step: str,
    ) -> int:
        """Build groups: entity → set[game] via prop_fwd, then emit symmetric pairs."""
        groups: dict[URIRef, set[URIRef]] = defaultdict(set)
        for game, _, entity in g.triples((None, prop_fwd, None)):
            if isinstance(game, URIRef) and isinstance(entity, URIRef):
                groups[entity].add(game)

        skipped_groups = 0
        pairs: list[tuple[URIRef, URIRef]] = []
        for entity, games in groups.items():
            if len(games) > max_group:
                skipped_groups += 1
                continue
            glist = list(games)
            for i, g1 in enumerate(glist):
                for g2 in glist[i + 1:]:
                    pairs.append((g1, g2))

        if skipped_groups:
            logger.warning(
                f"  {label}: skipped {skipped_groups} groups with >{max_group} games "
                f"(use --max-group N to raise the limit)"
            )

        new = 0
        with tqdm(
            pairs, desc=f"  [{step}] {label}", unit="pair", ncols=80, leave=True
        ) as pbar:
            for g1, g2 in pbar:
                for a, b in ((g1, g2), (g2, g1)):
                    t = (a, result_prop, b)
                    if t not in g:
                        g.add(t)
                        new += 1
                pbar.set_postfix(new=new)
        return new

    # ── 3: sharedFranchiseWith ──────────────────────────────────────────────
    added += _pairwise(
        VG.belongsTo, VG.includes, VG.sharedFranchiseWith,
        "sharedFranchiseWith", "6a/6",
    )

    # ── 4 & 5: sharesDeveloperWith / sharesPublisherWith ────────────────────
    added += _pairwise(
        VG.developedBy, VG.developerOf, VG.sharesDeveloperWith,
        "sharesDeveloperWith", "6b/6",
    )
    added += _pairwise(
        VG.publishedBy, VG.publisherOf, VG.sharesPublisherWith,
        "sharesPublisherWith", "6c/6",
    )

    return added


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def enrich_file(
    path: Path,
    run_reasoning: bool = False,
    max_group: int = 50,
    use_v2: bool = True,
    keep_dl_axioms: bool = False,
) -> None:
    """
    Enrich an OWL file with ontology constructs and optionally run reasoning.

    Parameters
    ----------
    path : Path
        The OWL file to process.
    run_reasoning : bool
        If True, materialise inferred triples via targeted reasoning.
    max_group : int
        Max group size for pairwise chain materialisation.
    use_v2 : bool
        If True, apply V2 enrichment axioms.
    keep_dl_axioms : bool
        If True (and run_reasoning=True), restores DL-only axioms
        (FunctionalProperty/InverseFunctionalProperty on DatatypeProperty,
        owl:hasKey) after reasoning. Default False: these axioms are
        stripped and NOT restored, producing an owlrl-safe output that
        avoids spurious owl:sameAs inferences.
    """
    logger.info(f"Processing: {path.name}")
    g = Graph()
    g.bind("vg", VG)
    g.bind("owl", OWL)
    g.bind("wd", WD)
    g.bind("dcterms", DCT)
    g.parse(str(path), format="xml")
    before = len(g)
    logger.info(f"  Loaded {before} triples")

    if use_v2:
        added = _add_axioms(g)
    else:
        added_v1 = _add_axioms_v1_only(g)
        added = added_v1

    if added == 0:
        logger.info("  Axioms already up to date")
    else:
        logger.info(f"  Added {added} new axiom triples")

    if run_reasoning:
        if path.name == "videogames.owl":
            logger.info("  Skipping reasoning on schema-only file (videogames.owl)")
        else:
            # Strip DL-only axioms to prevent false owl:sameAs during owlrl
            strip_dl_only_axioms(g)

            logger.info("  Running targeted materialisation...")
            inferred = _materialise(g, max_group=max_group)
            logger.info(
                f"  Materialisation done: +{inferred} new triples → {len(g)} total"
            )

            if keep_dl_axioms:
                restore_dl_only_axioms(g)
            else:
                logger.info(
                    "  DL-only axioms NOT restored (owlrl-safe output). "
                    "Use --keep-dl-axioms to preserve them."
                )

    if added == 0 and not run_reasoning:
        logger.info("  Nothing changed — skipping save")
        return

    g.serialize(str(path), format="xml")
    logger.info(f"  Saved {len(g)} triples → {path.name}")


def _add_axioms_v1_only(g: Graph) -> int:
    """Apply only the original V1 axioms (no V2)."""
    before = len(g)

    # ── AwardWinningGame ────────────────────────────────────────────────────
    awg = VG.AwardWinningGame
    if (awg, RDF.type, OWL.Class) not in g:
        g.add((awg, RDF.type, OWL.Class))
        g.add((awg, RDFS.subClassOf, VG.VideoGame))
        g.add((awg, RDFS.label, _lit("Award Winning Game")))
        g.add((awg, RDFS.comment,
               _lit("A video game that has received at least one award. "
                    "Instances are inferred by OWL-RL reasoning.")))
        restriction = _blank(g, [(OWL.onProperty, VG.wonAward),
                                  (OWL.someValuesFrom, VG.Award)])
        intersection = _intersection(g, [VG.VideoGame, restriction])
        equiv_class = _blank(g, [(OWL.intersectionOf, intersection)])
        g.add((awg, OWL.equivalentClass, equiv_class))

    # ── FranchiseGame ───────────────────────────────────────────────────────
    fg = VG.FranchiseGame
    if (fg, RDF.type, OWL.Class) not in g:
        g.add((fg, RDF.type, OWL.Class))
        g.add((fg, RDFS.subClassOf, VG.VideoGame))
        g.add((fg, RDFS.label, _lit("Franchise Game")))
        g.add((fg, RDFS.comment,
               _lit("A video game that is part of a franchise or series. "
                    "Instances are inferred by OWL-RL reasoning.")))
        restriction = _blank(g, [(OWL.onProperty, VG.belongsTo),
                                  (OWL.someValuesFrom, VG.Franchise)])
        intersection = _intersection(g, [VG.VideoGame, restriction])
        equiv_class = _blank(g, [(OWL.intersectionOf, intersection)])
        g.add((fg, OWL.equivalentClass, equiv_class))

    # ── sharedFranchiseWith ─────────────────────────────────────────────────
    sfw = VG.sharedFranchiseWith
    if (sfw, RDF.type, OWL.ObjectProperty) not in g:
        g.add((sfw, RDF.type, OWL.ObjectProperty))
        g.add((sfw, RDF.type, OWL.SymmetricProperty))
        g.add((sfw, RDFS.domain, VG.VideoGame))
        g.add((sfw, RDFS.range, VG.VideoGame))
        g.add((sfw, RDFS.label, _lit("shared franchise with")))
        g.add((sfw, RDFS.comment,
               _lit("Links two games that belong to the same franchise/series. "
                    "Inferred via property chain.")))
        chain = _rdf_list(g, [VG.belongsTo, VG.includes])
        g.add((sfw, OWL.propertyChainAxiom, chain))

    # ── sharesDeveloperWith ─────────────────────────────────────────────────
    sdw = VG.sharesDeveloperWith
    if (sdw, RDF.type, OWL.ObjectProperty) not in g:
        g.add((sdw, RDF.type, OWL.ObjectProperty))
        g.add((sdw, RDF.type, OWL.SymmetricProperty))
        g.add((sdw, RDFS.domain, VG.VideoGame))
        g.add((sdw, RDFS.range, VG.VideoGame))
        g.add((sdw, RDFS.label, _lit("shares developer with")))
        g.add((sdw, RDFS.comment,
               _lit("Links two games developed by the same studio. "
                    "Inferred via property chain.")))
        chain = _rdf_list(g, [VG.developedBy, VG.developerOf])
        g.add((sdw, OWL.propertyChainAxiom, chain))

    # ── sharesPublisherWith ─────────────────────────────────────────────────
    spw = VG.sharesPublisherWith
    if (spw, RDF.type, OWL.ObjectProperty) not in g:
        g.add((spw, RDF.type, OWL.ObjectProperty))
        g.add((spw, RDF.type, OWL.SymmetricProperty))
        g.add((spw, RDFS.domain, VG.VideoGame))
        g.add((spw, RDFS.range, VG.VideoGame))
        g.add((spw, RDFS.label, _lit("shares publisher with")))
        g.add((spw, RDFS.comment,
               _lit("Links two games published by the same company. "
                    "Inferred via property chain.")))
        chain = _rdf_list(g, [VG.publishedBy, VG.publisherOf])
        g.add((spw, OWL.propertyChainAxiom, chain))

    return len(g) - before


def main() -> None:
    import argparse

    ontology_dir = Path(__file__).parent

    parser = argparse.ArgumentParser(
        description="Enrich OWL files with advanced ontology constructs."
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="OWL files to process (default: all *.owl in this directory)",
    )
    parser.add_argument(
        "--reason",
        action="store_true",
        help="Materialise inferred triples after enriching",
    )
    parser.add_argument(
        "--max-group",
        type=int,
        default=50,
        metavar="N",
        help="Max group size for pairwise chain materialisation (default: 50)",
    )
    parser.add_argument(
        "--v2",
        action="store_true",
        default=True,
        help="Apply V2 enrichment axioms (default: enabled)",
    )
    parser.add_argument(
        "--no-v2",
        action="store_false",
        dest="v2",
        help="Skip V2 enrichment axioms (V1 only)",
    )
    parser.add_argument(
        "--keep-dl-axioms",
        action="store_true",
        default=False,
        help="Restore DL-only axioms (FunctionalProperty/InverseFunctionalProperty "
             "on DatatypeProperty, owl:hasKey) into the output after reasoning. "
             "Default: stripped for owlrl-safe output. "
             "Only relevant with --reason.",
    )
    ns = parser.parse_args()

    if ns.files:
        targets = [ontology_dir / f for f in ns.files]
    else:
        targets = sorted(ontology_dir.glob("*.owl"))

    if not targets:
        logger.error("No OWL files found.")
        sys.exit(1)

    for target in targets:
        if not target.exists():
            logger.warning(f"File not found: {target}")
            continue
        try:
            enrich_file(
                target,
                run_reasoning=ns.reason,
                max_group=ns.max_group,
                use_v2=ns.v2,
                keep_dl_axioms=ns.keep_dl_axioms,
            )
        except Exception as e:
            logger.error(f"Failed to enrich {target.name}: {e}")

    logger.info("Done.")


if __name__ == "__main__":
    main()
