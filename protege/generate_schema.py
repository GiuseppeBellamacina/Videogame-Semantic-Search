"""Genera schema.ttl, regole.ttl e relazione/appendice.tex dalle tabelle di questo file.

uv run python protege/generate_schema.py
"""

from pathlib import Path

from rdflib import OWL, RDF, RDFS, XSD, BNode, Graph, Literal, Namespace
from rdflib.collection import Collection

HERE = Path(__file__).resolve().parent
BASE = Namespace("http://www.videogame-ontology.org/")
VG = Namespace("http://www.videogame-ontology.org/ontology#")
SWRL = Namespace("http://www.w3.org/2003/11/swrl#")
VAR = Namespace("http://www.videogame-ontology.org/ontology/regole#")

# le tabelle restano una riga per elemento: black le lascia stare
# fmt: off
TOP = [
    ("VideoGame", "Un videogioco"),
    ("Company", "Uno studio, un editore o un gruppo industriale"),
    ("Person", "Una persona reale"),
    ("Character", "Un personaggio di finzione"),
    ("Platform", "Una piattaforma su cui si gioca"),
    ("Franchise", "Una serie di giochi"),
    ("GameEngine", "Un motore di gioco"),
    ("Award", "Il premio Gioco dell'anno di una cerimonia (The Game Awards, BAFTA, D.I.C.E....)"),
    ("Genre", "Un genere"),
    ("GameMode", "Una modalità di gioco"),
    ("Killing", "Un'uccisione nella trama di un gioco: vittima, assassino e gioco (relazione n-aria)"),
    ("FictionalOrganization", "Un'organizzazione del mondo di gioco (per esempio Aperture Science)"),
    ("CreativeWork", "Un'opera di un altro medium (romanzo, film, serie TV)"),
]

PRIMITIVE = [
    ("ConsolePlatform", "Platform", "Una console"),
    ("PCPlatform", "Platform", "Un personal computer"),
    ("Novel", "CreativeWork", "Un romanzo"),
    ("Film", "CreativeWork", "Un film"),
    ("TVSeries", "CreativeWork", "Una serie televisiva"),
    ("Comic", "CreativeWork", "Un fumetto"),
    ("TabletopGame", "CreativeWork", "Un gioco da tavolo o di ruolo cartaceo"),
    ("Human", "Character", "Un personaggio umano"),
    ("Alien", "Character", "Un personaggio di una specie non umana del mondo di gioco"),
]

DISJOINT = [
    [name for name, _ in TOP],
    ["ConsolePlatform", "PCPlatform"],
    ["Novel", "Film", "TVSeries", "Comic", "TabletopGame"],
    ["Human", "Alien", "Synthetic"],
]


def some(p, c):
    return ("some", p, c)


def at_least(n, p, c):
    return ("min", n, p, c)


def has_value(p, value):
    return ("value", p, value)


def int_at_least(n):
    return ("range", "xsd:integer", "xsd:minInclusive", n)


def int_at_most(n):
    return ("range", "xsd:integer", "xsd:maxInclusive", n)


def date_before(date):
    return ("range", "xsd:dateTime", "xsd:maxExclusive", date)


def all_of(*xs):
    return ("and", *xs)


def any_of(*xs):
    return ("or", *xs)


DEFINED = [
    ("CurrentGenerationConsole", "ConsolePlatform", "Una console della nona generazione, l'attuale", all_of("ConsolePlatform", some("generation", int_at_least(9)))),
    ("PreviousGenerationConsole", "ConsolePlatform", "Una console di ottava generazione o precedente", all_of("ConsolePlatform", some("generation", int_at_most(8)))),
    ("CrossGenerationGame", "StillPlayable", "Un gioco giocabile oggi che è uscito anche su una console di una generazione precedente", all_of("StillPlayable", some("playableOn", "PreviousGenerationConsole"))),
    ("ProlificDirector", "GameDirector", "Chi ha diretto almeno tre giochi", all_of("GameDirector", at_least(3, "directorOf", "VideoGame"))),
    ("ProlificDeveloper", "Developer", "Un'azienda che ha sviluppato almeno cinque giochi", all_of("Developer", at_least(5, "developerOf", "VideoGame"))),
    ("FirstPartyStudio", "Developer", "Uno studio che fa parte del gruppo di un costruttore di console", all_of("Developer", some("inGroupOf", "PlatformHolder"))),
    ("VillainSlayer", "Protagonist", "Un protagonista che ha ucciso un cattivo sconfitto", all_of("Protagonist", some("kills", "DefeatedVillain"))),
    ("TragicProtagonist", "Protagonist", "Un protagonista che muore nella trama di un gioco", all_of("Protagonist", "DeceasedCharacter")),
    ("Turncoat", "Protagonist", "Un personaggio che è protagonista in un gioco e antagonista in un altro", all_of("Protagonist", "Antagonist")),
    ("HistoricalGame", "VideoGame", "Un gioco con personaggi realmente esistiti: probabilmente ambientato nel passato", all_of("VideoGame", some("hasCharacter", "HistoricalCharacter"))),
    ("SciFiGame", "VideoGame", "Un gioco con personaggi alieni o sintetici: probabilmente fantascienza", all_of("VideoGame", some("hasCharacter", any_of("Alien", "Synthetic")))),
    ("RogueAIGame", "VideoGame", "Un gioco il cui antagonista è un'intelligenza artificiale", all_of("VideoGame", some("hasAntagonist", "RogueAI"))),
    ("PrequelGame", "VideoGame", "Un gioco la cui storia precede quella di un altro", all_of("VideoGame", some("prequelOf", "VideoGame"))),
    ("PrequelReturn", "ReturnAfterDeathGame", "Un gioco in cui ricompare un personaggio già morto, spiegato dal fatto che è un prequel", all_of("ReturnAfterDeathGame", "PrequelGame")),
    ("Synthetic", "Character", "Un personaggio costruito da qualcuno nel mondo di gioco: un'intelligenza artificiale o un robot", all_of("Character", some("builtBy", "owl:Thing"))),
    ("PlayerCharacter", "Character", "Un personaggio controllato dal giocatore in almeno un gioco", all_of("Character", some("playableIn", "VideoGame"))),
    ("KilledMoreThanOnce", "DeceasedCharacter", "Un personaggio ucciso in almeno due giochi: torna sempre", all_of("DeceasedCharacter", at_least(2, "victimIn", "Killing"))),
    ("Remaster", "VideoGame", "La nuova edizione di un altro gioco", all_of("VideoGame", some("remasterOf", "VideoGame"))),
    ("GameDirector", "Person", "Chi ha diretto almeno un gioco", all_of("Person", some("directorOf", "VideoGame"))),
    ("StudioHead", "Person", "Chi guida un'azienda", all_of("Person", some("heads", "Company"))),
    ("DeceasedCharacter", "Character", "Un personaggio ucciso nella trama di un gioco", all_of("Character", some("victimIn", "Killing"))),
    ("Killer", "Character", "Un personaggio che ha tolto la vita a qualcuno", all_of("Character", some("killerIn", "Killing"))),
    ("Developer", "Company", "Un'azienda che ha sviluppato almeno un gioco", all_of("Company", some("developerOf", "VideoGame"))),
    ("Publisher", "Company", "Un'azienda che ha pubblicato almeno un gioco", all_of("Company", some("publisherOf", "VideoGame"))),
    ("PlatformHolder", "Company", "Un'azienda che costruisce console", all_of("Company", some("manufacturerOf", "ConsolePlatform"))),
    ("FoundedByVeterans", "Company", "Un'azienda fondata da chi lavorava per uno sviluppatore", all_of("Company", some("foundedBy", some("formerEmployeeOf", "Developer")))),
    ("FirstPartyGame", "VideoGame", "Un gioco pubblicato dal gruppo di un costruttore di console", all_of("VideoGame", some("publishedByGroup", "PlatformHolder"))),
    ("SequelGame", "VideoGame", "Il seguito di un altro gioco", all_of("VideoGame", some("sequelOf", "VideoGame"))),
    ("LateEntry", "SequelGame", "Almeno il terzo capitolo di una serie", all_of("SequelGame", some("sequelOf", some("sequelOf", "VideoGame")))),
    ("ViolentStoryGame", "VideoGame", "Un gioco nella cui trama qualcuno viene ucciso", all_of("VideoGame", some("hasKilling", "Killing"))),
    ("RealisticViolenceGame", "ViolentStoryGame", "Un gioco violento classificato PEGI 16 o 18: violenza realistica, non per minori", all_of("ViolentStoryGame", some("pegiRating", int_at_least(16)))),
    ("FantasyViolenceGame", "ViolentStoryGame", "Un gioco violento classificato al più PEGI 12: violenza su personaggi non realistici", all_of("ViolentStoryGame", some("pegiRating", int_at_most(12)))),
    ("GOTYWinner", "VideoGame", "Un gioco premiato come gioco dell'anno", all_of("VideoGame", some("wonAward", "Award"))),
    ("StillPlayable", "VideoGame", "Un gioco giocabile su una console attuale", all_of("VideoGame", some("playableOn", "CurrentGenerationConsole"))),
    ("Adaptation", "VideoGame", "Un gioco tratto da un'opera di un altro medium", all_of("VideoGame", some("basedOn", "CreativeWork"))),
    ("LiteraryAdaptation", "Adaptation", "Un gioco tratto da un romanzo", all_of("Adaptation", some("basedOn", "Novel"))),
    ("AuteurGame", "VideoGame", "Un gioco diretto da chi guida uno studio", all_of("VideoGame", some("directedBy", "StudioHead"))),
    ("LongRunningFranchise", "Franchise", "Una serie con almeno tre capitoli", all_of("Franchise", some("includes", "LateEntry"))),
    ("AwardWinningFranchise", "Franchise", "Una serie con un gioco dell'anno", all_of("Franchise", some("includes", "GOTYWinner"))),
    ("TransmediaFranchise", "Franchise", "Una serie diventata film o serie TV", all_of("Franchise", some("adaptedInto", any_of("Film", "TVSeries")))),
    ("FranchiseWithStudioChange", "Franchise", "Una serie passata a un altro studio", all_of("Franchise", some("includes", "SequelByDifferentStudio"))),
    ("Protagonist", "Character", "Il protagonista di un gioco", all_of("Character", some("protagonistOf", "VideoGame"))),
    ("Antagonist", "Character", "L'antagonista di un gioco", all_of("Character", some("antagonistOf", "VideoGame"))),
    ("RecurringCharacter", "Character", "Un personaggio presente in almeno due giochi", all_of("Character", at_least(2, "appearsIn", "VideoGame"))),
    ("RecurringVillain", "RecurringCharacter", "Un antagonista ricorrente", all_of("RecurringCharacter", "Antagonist")),
    ("RogueAI", "Synthetic", "Un'intelligenza artificiale o un robot antagonista", all_of("Synthetic", "Antagonist")),
    ("MultipleKiller", "Killer", "Un personaggio che ha ucciso almeno due personaggi", all_of("Killer", at_least(2, "kills", "Character"))),
    ("HistoricalCharacter", "Character", "Un personaggio che interpreta una persona reale", all_of("Character", some("portrays", "Person"))),
    ("ClassicGame", "VideoGame", "Un gioco uscito prima del 2005", all_of("VideoGame", some("releaseDate", date_before("2005-01-01T00:00:00")))),
    ("ClassicStillPlayable", "ClassicGame", "Un classico precedente al 2005 giocabile oggi su una console attuale", all_of("ClassicGame", "StillPlayable")),
    ("Pegi3Game", "VideoGame", "Un gioco classificato PEGI 3, adatto a tutti", all_of("VideoGame", has_value("pegiRating", 3))),
    ("Pegi7Game", "VideoGame", "Un gioco classificato PEGI 7", all_of("VideoGame", has_value("pegiRating", 7))),
    ("Pegi12Game", "VideoGame", "Un gioco classificato PEGI 12", all_of("VideoGame", has_value("pegiRating", 12))),
    ("Pegi16Game", "VideoGame", "Un gioco classificato PEGI 16", all_of("VideoGame", has_value("pegiRating", 16))),
    ("Pegi18Game", "VideoGame", "Un gioco classificato PEGI 18, solo per adulti", all_of("VideoGame", has_value("pegiRating", 18))),
]

RULE_TARGETS = [
    ("FirstPartyOnRivalConsole", "VideoGame", "Un gioco first-party uscito su una console di un concorrente"),
    ("SequelByDifferentStudio", "VideoGame", "Un seguito sviluppato da uno studio diverso"),
    ("VeteransReturn", "VideoGame", "Un gioco fatto da uno studio fondato da chi aveva lavorato alla serie"),
    ("EngineChangeSequel", "VideoGame", "Un seguito che cambia motore"),
    ("ExternalEngineGame", "VideoGame", "Un gioco fatto con un motore sviluppato da un'altra azienda, anche dello stesso gruppo (vedi GroupEngineGame)"),
    ("GroupEngineGame", "VideoGame", "Un gioco fatto con il motore di un'altra azienda dello stesso gruppo"),
    ("SameGroupSequel", "VideoGame", "Un seguito sviluppato da un altro studio dello stesso gruppo"),
    ("SelfPublishedGame", "VideoGame", "Un gioco sviluppato e pubblicato dalla stessa azienda"),
    ("InHouseEngineGame", "VideoGame", "Un gioco fatto con il motore dello stesso studio"),
    ("ReturningDirectorSequel", "VideoGame", "Un seguito con lo stesso regista del predecessore"),
    ("DefeatedVillain", "DeceasedCharacter", "Un antagonista ucciso dal protagonista"),
    ("ReturningCharacter", "DeceasedCharacter", "Un personaggio che ricompare in un gioco uscito dopo quello in cui è stato ucciso"),
    ("ReturnAfterDeathGame", "VideoGame", "Un gioco uscito dopo la morte di un suo personaggio: prequel, linea temporale alternativa o resurrezione"),
    ("MustPlayGame", "VideoGame", "Un gioco con almeno 95 su Metacritic"),
]

# name, domain, range, inverse, characteristics, comment
OBJECT_PROPS = [
    ("developedBy", "VideoGame", "Company", "developerOf", [], None),
    ("publishedBy", "VideoGame", "Company", "publisherOf", [], None),
    ("availableOn", "VideoGame", "Platform", "platformFor", [], None),
    ("hasGenre", "VideoGame", "Genre", None, [], None),
    ("hasGameMode", "VideoGame", "GameMode", None, [], None),
    ("belongsTo", "VideoGame", "Franchise", "includes", [], None),
    ("sequelOf", "VideoGame", "VideoGame", "hasSequel", ["Transitive"], "Asserita solo verso il predecessore diretto"),
    ("remasterOf", "VideoGame", "VideoGame", "hasRemaster", [], None),
    ("wonAward", "VideoGame", "Award", None, [], None),
    ("madeWith", "VideoGame", "GameEngine", None, [], None),
    ("engineDevelopedBy", "GameEngine", "Company", None, [], None),
    ("manufacturedBy", "Platform", "Company", "manufacturerOf", [], None),
    ("subsidiaryOf", "Company", "Company", None, ["Transitive"], None),
    ("publishedByGroup", "VideoGame", "Company", None, [], "Derivata dalle regole: l'editore e i gruppi che lo controllano"),
    ("inGroupOf", "Company", "Company", None, [], "Derivata dalle regole: l'azienda stessa e tutte quelle che la controllano"),
    ("directedBy", "VideoGame", "Person", "directorOf", [], None),
    ("heads", "Person", "Company", None, [], None),
    ("foundedBy", "Company", "Person", None, [], None),
    ("formerEmployeeOf", "Person", "Company", None, [], None),
    ("basedOn", "VideoGame", "CreativeWork", None, [], None),
    ("adaptedInto", "Franchise", "CreativeWork", None, [], None),
    ("appearsIn", "Character", "VideoGame", "hasCharacter", [], None),
    ("protagonistOf", "Character", "VideoGame", None, [], None),
    ("antagonistOf", "Character", "VideoGame", "hasAntagonist", [], None),
    ("killedBy", "Character", "Character", "kills", [], "Dedotta dalla regola KillingEvent"),
    ("victim", "Killing", "Character", "victimIn", [], None),
    ("killer", "Killing", "Character", "killerIn", [], None),
    ("inGame", "Killing", "VideoGame", "hasKilling", [], None),
    ("portrays", "Character", "Person", None, [], None),
    ("builtBy", "Character", "owl:Thing", None, [], "Chi ha costruito il personaggio nel mondo di gioco (un altro personaggio o un'organizzazione)"),
    ("playableIn", "Character", "VideoGame", None, [], "Il personaggio è controllato dal giocatore in quel gioco"),
    ("prequelOf", "VideoGame", "VideoGame", None, [], "La storia del gioco si svolge prima di quella dell'altro, anche se è uscito dopo"),
    ("releasedAfter", "VideoGame", "VideoGame", None, [], "Derivata dalle regole: uscito dopo, nella stessa serie"),
    ("playableOn", "VideoGame", "Platform", None, [], "Disponibile, anche tramite una nuova edizione"),
    ("techLinkedTo", "VideoGame", "VideoGame", None, [], "Giochi dello studio che ha fatto il motore usato"),
]
SUBPROPERTIES = [("availableOn", "playableOn"), ("protagonistOf", "appearsIn"), ("antagonistOf", "appearsIn"), ("playableIn", "appearsIn")]
CHAINS = [("playableOn", ["hasRemaster", "availableOn"]), ("techLinkedTo", ["madeWith", "engineDevelopedBy", "developerOf"])]
# solo proprietà semplici (né transitive né super-proprietà di catene): per questo non sequelOf
DISJOINT_PROPS = [("remasterOf", "prequelOf")]

# name, domain, range, functional
DATA_PROPS = [
    ("releaseDate", "VideoGame", "xsd:dateTime", True),
    ("metacriticScore", "VideoGame", "xsd:integer", True),
    ("pegiRating", "VideoGame", "xsd:integer", True),
    ("generation", "ConsolePlatform", "xsd:integer", True),
    ("hasWikidataId", "owl:Thing", "xsd:string", False),
]
KEYS = [("VideoGame", "hasWikidataId")]

RIVAL = [("availableOn", "?g", "?p"), ("ConsolePlatform", "?p"), ("manufacturedBy", "?p", "?m"), ("PlatformHolder", "?h"), ("differentFrom", "?h", "?m")]
RULES = [
    ("PublisherGroup", [("publishedBy", "?g", "?c")], [("publishedByGroup", "?g", "?c")]),
    ("ParentGroup", [("publishedByGroup", "?g", "?c"), ("subsidiaryOf", "?c", "?p")], [("publishedByGroup", "?g", "?p")]),
    ("FirstPartyOnRivalConsole", [("publishedByGroup", "?g", "?h"), *RIVAL], [("FirstPartyOnRivalConsole", "?g")]),
    ("SequelByDifferentStudio", [("sequelOf", "?a", "?b"), ("developedBy", "?a", "?x"), ("developedBy", "?b", "?y"), ("differentFrom", "?x", "?y")], [("SequelByDifferentStudio", "?a")]),
    ("VeteransReturn", [("developedBy", "?g", "?c"), ("foundedBy", "?c", "?p"), ("formerEmployeeOf", "?p", "?o"), ("developerOf", "?o", "?h"), ("belongsTo", "?g", "?f"), ("belongsTo", "?h", "?f")], [("VeteransReturn", "?g")]),
    ("EngineChangeSequel", [("sequelOf", "?a", "?b"), ("madeWith", "?a", "?x"), ("madeWith", "?b", "?y"), ("differentFrom", "?x", "?y")], [("EngineChangeSequel", "?a")]),
    ("ExternalEngine", [("madeWith", "?g", "?e"), ("engineDevelopedBy", "?e", "?m"), ("developedBy", "?g", "?d"), ("differentFrom", "?m", "?d")], [("ExternalEngineGame", "?g")]),
    ("InHouseEngine", [("madeWith", "?g", "?e"), ("engineDevelopedBy", "?e", "?d"), ("developedBy", "?g", "?d")], [("InHouseEngineGame", "?g")]),
    ("ReturningDirector", [("sequelOf", "?a", "?b"), ("directedBy", "?a", "?p"), ("directedBy", "?b", "?p")], [("ReturningDirectorSequel", "?a")]),
    ("KillingEvent", [("victim", "?k", "?v"), ("killer", "?k", "?a")], [("killedBy", "?v", "?a")]),
    ("DefeatedVillain", [("antagonistOf", "?v", "?g"), ("protagonistOf", "?h", "?g"), ("killedBy", "?v", "?h")], [("DefeatedVillain", "?v")]),
    ("ReleaseOrder", [("sequelOf", "?a", "?b")], [("releasedAfter", "?a", "?b")]),
    ("ReleaseOrderChain", [("releasedAfter", "?a", "?b"), ("sequelOf", "?b", "?c")], [("releasedAfter", "?a", "?c")]),
    ("ReturnAfterDeath", [("victim", "?k", "?c"), ("inGame", "?k", "?g"), ("appearsIn", "?c", "?h"), ("releasedAfter", "?h", "?g")],
     [("ReturningCharacter", "?c"), ("ReturnAfterDeathGame", "?h")]),
    ("GroupSelf", [("Company", "?c")], [("inGroupOf", "?c", "?c")]),
    ("GroupParent", [("inGroupOf", "?c", "?p"), ("subsidiaryOf", "?p", "?q")], [("inGroupOf", "?c", "?q")]),
    ("GroupEngine", [("madeWith", "?g", "?e"), ("engineDevelopedBy", "?e", "?m"), ("developedBy", "?g", "?d"), ("differentFrom", "?m", "?d"), ("inGroupOf", "?m", "?r"), ("inGroupOf", "?d", "?r")],
     [("GroupEngineGame", "?g")]),
    ("SameGroupSequel", [("sequelOf", "?a", "?b"), ("developedBy", "?a", "?x"), ("developedBy", "?b", "?y"), ("differentFrom", "?x", "?y"), ("inGroupOf", "?x", "?r"), ("inGroupOf", "?y", "?r")],
     [("SameGroupSequel", "?a")]),
    ("SelfPublished", [("developedBy", "?g", "?c"), ("publishedBy", "?g", "?c")], [("SelfPublishedGame", "?g")]),
    ("MustPlay", [("metacriticScore", "?g", "?s"), ("xsd:integer", "xsd:minInclusive", 95, "?s")], [("MustPlayGame", "?g")]),
]
# fmt: on


def term(name):
    prefix, _, local = name.rpartition(":")
    return {"xsd": XSD, "owl": OWL}[prefix][local] if prefix else VG[local]


def rdf_list(g, items):
    head = BNode()
    Collection(g, head, items)
    return head


def class_expression(g, expr):
    """Costruisce nel grafo l'espressione di classe descritta da una tupla delle tabelle."""
    if isinstance(expr, str):
        return term(expr)
    op, *args = expr
    node = BNode()
    if op in ("and", "or"):
        g.add((node, RDF.type, OWL.Class))
        g.add(
            (
                node,
                OWL.intersectionOf if op == "and" else OWL.unionOf,
                rdf_list(g, [class_expression(g, x) for x in args]),
            )
        )
    elif op == "some":
        prop, cls = args
        g.add((node, RDF.type, OWL.Restriction))
        g.add((node, OWL.onProperty, VG[prop]))
        g.add((node, OWL.someValuesFrom, class_expression(g, cls)))
    elif op == "value":
        prop, value = args
        g.add((node, RDF.type, OWL.Restriction))
        g.add((node, OWL.onProperty, VG[prop]))
        g.add((node, OWL.hasValue, Literal(value)))
    elif op == "min":
        n, prop, cls = args
        g.add((node, RDF.type, OWL.Restriction))
        g.add((node, OWL.onProperty, VG[prop]))
        g.add(
            (
                node,
                OWL.minQualifiedCardinality,
                Literal(n, datatype=XSD.nonNegativeInteger),
            )
        )
        g.add((node, OWL.onClass, class_expression(g, cls)))
    else:
        datatype, facet, value = args
        literal = (
            Literal(value)
            if isinstance(value, int)
            else Literal(value, datatype=term(datatype))
        )
        facet_node = BNode()
        g.add((facet_node, term(facet), literal))
        g.add((node, RDF.type, RDFS.Datatype))
        g.add((node, OWL.onDatatype, term(datatype)))
        g.add((node, OWL.withRestrictions, rdf_list(g, [facet_node])))
    return node


def new_graph():
    g = Graph()
    for prefix, namespace in [("vg", VG), ("owl", OWL), ("swrl", SWRL), ("var", VAR)]:
        g.bind(prefix, namespace)
    return g


def add_class(g, name, parent, comment, definition=None):
    g.add((VG[name], RDF.type, OWL.Class))
    g.add((VG[name], RDFS.label, Literal(name)))
    g.add((VG[name], RDFS.comment, Literal(comment)))
    if definition:
        g.add((VG[name], OWL.equivalentClass, class_expression(g, definition)))
    elif parent:
        g.add((VG[name], RDFS.subClassOf, VG[parent]))


def add_object_property(g, name, domain, range_, inverse, characteristics, comment):
    """Le proprietà con inversa e dominio diverso dal range sono anche asimmetriche e irriflessive."""
    strict = (
        [OWL.IrreflexiveProperty, OWL.AsymmetricProperty]
        if inverse and domain != range_
        else []
    )
    for kind in [
        OWL.ObjectProperty,
        *strict,
        *(OWL[f"{c}Property"] for c in characteristics),
    ]:
        g.add((VG[name], RDF.type, kind))
    g.add((VG[name], RDFS.domain, term(domain)))
    g.add((VG[name], RDFS.range, term(range_)))
    if comment:
        g.add((VG[name], RDFS.comment, Literal(comment)))
    if inverse:
        for kind in [OWL.ObjectProperty, *strict]:
            g.add((VG[inverse], RDF.type, kind))
        g.add((VG[inverse], OWL.inverseOf, VG[name]))


def schema():
    g = new_graph()
    g.add((BASE.ontology, RDF.type, OWL.Ontology))
    g.add((BASE.ontology, RDFS.label, Literal("Videogiochi: schema")))
    for name, comment in TOP:
        add_class(g, name, None, comment)
    for name, parent, comment in PRIMITIVE + RULE_TARGETS:
        add_class(g, name, parent, comment)
    for name, parent, comment, definition in DEFINED:
        assert (
            definition[1] == parent
        ), f"{name}: il padre deve essere il primo termine della definizione"
        add_class(g, name, parent, comment, definition)
    for i, block in enumerate(DISJOINT):
        node = BNode(f"disgiunte{i}")
        g.add((node, RDF.type, OWL.AllDisjointClasses))
        g.add((node, OWL.members, rdf_list(g, [VG[name] for name in block])))
    for row in OBJECT_PROPS:
        add_object_property(g, *row)
    for sub, sup in SUBPROPERTIES:
        g.add((VG[sub], RDFS.subPropertyOf, VG[sup]))
    for prop, chain in CHAINS:
        g.add((VG[prop], OWL.propertyChainAxiom, rdf_list(g, [VG[p] for p in chain])))
    for a, b in DISJOINT_PROPS:
        g.add((VG[a], OWL.propertyDisjointWith, VG[b]))
    for name, domain, range_, functional in DATA_PROPS:
        g.add((VG[name], RDF.type, OWL.DatatypeProperty))
        if functional:
            g.add((VG[name], RDF.type, OWL.FunctionalProperty))
        g.add((VG[name], RDFS.domain, term(domain)))
        g.add((VG[name], RDFS.range, term(range_)))
    for cls, prop in KEYS:
        g.add((VG[cls], OWL.hasKey, rdf_list(g, [VG[prop]])))
    return g


def swrl_atom(g, pred, *args):
    variables = [VAR[a[1:]] for a in args if isinstance(a, str) and a.startswith("?")]
    node = BNode()
    if pred == "differentFrom":
        g.add((node, RDF.type, SWRL.DifferentIndividualsAtom))
    elif pred.startswith("xsd:"):
        g.add((node, RDF.type, SWRL.DataRangeAtom))
        g.add(
            (
                node,
                SWRL.dataRange,
                class_expression(g, ("range", pred, args[0], args[1])),
            )
        )
    elif len(args) == 1:
        g.add((node, RDF.type, SWRL.ClassAtom))
        g.add((node, SWRL.classPredicate, VG[pred]))
    else:
        kind = (
            SWRL.DatavaluedPropertyAtom
            if pred in {p[0] for p in DATA_PROPS}
            else SWRL.IndividualPropertyAtom
        )
        g.add((node, RDF.type, kind))
        g.add((node, SWRL.propertyPredicate, VG[pred]))
    for i, variable in enumerate(variables, 1):
        g.add((node, SWRL[f"argument{i}"], variable))
    return node


def swrl_atom_list(g, atoms):
    head = RDF.nil
    for atom in reversed(atoms):
        cell = BNode()
        g.add((cell, RDF.type, SWRL.AtomList))
        g.add((cell, RDF.first, atom))
        g.add((cell, RDF.rest, head))
        head = cell
    return head


def rule_text(atoms, separator=" ^ "):
    def text(atom):
        if atom[0].startswith("xsd:"):
            return f"{atom[0]}[>= {atom[2]}]({atom[3]})"
        return f"{atom[0]}({', '.join(map(str, atom[1:]))})"

    return separator.join(text(a) for a in atoms)


def rules():
    g = new_graph()
    ontology = BASE["ontology/regole"]
    g.add((ontology, RDF.type, OWL.Ontology))
    g.add((ontology, RDFS.label, Literal("Videogiochi: regole SWRL")))
    g.add((ontology, OWL.imports, BASE.ontology))
    for _, body, head in RULES:
        for atom in body + head:
            for arg in atom[1:]:
                if isinstance(arg, str) and arg.startswith("?"):
                    g.add((VAR[arg[1:]], RDF.type, SWRL.Variable))
    for name, body, head in RULES:
        g.add((VAR[name], RDF.type, SWRL.Imp))
        g.add((VAR[name], RDFS.label, Literal(name)))
        g.add(
            (
                VAR[name],
                RDFS.comment,
                Literal(f"{rule_text(body)} -> {rule_text(head)}"),
            )
        )
        g.add(
            (VAR[name], SWRL.body, swrl_atom_list(g, [swrl_atom(g, *a) for a in body]))
        )
        g.add(
            (VAR[name], SWRL.head, swrl_atom_list(g, [swrl_atom(g, *a) for a in head]))
        )
    return g


FACETS = {
    "xsd:minInclusive": r"\geq",
    "xsd:maxInclusive": r"\leq",
    "xsd:maxExclusive": "<",
}


def latex(expr):
    """L'espressione di classe in logica descrittiva, per l'appendice."""
    if isinstance(expr, str):
        return rf"\textsf{{{expr}}}"
    op, *args = expr
    if op in ("and", "or"):
        joiner = r" \sqcap " if op == "and" else r" \sqcup "
        return joiner.join(
            f"({latex(x)})" if isinstance(x, tuple) and x[0] == "or" else latex(x)
            for x in args
        )
    if op == "value":
        prop, value = args
        return rf"\exists\,\textit{{{prop}}}.\{{{value}\}}"
    if op == "min":
        n, prop, cls = args
        return rf"{{\geq}}{n}\,\textit{{{prop}}}.{latex(cls)}"
    prop, cls = args
    if isinstance(cls, tuple) and cls[0] == "range":
        _, datatype, facet, value = cls
        value = value[:10] if isinstance(value, str) else value
        name = datatype.split(":")[1].replace("dateTime", "date")
        return rf"\exists\,\textit{{{prop}}}.\texttt{{{name}}}[{FACETS[facet]} {value}]"
    inner = (
        f"({latex(cls)})" if isinstance(cls, tuple) and cls[0] == "or" else latex(cls)
    )
    return rf"\exists\,\textit{{{prop}}}.{inner}"


def esc(text):
    return str(text).replace("&", r"\&").replace("_", r"\_").replace("#", r"\#")


def tt(text):
    return rf"\texttt{{{text}}}"


def latex_table(caption, columns, header, rows):
    lines = [
        rf"\begingroup\footnotesize\begin{{longtable}}{{{columns}}}",
        rf"\caption{{{caption}}}\\ \toprule",
        header + r" \\ \midrule \endfirsthead",
        header + r" \\ \midrule \endhead \bottomrule \endfoot",
    ]
    return "\n".join(
        lines
        + [" & ".join(row) + r" \\" for row in rows]
        + [r"\end{longtable}\endgroup", ""]
    )


def class_table():
    kinds = (
        {n: "primitiva" for n, _ in TOP}
        | {n: "primitiva" for n, _, _ in PRIMITIVE}
        | {n: "regola SWRL" for n, _, _ in RULE_TARGETS}
        | {n: "definita" for n, *_ in DEFINED}
    )
    parents = (
        {n: "--" for n, _ in TOP}
        | {n: p for n, p, _ in PRIMITIVE + RULE_TARGETS}
        | {n: p for n, p, *_ in DEFINED}
    )
    comments = (
        {n: c for n, c in TOP}
        | {n: c for n, _, c in PRIMITIVE + RULE_TARGETS}
        | {n: c for n, _, c, _ in DEFINED}
    )
    rows = [
        [tt(name), tt(parents[name]), kinds[name], comments[name]] for name in kinds
    ]
    return latex_table(
        f"Le {len(kinds)} classi",
        "lllp{5.8cm}",
        r"\textbf{Classe} & \textbf{Padre} & \textbf{Tipo} & \textbf{Descrizione}",
        rows,
    )


def object_property_table():
    chains = {prop: chain for prop, chain in CHAINS}
    rows = []
    for name, domain, range_, inverse, characteristics, _ in OBJECT_PROPS:
        features = [f"inversa {tt(inverse)}"] if inverse else []
        features += [
            {"Transitive": "transitiva", "Symmetric": "simmetrica"}[c]
            for c in characteristics
        ]
        if name in chains:
            features.append("catena " + " $\\circ$ ".join(chains[name]))
        features += [
            f"sotto-proprietà di {tt(sup)}" for sub, sup in SUBPROPERTIES if sub == name
        ]
        rows.append([tt(name), tt(domain), tt(range_), ", ".join(features)])
    count = len(OBJECT_PROPS) + sum(1 for p in OBJECT_PROPS if p[3])
    return latex_table(
        f"Le {count} object property",
        "lllp{6cm}",
        r"\textbf{Proprietà} & \textbf{Dominio} & \textbf{Range} & \textbf{Caratteristiche}",
        rows,
    )


def data_property_table():
    rows = [
        [
            tt(name),
            tt(domain),
            tt(range_),
            (
                "funzionale"
                if functional
                else ("chiave di " + tt("VideoGame") if name == "hasWikidataId" else "")
            ),
        ]
        for name, domain, range_, functional in DATA_PROPS
    ]
    return latex_table(
        f"Le {len(DATA_PROPS)} datatype property",
        "lllp{6cm}",
        r"\textbf{Proprietà} & \textbf{Dominio} & \textbf{Range} & \textbf{Caratteristiche}",
        rows,
    )


def game_rows():
    g = Graph()
    g.parse(HERE / "dati.ttl", format="turtle")
    query = """SELECT ?label (COALESCE(?s, "Giochi singoli") AS ?serie) (YEAR(?d) AS ?anno) ?dev WHERE { ?g vg:hasWikidataId ?id ; rdfs:label ?label .
               OPTIONAL { ?g vg:belongsTo/rdfs:label ?s } OPTIONAL { ?g vg:releaseDate ?d } OPTIONAL { ?g vg:developedBy/rdfs:label ?dev } }
               ORDER BY ?serie ?d"""
    return [
        [esc(x) if x is not None else "--" for x in row]
        for row in g.query(query, initNs={"vg": VG, "rdfs": RDFS})
    ]


def appendix(games):
    parts = [
        r"\section{Le componenti dell'ontologia}\label{app:componenti}",
        "",
        class_table(),
        object_property_table(),
        data_property_table(),
    ]
    definitions = "\n".join(
        rf"\textsf{{{name}}} &\equiv {latex(definition)} \\"
        for name, _, _, definition in DEFINED
    )
    parts.append(
        r"\subsection*{Classi definite}"
        + "\n"
        + r"\begingroup\small\begin{align*}"
        + "\n"
        + definitions
    )
    disjoint = "; ".join(", ".join(block) for block in DISJOINT)
    disjoint_props = "; ".join(f"{a} e {b}" for a, b in DISJOINT_PROPS)
    parts.append(
        r"\end{align*}\endgroup"
        + "\n"
        + rf"\noindent Disgiunzioni: {disjoint}. Proprietà disgiunte: {disjoint_props}."
        + "\n"
    )
    items = "\n".join(
        rf"\item \textbf{{{name}}}: \texttt{{{rule_text(body, ' $\\wedge$ ')} $\rightarrow$ {rule_text(head, ' $\\wedge$ ')}}}"
        for name, body, head in RULES
    )
    parts.append(
        r"\subsection*{Regole SWRL}"
        + "\n"
        + r"\begin{itemize}\footnotesize"
        + "\n"
        + items
        + "\n"
        + r"\end{itemize}"
        + "\n"
    )
    if games:
        parts.append(
            latex_table(
                f"I {len(games)} giochi del dataset",
                "p{6.5cm}p{3cm}lp{3.5cm}",
                r"\textbf{Gioco} & \textbf{Serie} & \textbf{Anno} & \textbf{Sviluppatore}",
                games,
            )
        )
    return "\n".join(parts)


def main():
    for name, graph in {"schema.ttl": schema(), "regole.ttl": rules()}.items():
        graph.serialize(destination=HERE / name, format="turtle")
    games = game_rows() if (HERE / "dati.ttl").exists() else []
    (HERE / "relazione" / "appendice.tex").write_text(appendix(games), encoding="utf-8")
    numbers = {"Giochi": len(games)} if games else {}
    numbers |= {
        "Top": len(TOP),
        "Classi": len(TOP) + len(PRIMITIVE) + len(RULE_TARGETS) + len(DEFINED),
        "Definite": len(DEFINED),
        "Regole": len(RULES),
        "ObjProp": len(OBJECT_PROPS) + sum(1 for p in OBJECT_PROPS if p[3]),
        "DataProp": len(DATA_PROPS),
    }
    (HERE / "relazione" / "numeri.tex").write_text(
        "".join(f"\\newcommand{{\\n{k}}}{{{v}}}\n" for k, v in numbers.items()),
        encoding="utf-8",
    )
    print(" ".join(f"{k}={v}" for k, v in numbers.items()))


if __name__ == "__main__":
    main()
