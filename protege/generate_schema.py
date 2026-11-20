"""Generate the schema (schema_generated.ttl) and the SWRL rules (swrl_rules.ttl) from the
declarative tables below.

Like a database migration: the schema is never edited by hand, it is the output of this
script. Every family of near-identical classes (games on a platform, games of a genre,
games of a publisher...) is one template plus one table row per class. The templates write
Turtle text in a fixed order (so the files are identical at every run); rdflib parses the
result to check it and to count what it contains.

    uv run python protege/generate_schema.py            # write the two files
    uv run python protege/generate_schema.py --diff     # also list what changed vs ontology/output/videogames.ttl
"""

import sys
from pathlib import Path

from rdflib import Graph

HERE = Path(__file__).resolve().parent
VG = "http://www.videogame-ontology.org/ontology#"
PREFIXES = f"""@prefix vg: <{VG}> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix wd: <http://www.wikidata.org/entity/> .
@prefix swrl: <http://www.w3.org/2003/11/swrl#> .
@prefix var: <http://www.videogame-ontology.org/ontology/swrl#> .
"""

# ---------------------------------------------------------------------------
# Tables
# ---------------------------------------------------------------------------

# Top-level classes: name, label, comment. Pairwise disjoint.
TOP = [
    ("VideoGame", "Video Game", "A video game product"),
    ("Company", "Company", "A company or studio. One individual per company: Developer and Publisher are roles it can play, not separate entities"),
    ("Genre", "Genre", "A category or genre of video games"),
    ("Platform", "Platform", "A hardware or software platform on which a game can be played"),
    ("Character", "Character", "A fictional character appearing in a video game"),
    ("Franchise", "Franchise", "A series or franchise of video games"),
    ("Award", "Award", "An award or recognition given to a video game"),
    ("GameEngine", "Game Engine", "A software framework used to develop video games"),
    ("GameMode", "Game Mode", "A mode of play available in a video game"),
]

# Other primitive subclasses: name, parent, label, comment.
PRIMITIVE = [
    ("GameOfTheYearAward", "Award", "Game of the Year Award", "The main Game of the Year prize (The Game Awards, Spike Video Game Awards)"),
    ("UnrealEngineFamily", "GameEngine", "Unreal Engine Family", "Any version of Unreal Engine"),
]

# Platform tree: family -> (label, comment, [(sub-family, label, comment)]). Siblings are disjoint.
PLATFORMS = {
    "ConsolePlatform": ("Console Platform", "A dedicated video game console", [
        ("PlayStationPlatform", "PlayStation Platform", "A console of the Sony PlayStation family"),
        ("XboxPlatform", "Xbox Platform", "A console of the Microsoft Xbox family"),
        ("NintendoPlatform", "Nintendo Platform", "A console of the Nintendo family"),
    ]),
    "PCPlatform": ("PC Platform", "A personal computer", [
        ("WindowsPlatform", "Windows Platform", "A computer running Microsoft Windows"),
        ("MacOSPlatform", "macOS Platform", "A computer running Apple macOS"),
        ("LinuxPlatform", "Linux Platform", "A computer running a Linux-based system"),
    ]),
    "MobilePlatform": ("Mobile Platform", "A phone or tablet", [
        ("IOSPlatform", "iOS Platform", "A device running Apple iOS"),
        ("AndroidPlatform", "Android Platform", "A device running Android"),
    ]),
    "BrowserPlatform": ("Browser Platform", "A web browser or web-based platform", []),
    "ArcadePlatform": ("Arcade Platform", "An arcade machine", []),
    "RetroComputerPlatform": ("Retro Computer Platform", "A home computer of the 1980s and early 1990s (Commodore 64, ZX Spectrum, Atari ST, MSX...)", []),
    "VRPlatform": ("VR Platform", "A virtual or mixed reality platform", []),
}

# Template "game available on X": VideoGame and (availableOn some XPlatform).
GAME_ON_PLATFORM = [
    ("PCGame", "PCPlatform", "PC Game"), ("ConsoleGame", "ConsolePlatform", "Console Game"),
    ("MobileGame", "MobilePlatform", "Mobile Game"), ("BrowserGame", "BrowserPlatform", "Browser Game"),
    ("ArcadeGame", "ArcadePlatform", "Arcade Game"), ("RetroComputerGame", "RetroComputerPlatform", "Retro Computer Game"),
    ("VRGame", "VRPlatform", "VR Game"), ("PlayStationGame", "PlayStationPlatform", "PlayStation Game"),
    ("XboxGame", "XboxPlatform", "Xbox Game"), ("NintendoGame", "NintendoPlatform", "Nintendo Game"),
    ("WindowsGame", "WindowsPlatform", "Windows Game"), ("MacOSGame", "MacOSPlatform", "macOS Game"),
    ("LinuxGame", "LinuxPlatform", "Linux Game"), ("AndroidGame", "AndroidPlatform", "Android Game"),
]

# Genres: prefix, label, comment. Generates XGenre (primitive) and XGame (hasGenre some XGenre).
GENRES = [
    ("Action", "Action", "A genre emphasizing physical challenges and hand-eye coordination"),
    ("Adventure", "Adventure", "A genre emphasizing exploration and narrative-driven gameplay"),
    ("Casual", "Casual", "Casual and hidden-object games"),
    ("Horror", "Horror", "A genre designed to evoke fear, dread, and suspense"),
    ("Platformer", "Platformer", "A genre focused on navigating platforms and obstacles"),
    ("Puzzle", "Puzzle", "A genre centred on logic puzzles and problem-solving"),
    ("RPG", "RPG", "A role-playing game genre with character progression and narrative focus"),
    ("Racing", "Racing", "A genre focusing on vehicle-based competition and racing"),
    ("Shooter", "Shooter", "First-person, third-person and shoot 'em up games"),
    ("Simulation", "Simulation", "A genre that simulates real-world or fictional systems"),
    ("Sports", "Sports", "A genre simulating traditional sports and athletic competitions"),
    ("Strategy", "Strategy", "A genre emphasizing tactical and strategic thinking"),
    ("VisualNovel", "Visual Novel", "Visual novels and eroge"),
]

# Game modes (pairwise disjoint): prefix, label, comment. Generates XMode and XGame.
MODES = [
    ("SinglePlayer", "Single-Player", "A game mode designed for a single player"),
    ("Multiplayer", "Multiplayer", "A game mode supporting multiple simultaneous players"),
    ("Coop", "Co-op", "A game mode supporting cooperative play among players"),
]

# Publishers used as nominals: class, individual (pub/...), name.
PUBLISHERS = [
    ("NintendoPublishedGame", "Nintendo", "Nintendo"),
    ("SonyPublishedGame", "Sony_Interactive_Entertainment", "Sony Interactive Entertainment"),
    ("XboxPublishedGame", "Xbox_Game_Studios", "Xbox Game Studios"),
    ("ElectronicArtsPublishedGame", "Electronic_Arts", "Electronic Arts"),
    ("SquareEnixPublishedGame", "Square_Enix", "Square Enix"),
    ("CapcomPublishedGame", "Capcom", "Capcom"),
    ("KonamiPublishedGame", "Konami", "Konami"),
    ("BandaiNamcoPublishedGame", "Bandai_Namco_Entertainment", "Bandai Namco Entertainment"),
]

# Country template: VideoGame and (countryOfOrigin value "...").
COUNTRIES = [("AmericanGame", "American Game", "United States"), ("JapaneseGame", "Japanese Game", "Japan")]

# Object properties: name, label, domain, range, inverse (name, label) or None, characteristics, comment.
OBJECT_PROPS = [
    ("developedBy", "developed by", "VideoGame", "Company", ("developerOf", "developer of"), [], None),
    ("publishedBy", "published by", "VideoGame", "Company", ("publisherOf", "publisher of"), [], None),
    ("hasGenre", "has genre", "VideoGame", "Genre", ("genreOf", "genre of"), [], None),
    ("availableOn", "available on", "VideoGame", "Platform", ("platformFor", "platform for"), [], None),
    ("hasGameMode", "has game mode", "VideoGame", "GameMode", ("modeInGame", "mode in game"), [], None),
    ("hasCharacter", "has character", "VideoGame", "Character", ("appearsIn", "appears in"), [], None),
    ("belongsTo", "belongs to", "VideoGame", "Franchise", ("includes", "includes"), [], None),
    ("wonAward", "won award", "VideoGame", "Award", ("awardWonBy", "award won by"), [], None),
    ("madeWith", "made with", "VideoGame", "GameEngine", ("engineUsedIn", "engine used in"), [], None),
    ("manufacturedBy", "manufactured by", "Platform", "Company", ("manufacturerOf", "manufacturer of"), [], "The company that makes the platform (Wikidata P176)"),
    ("sequelOf", "sequel of", "VideoGame", "VideoGame", ("hasSequel", "has sequel"), ["Transitive"], "A later game of the same series. Asserted towards the direct predecessor only; the rest of the series follows by transitivity"),
    ("subsidiaryOf", "subsidiary of", "Company", "Company", None, ["Transitive"], "A company controlled by another (Wikidata P749); transitive, so a studio belongs to every group above it"),
    ("publishedByGroup", "published by group", "VideoGame", "Company", None, [], "The publisher or any group that controls it"),
    ("sharesDeveloperWith", "shares developer with", "VideoGame", "VideoGame", None, ["Symmetric"], "Two games developed by the same studio (property chain)"),
    ("sharesPublisherWith", "shares publisher with", "VideoGame", "VideoGame", None, ["Symmetric"], "Two games published by the same company (property chain)"),
    ("sharedFranchiseWith", "shared franchise with", "VideoGame", "VideoGame", None, ["Symmetric"], "Two games of the same franchise (property chain)"),
]
CHAINS = [
    ("sharesDeveloperWith", "developedBy", "developerOf"),
    ("sharesPublisherWith", "publishedBy", "publisherOf"),
    ("sharedFranchiseWith", "belongsTo", "includes"),
    ("publishedByGroup", "publishedBy", "subsidiaryOf"),
]
SUBPROPERTIES = [("publishedBy", "publishedByGroup")]

# Datatype properties: name, label, domain, range, super-property, functional, Dublin Core match.
DATA_PROPS = [
    ("name", "name", None, "xsd:string", None, False, None),
    ("gameName", "game name", "VideoGame", "xsd:string", "name", True, "dcterms:title"),
    ("developerName", "developer name", "Developer", "xsd:string", "name", True, None),
    ("publisherName", "publisher name", "Publisher", "xsd:string", "name", True, None),
    ("genreName", "genre name", "Genre", "xsd:string", "name", True, None),
    ("platformName", "platform name", "Platform", "xsd:string", "name", True, None),
    ("characterName", "character name", "Character", "xsd:string", "name", True, None),
    ("franchiseName", "franchise name", "Franchise", "xsd:string", "name", True, None),
    ("awardName", "award name", "Award", "xsd:string", "name", True, None),
    ("engineName", "engine name", "GameEngine", "xsd:string", "name", True, None),
    ("releaseDate", "release date", "VideoGame", "xsd:dateTime", None, True, "dcterms:issued"),
    ("metacriticScore", "Metacritic score", "VideoGame", "xsd:integer", None, True, None),
    ("countryOfOrigin", "country of origin", "VideoGame", "xsd:string", None, False, None),
    ("hasWikidataId", "Wikidata ID", None, "xsd:string", None, False, None),
]
KEYS = [("VideoGame", "hasWikidataId")]
WIKIDATA = [("VideoGame", "Q7889"), ("Developer", "Q210167"), ("Genre", "Q65956376"), ("GameEngine", "Q193564")]


# Class expressions, written as Turtle (one line per class in the tables below)
def ref(x):
    return x if x.startswith(("[", "<", '"')) or ":" in x else f"vg:{x}"


def iri(local):  # local names with "/" (pub/Nintendo) are not valid prefixed names
    return f"<{VG}{local}>"


def some(p, c):
    return f"[ a owl:Restriction ; owl:onProperty vg:{p} ; owl:someValuesFrom {ref(c)} ]"


def value(p, v):
    return f"[ a owl:Restriction ; owl:onProperty vg:{p} ; owl:hasValue {ref(v)} ]"


def at_least(n, p, c):
    return f'[ a owl:Restriction ; owl:onProperty vg:{p} ; owl:minQualifiedCardinality "{n}"^^xsd:nonNegativeInteger ; owl:onClass {ref(c)} ]'


def data_range(datatype, facet, v):
    return f"[ a rdfs:Datatype ; owl:onDatatype {datatype} ; owl:withRestrictions ( [ {facet} {v} ] ) ]"


def and_(*xs):
    return f"[ a owl:Class ; owl:intersectionOf ( {' '.join(ref(x) for x in xs)} ) ]"


# Other defined classes: name, parent, label, comment, definition (equivalentClass).
DEFINED = [
    ("Developer", "Company", "Developer", "A company that has developed at least one video game. Not disjoint from Publisher: one company can play both roles", and_("Company", some("developerOf", "VideoGame"))),
    ("Publisher", "Company", "Publisher", "A company that has published at least one video game. Not disjoint from Developer: one company can play both roles", and_("Company", some("publisherOf", "VideoGame"))),
    ("AwardWinningGame", "VideoGame", "Award Winning Game", "A video game that has received at least one award", and_("VideoGame", some("wonAward", "Award"))),
    ("GOTYWinner", "AwardWinningGame", "Game of the Year Winner", "A video game that has won a Game of the Year award", and_("VideoGame", some("wonAward", "GameOfTheYearAward"))),
    ("FranchiseGame", "VideoGame", "Franchise Game", "A video game that is part of a franchise or series", and_("VideoGame", some("belongsTo", "Franchise"))),
    ("UnrealEngineGame", "VideoGame", "Unreal Engine Game", "A video game made with Unreal Engine", and_("VideoGame", some("madeWith", "UnrealEngineFamily"))),
    ("HighlyRatedGame", "VideoGame", "Highly Rated Game", "A video game with a Metacritic score of 85 or above", and_("VideoGame", some("metacriticScore", data_range("xsd:integer", "xsd:minInclusive", 85)))),
    ("RecentGame", "VideoGame", "Recent Game", "A video game released on or after 2020-01-01", and_("VideoGame", some("releaseDate", data_range("xsd:dateTime", "xsd:minInclusive", '"2020-01-01T00:00:00"^^xsd:dateTime')))),
    ("MultiConsoleGame", "VideoGame", "Multi-Console Game", "A video game available on at least two console platforms", and_("VideoGame", at_least(2, "availableOn", "ConsolePlatform"))),
    ("MultiPlatformGame", "VideoGame", "Multi-Platform Game", "A video game available on at least three platforms", and_("VideoGame", at_least(3, "availableOn", "Platform"))),
    ("SequelGame", "VideoGame", "Sequel Game", "A video game that is a sequel to another game", and_("VideoGame", some("sequelOf", "VideoGame"))),
    # layered classes: they need the transitive sequel chain or other defined classes
    ("LateEntry", "SequelGame", "Late Entry", "At least the third chapter of a series: the sequel of a game that is itself a sequel", and_("VideoGame", some("sequelOf", some("sequelOf", "VideoGame")))),
    ("LongRunningOriginal", "VideoGame", "Long-Running Original", "A game whose sequel has a sequel in turn: the first chapters of long series", and_("VideoGame", some("hasSequel", some("hasSequel", "VideoGame")))),
    ("AcclaimedSequel", "SequelGame", "Acclaimed Sequel", "A sequel that is also highly rated (class defined on other defined classes)", and_("SequelGame", "HighlyRatedGame")),
    # company and franchise level: knowledge about groups and series, derived from the games
    ("PlatformHolder", "Company", "Platform Holder", "A company that makes at least one console", and_("Company", some("manufacturerOf", "ConsolePlatform"))),
    ("FirstPartyGame", "VideoGame", "First-Party Game", "A game published by a platform holder or by a company of its group", and_("VideoGame", some("publishedByGroup", "PlatformHolder"))),
    ("LongRunningFranchise", "Franchise", "Long-Running Franchise", "A series with at least three chapters: it includes a late entry", and_("Franchise", some("includes", "LateEntry"))),
    ("FranchiseWithStudioChange", "Franchise", "Franchise with Studio Change", "A series in which a sequel was developed by a different studio (built on a SWRL conclusion)", and_("Franchise", some("includes", "SequelByDifferentStudio"))),
]

# Target classes of the SWRL rules: name, label, comment.
SWRL_TARGETS = [
    ("SelfPublishedGame", "Self-Published Game", "A game developed and published by the same company (SWRL rule)"),
    ("SequelByDifferentStudio", "Sequel by Different Studio", "A sequel developed by a studio different from the one of its predecessor (SWRL rule)"),
    ("FirstPartyOnRivalConsole", "First-Party Game on a Rival Console", "A first-party game that also came out on a console made by another platform holder (SWRL rule)"),
    ("CouchCoopCandidate", "Couch Co-op Candidate", "A game with a co-op mode available on a console (SWRL rule)"),
    ("MustPlayGame", "Must-Play Game", "A game with a Metacritic score above 94 (SWRL rule)"),
]

# SWRL rules: name, body atoms, head atoms. An atom is (predicate, args...): a class (1 arg),
# a property (2 args), "differentFrom", or ("xsd:integer", facet, value, var) for a data range
# (as in the course examples: no swrlb built-ins, so HermiT runs every rule).
# HermiT matches rule atoms only against asserted (simple) properties, not values derived from
# a chain or from transitivity: the first-party rule has a version for the publisher itself and
# one for its direct parent company.
RIVAL = [("availableOn", "?g", "?p"), ("ConsolePlatform", "?p"), ("manufacturedBy", "?p", "?m"), ("differentFrom", "?h", "?m"), ("manufacturerOf", "?h", "?q"), ("ConsolePlatform", "?q")]
RULES = [
    ("SelfPublished", [("developedBy", "?g", "?c"), ("publishedBy", "?g", "?c")], [("SelfPublishedGame", "?g")]),
    ("SequelByDifferentStudio", [("sequelOf", "?a", "?b"), ("developedBy", "?a", "?x"), ("developedBy", "?b", "?y"), ("differentFrom", "?x", "?y")], [("SequelByDifferentStudio", "?a")]),
    ("FirstPartyOnRivalConsole", [("publishedBy", "?g", "?h"), *RIVAL], [("FirstPartyOnRivalConsole", "?g")]),
    ("FirstPartyOnRivalConsoleGroup", [("publishedBy", "?g", "?x"), ("subsidiaryOf", "?x", "?h"), *RIVAL], [("FirstPartyOnRivalConsole", "?g")]),
    ("CouchCoop", [("hasGameMode", "?g", "?m"), ("CoopMode", "?m"), ("availableOn", "?g", "?p"), ("ConsolePlatform", "?p")], [("CouchCoopCandidate", "?g")]),
    ("MustPlay", [("metacriticScore", "?g", "?s"), ("xsd:integer", "xsd:minExclusive", 94, "?s")], [("MustPlayGame", "?g")]),
]

# ---------------------------------------------------------------------------
# Turtle writers
# ---------------------------------------------------------------------------


def statement(subject, *pairs):
    """subject p1 o1 ; p2 o2 . (pairs with a None object are skipped)"""
    body = " ;\n    ".join(f"{p} {o}" for p, o in pairs if o is not None)
    return f"{subject} {body} .\n"


def cls(name, label, comment, parent=None, equivalent=None):
    return statement(f"vg:{name}", ("a", "owl:Class"), ("rdfs:label", f'"{label}"'), ("rdfs:comment", f'"{comment}"'),
                     ("rdfs:subClassOf", parent and f"vg:{parent}"), ("owl:equivalentClass", equivalent))


def disjoint(names):
    return statement("[]", ("a", "owl:AllDisjointClasses"), ("owl:members", f"( {' '.join(f'vg:{n}' for n in names)} )"))


def schema():
    out = [PREFIXES, statement("<http://www.videogame-ontology.org/ontology>", ("a", "owl:Ontology"), ("rdfs:label", '"Video Game Ontology"'),
                               ("owl:versionInfo", '"3.0 (generated by protege/generate_schema.py)"'),
                               ("rdfs:comment", '"Video games, their companies, genres, platforms, game modes, franchises, awards and engines. Generated from declarative tables: do not edit by hand."')),
           statement("skos:closeMatch", ("a", "owl:AnnotationProperty"))]
    out.append("\n# --- Top-level classes (pairwise disjoint) and other primitive classes\n")
    out += [cls(*row) for row in TOP] + [disjoint([row[0] for row in TOP])]
    out += [cls(name, label, comment, parent) for name, parent, label, comment in PRIMITIVE]
    out.append("\n# --- Platforms: families and sub-families (siblings are disjoint)\n")
    for family, (label, comment, subs) in PLATFORMS.items():
        out += [cls(family, label, comment, "Platform")] + [cls(s, sl, sc, family) for s, sl, sc in subs]
        out += [disjoint([s for s, _, _ in subs])] if len(subs) > 1 else []
    out.append(disjoint(PLATFORMS))
    out.append("\n# --- Genres and game modes (modes are disjoint)\n")
    out += [cls(f"{p}Genre", f"{label} Genre", comment, "Genre") for p, label, comment in GENRES]
    out += [cls(f"{p}Mode", f"{label} Mode", comment, "GameMode") for p, label, comment in MODES] + [disjoint([f"{p}Mode" for p, _, _ in MODES])]
    out.append("\n# --- Publishers used as nominals by the defined classes\n")
    out += [statement(iri(f"pub/{ind}"), ("a", "owl:NamedIndividual , vg:Publisher"), ("vg:publisherName", f'"{name}"')) for _, ind, name in PUBLISHERS]

    out.append("\n# --- Defined classes from templates (one table row each)\n")
    labels = {**{f: v[0] for f, v in PLATFORMS.items()}, **{s: sl for v in PLATFORMS.values() for s, sl, _ in v[2]}}
    out += [cls(game, label, f"A video game available on a {labels[plat].removesuffix(' Platform')} platform", "VideoGame", and_("VideoGame", some("availableOn", plat))) for game, plat, label in GAME_ON_PLATFORM]
    out += [cls(f"{p}Game", f"{label} Game", f"A video game of the {label.lower()} genre", "VideoGame", and_("VideoGame", some("hasGenre", f"{p}Genre"))) for p, label, _ in GENRES]
    out += [cls(f"{p}Game", f"{label} Game", f"A video game with a {label.lower()} mode", "VideoGame", and_("VideoGame", some("hasGameMode", f"{p}Mode"))) for p, label, _ in MODES]
    out += [cls(game, f"{name} Published Game", f"A video game published by {name} (nominal)", "VideoGame", and_("VideoGame", value("publishedBy", iri(f"pub/{ind}")))) for game, ind, name in PUBLISHERS]
    out += [cls(game, label, f"A video game whose country of origin is {country}", "VideoGame", and_("VideoGame", value("countryOfOrigin", f'"{country}"'))) for game, label, country in COUNTRIES]
    out.append("\n# --- Other defined classes\n")
    out += [cls(name, label, comment, parent, definition) for name, parent, label, comment, definition in DEFINED]
    out.append("\n# --- Target classes of the SWRL rules (swrl_rules.ttl)\n")
    out += [cls(name, label, comment, "VideoGame") for name, label, comment in SWRL_TARGETS]

    out.append("\n# --- Object properties\n")
    for name, label, dom, rng, inv, chars, comment in OBJECT_PROPS:
        loose = ["owl:IrreflexiveProperty", "owl:AsymmetricProperty"] if inv and dom != rng else []  # a link between two kinds of thing never loops or goes back
        types = ", ".join(["owl:ObjectProperty", *loose, *(f"owl:{c}Property" for c in chars)])
        out.append(statement(f"vg:{name}", ("a", types), ("rdfs:label", f'"{label}"'), ("rdfs:comment", comment and f'"{comment}"'),
                             ("rdfs:domain", f"vg:{dom}"), ("rdfs:range", f"vg:{rng}")))
        if inv:
            out.append(statement(f"vg:{inv[0]}", ("a", ", ".join(["owl:ObjectProperty", *loose])), ("rdfs:label", f'"{inv[1]}"'),
                                 ("rdfs:domain", f"vg:{rng}"), ("rdfs:range", f"vg:{dom}"), ("owl:inverseOf", f"vg:{name}")))
    out += [statement(f"vg:{p}", ("owl:propertyChainAxiom", f"( vg:{a} vg:{b} )")) for p, a, b in CHAINS]
    out += [statement(f"vg:{sub}", ("rdfs:subPropertyOf", f"vg:{sup}")) for sub, sup in SUBPROPERTIES]
    out.append("\n# --- Datatype properties (the functional ones are DL-only axioms, kept for HermiT)\n")
    out += [statement(f"vg:{name}", ("a", "owl:DatatypeProperty, owl:FunctionalProperty" if functional else "owl:DatatypeProperty"), ("rdfs:label", f'"{label}"'),
                      ("rdfs:domain", f"vg:{dom}" if dom else "owl:Thing"), ("rdfs:range", rng), ("rdfs:subPropertyOf", sup and f"vg:{sup}"), ("skos:closeMatch", dc))
            for name, label, dom, rng, sup, functional, dc in DATA_PROPS]
    out.append("\n# --- Keys and alignments (skos:closeMatch, not equivalence)\n")
    out += [statement(f"vg:{c}", ("owl:hasKey", f"( vg:{p} )")) for c, p in KEYS]
    out += [statement(f"vg:{c}", ("skos:closeMatch", f"wd:{q}")) for c, q in WIKIDATA]
    return "".join(out)


def rules():
    data_props = {row[0] for row in DATA_PROPS}

    def atom(pred, *args):
        v = [f"var:{a[1:]}" for a in args if isinstance(a, str) and a.startswith("?")]
        if pred == "differentFrom":
            return f"[ a swrl:DifferentIndividualsAtom ; swrl:argument1 {v[0]} ; swrl:argument2 {v[1]} ]"
        if pred.startswith("xsd:"):
            return f"[ a swrl:DataRangeAtom ; swrl:dataRange {data_range(pred, args[0], args[1])} ; swrl:argument1 {v[0]} ]"
        if len(args) == 1:
            return f"[ a swrl:ClassAtom ; swrl:classPredicate vg:{pred} ; swrl:argument1 {v[0]} ]"
        kind = "DatavaluedPropertyAtom" if pred in data_props else "IndividualPropertyAtom"
        return f"[ a swrl:{kind} ; swrl:propertyPredicate vg:{pred} ; swrl:argument1 {v[0]} ; swrl:argument2 {v[1]} ]"

    def atom_list(atoms):  # nested swrl:AtomList, as Protégé writes it
        return "rdf:nil" if not atoms else f"[ a swrl:AtomList ;\n      rdf:first {atoms[0]} ;\n      rdf:rest {atom_list(atoms[1:])} ]"

    def text(atoms):
        return " ^ ".join(f"{a[0]}({', '.join(map(str, a[1:]))})" for a in atoms)

    out = [PREFIXES, statement("<http://www.videogame-ontology.org/ontology/swrl-rules>", ("a", "owl:Ontology"),
                               ("rdfs:comment", '"SWRL rules (generated by protege/generate_schema.py), all DL-safe and run by HermiT."'),
                               ("owl:imports", "<http://www.videogame-ontology.org/ontology>"))]
    variables = sorted({a for _, body, head in RULES for atom_ in body + head for a in atom_[1:] if isinstance(a, str) and a.startswith("?")})
    out += [statement(f"var:{v[1:]}", ("a", "swrl:Variable")) for v in variables]
    for name, body, head in RULES:
        out.append("\n" + statement(f"var:{name}", ("a", "swrl:Imp"), ("rdfs:label", f'"{name}"'), ("rdfs:comment", f'"{text(body)} -> {text(head)}"'),
                                    ("swrl:body", atom_list([atom(*a) for a in body])), ("swrl:head", atom_list([atom(*a) for a in head]))))
    return "".join(out)


def count(g, pattern):
    q = f"PREFIX owl: <http://www.w3.org/2002/07/owl#> SELECT (COUNT(DISTINCT ?s) AS ?n) WHERE {{ {pattern} }}"
    return int(next(iter(g.query(q)))[0])


def entities(g):
    q = "SELECT ?s WHERE { VALUES ?t { owl:Class owl:ObjectProperty owl:DatatypeProperty } ?s a ?t FILTER(STRSTARTS(STR(?s), STR(vg:))) }"
    return {str(row[0]).removeprefix(VG) for row in g.query(q, initNs={"vg": VG, "owl": "http://www.w3.org/2002/07/owl#"})}


def main():
    files = {"schema_generated.ttl": schema(), "swrl_rules.ttl": rules()}
    for name, text in files.items():
        (HERE / name).write_text(text, encoding="utf-8")
        print(f"wrote protege/{name}")
    g = Graph()
    g.parse(data=files["schema_generated.ttl"], format="turtle")  # also checks the Turtle
    Graph().parse(data=files["swrl_rules.ttl"], format="turtle")
    for label, pattern in [
        ("classes", "?s a owl:Class FILTER(isIRI(?s))"), ("defined classes", "?s owl:equivalentClass ?e"),
        ("object properties", "?s a owl:ObjectProperty"), ("datatype properties", "?s a owl:DatatypeProperty"),
        ("functional", "?s a owl:FunctionalProperty"), ("transitive", "?s a owl:TransitiveProperty"),
        ("property chains", "?s owl:propertyChainAxiom ?c"), ("disjoint blocks", "?s a owl:AllDisjointClasses"),
        ("keys", "?s owl:hasKey ?k"),
    ]:
        print(f"{label:>20}: {count(g, pattern)}")
    print(f"{'SWRL rules':>20}: {len(RULES)}\n{'triples':>20}: {len(g)}")
    if "--diff" in sys.argv:
        old = Graph()
        old.parse(HERE.parent / "ontology" / "output" / "videogames.ttl", format="turtle")
        new, before = entities(g), entities(old)
        print("\nRemoved:", ", ".join(sorted(before - new)) or "-")
        print("Added:", ", ".join(sorted(new - before)) or "-")


if __name__ == "__main__":
    main()
