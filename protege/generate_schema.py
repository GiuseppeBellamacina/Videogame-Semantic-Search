"""Genera schema.ttl, regole.ttl e relazione/appendice.tex dalle tabelle qui sotto.

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

TOP = [
    ("VideoGame", "Un videogioco"),
    ("Company", "Uno studio, un editore o un gruppo industriale"),
    ("Person", "Una persona reale"),
    ("Character", "Un personaggio di finzione"),
    ("Platform", "Una piattaforma su cui si gioca"),
    ("Franchise", "Una serie di giochi"),
    ("GameEngine", "Un motore di gioco"),
    ("Award", "Un premio"),
    ("Genre", "Un genere"),
    ("GameMode", "Una modalità di gioco"),
    ("Killing", "Un'uccisione nella trama di un gioco: vittima, assassino e gioco (relazione n-aria)"),
    ("CreativeWork", "Un'opera di un altro medium (romanzo, film, serie TV)"),
]

PRIMITIVE = [
    ("ConsolePlatform", "Platform", "Una console"),
    ("PCPlatform", "Platform", "Un personal computer"),
    ("CurrentGenerationConsole", "ConsolePlatform", "Una console dell'attuale generazione"),
    ("Novel", "CreativeWork", "Un romanzo"),
    ("Film", "CreativeWork", "Un film"),
    ("TVSeries", "CreativeWork", "Una serie televisiva"),
    ("Comic", "CreativeWork", "Un fumetto"),
    ("TabletopGame", "CreativeWork", "Un gioco da tavolo o di ruolo cartaceo"),
    ("GameOfTheYearAward", "Award", "Un premio Gioco dell'anno"),
    ("Human", "Character", "Un personaggio umano"),
    ("ArtificialIntelligence", "Character", "Un'intelligenza artificiale"),
    ("DeceasedCharacter", "Character", "Un personaggio morto (dominio di killedBy)"),
    ("Killer", "Character", "Un personaggio che ha tolto la vita a qualcuno (range di killedBy)"),
    ("GameDirector", "Person", "Un regista di videogiochi (range di directedBy)"),
    ("StudioHead", "Person", "Chi guida un'azienda (dominio di heads)"),
    ("Remaster", "VideoGame", "La nuova edizione di un gioco (dominio di remasterOf)"),
]

DISJOINT = [
    [name for name, _ in TOP],
    ["ConsolePlatform", "PCPlatform"],
    ["Novel", "Film", "TVSeries", "Comic", "TabletopGame"],
    ["Human", "ArtificialIntelligence"],
]


def some(p, c):
    return ("some", p, c)


def at_least(n, p, c):
    return ("min", n, p, c)


def score(n):
    return ("range", "xsd:integer", "xsd:minInclusive", n)


def score_max(n):
    return ("range", "xsd:integer", "xsd:maxInclusive", n)


def and_(*xs):
    return ("and", *xs)


def or_(*xs):
    return ("or", *xs)


DEFINED = [
    ("Developer", "Company", "Un'azienda che ha sviluppato almeno un gioco", and_("Company", some("developerOf", "VideoGame"))),
    ("Publisher", "Company", "Un'azienda che ha pubblicato almeno un gioco", and_("Company", some("publisherOf", "VideoGame"))),
    ("PlatformHolder", "Company", "Un'azienda che costruisce console", and_("Company", some("manufacturerOf", "ConsolePlatform"))),
    ("FoundedByVeterans", "Company", "Un'azienda fondata da chi lavorava per uno sviluppatore", and_("Company", some("foundedBy", some("formerEmployeeOf", "Developer")))),
    ("FirstPartyGame", "VideoGame", "Un gioco pubblicato dal gruppo di un costruttore di console", and_("VideoGame", some("publishedByGroup", "PlatformHolder"))),
    ("SequelGame", "VideoGame", "Il seguito di un altro gioco", and_("VideoGame", some("sequelOf", "VideoGame"))),
    ("LateEntry", "SequelGame", "Almeno il terzo capitolo di una serie", and_("VideoGame", some("sequelOf", some("sequelOf", "VideoGame")))),
    ("LongRunningOriginal", "VideoGame", "Il capostipite di una serie di almeno tre capitoli", and_("VideoGame", some("hasSequel", some("hasSequel", "VideoGame")))),
    ("ViolentStoryGame", "VideoGame", "Un gioco nella cui trama qualcuno viene ucciso", and_("VideoGame", some("hasKilling", "Killing"))),
    ("RealisticViolenceGame", "ViolentStoryGame", "Un gioco violento classificato PEGI 16 o 18: violenza realistica, non per minori", and_("ViolentStoryGame", some("pegiRating", score(16)))),
    ("FantasyViolenceGame", "ViolentStoryGame", "Un gioco violento classificato al più PEGI 12: violenza su personaggi non realistici", and_("ViolentStoryGame", some("pegiRating", score_max(12)))),
    ("HighlyRatedGame", "VideoGame", "Un gioco con almeno 90 su Metacritic", and_("VideoGame", some("metacriticScore", score(90)))),
    ("AcclaimedSequel", "SequelGame", "Un seguito acclamato", and_("SequelGame", "HighlyRatedGame")),
    ("GOTYWinner", "VideoGame", "Un gioco premiato come gioco dell'anno", and_("VideoGame", some("wonAward", "GameOfTheYearAward"))),
    ("RemasteredClassic", "VideoGame", "Un gioco che ha avuto una nuova edizione", and_("VideoGame", some("hasRemaster", "VideoGame"))),
    ("RemasterCollection", "Remaster", "Una raccolta che rimasterizza almeno due giochi", and_("Remaster", at_least(2, "remasterOf", "VideoGame"))),
    ("StillPlayable", "VideoGame", "Un gioco giocabile su una console attuale", and_("VideoGame", some("playableOn", "CurrentGenerationConsole"))),
    ("MultiPlatformGame", "VideoGame", "Un gioco uscito su almeno tre piattaforme", and_("VideoGame", at_least(3, "availableOn", "Platform"))),
    ("Adaptation", "VideoGame", "Un gioco tratto da un'opera di un altro medium", and_("VideoGame", some("basedOn", "CreativeWork"))),
    ("LiteraryAdaptation", "Adaptation", "Un gioco tratto da un romanzo", and_("VideoGame", some("basedOn", "Novel"))),
    ("AuteurGame", "VideoGame", "Un gioco diretto da chi guida uno studio", and_("VideoGame", some("directedBy", "StudioHead"))),
    ("LongRunningFranchise", "Franchise", "Una serie con almeno tre capitoli", and_("Franchise", some("includes", "LateEntry"))),
    ("AwardWinningFranchise", "Franchise", "Una serie con un gioco dell'anno", and_("Franchise", some("includes", "GOTYWinner"))),
    ("TransmediaFranchise", "Franchise", "Una serie diventata film o serie TV", and_("Franchise", some("adaptedInto", or_("Film", "TVSeries")))),
    ("FranchiseWithStudioChange", "Franchise", "Una serie passata a un altro studio", and_("Franchise", some("includes", "SequelByDifferentStudio"))),
    ("Protagonist", "Character", "Il protagonista di un gioco", and_("Character", some("protagonistOf", "VideoGame"))),
    ("Antagonist", "Character", "L'antagonista di un gioco", and_("Character", some("antagonistOf", "VideoGame"))),
    ("RecurringCharacter", "Character", "Un personaggio presente in almeno due giochi", and_("Character", at_least(2, "appearsIn", "VideoGame"))),
    ("RecurringVillain", "RecurringCharacter", "Un antagonista ricorrente", and_("RecurringCharacter", "Antagonist")),
    ("RogueAI", "ArtificialIntelligence", "Un'intelligenza artificiale antagonista", and_("ArtificialIntelligence", "Antagonist")),
    ("DigitalMind", "ArtificialIntelligence", "Un'intelligenza artificiale nata dalla mente di un umano", and_("ArtificialIntelligence", some("mindCopiedFrom", "Human"))),
    ("MultipleKiller", "Killer", "Un personaggio che ha ucciso almeno due personaggi", and_("Character", at_least(2, "kills", "Character"))),
    ("HistoricalCharacter", "Character", "Un personaggio che interpreta una persona reale", and_("Character", some("portrays", "Person"))),
]

RULE_TARGETS = [
    ("FirstPartyOnRivalConsole", "VideoGame", "Un gioco first-party uscito su una console di un concorrente"),
    ("SequelByDifferentStudio", "VideoGame", "Un seguito sviluppato da uno studio diverso"),
    ("VeteransReturn", "VideoGame", "Un gioco fatto da uno studio fondato da chi aveva lavorato alla serie"),
    ("EngineChangeSequel", "VideoGame", "Un seguito che cambia motore"),
    ("ExternalEngineGame", "VideoGame", "Un gioco fatto con un motore sviluppato da un'altra azienda"),
    ("InHouseEngineGame", "VideoGame", "Un gioco fatto con il motore dello stesso studio"),
    ("ReturningDirectorSequel", "VideoGame", "Un seguito con lo stesso regista del predecessore"),
    ("DefeatedVillain", "Character", "Un antagonista ucciso dal protagonista"),
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
    ("remasterOf", "Remaster", "VideoGame", "hasRemaster", [], None),
    ("wonAward", "VideoGame", "Award", None, [], None),
    ("madeWith", "VideoGame", "GameEngine", None, [], None),
    ("engineDevelopedBy", "GameEngine", "Company", None, [], None),
    ("manufacturedBy", "Platform", "Company", "manufacturerOf", [], None),
    ("subsidiaryOf", "Company", "Company", None, ["Transitive"], None),
    ("publishedByGroup", "VideoGame", "Company", None, [], "Derivata dalle regole: l'editore e i gruppi che lo controllano"),
    ("directedBy", "VideoGame", "GameDirector", "directorOf", [], None),
    ("heads", "StudioHead", "Company", None, [], None),
    ("foundedBy", "Company", "Person", None, [], None),
    ("formerEmployeeOf", "Person", "Company", None, [], None),
    ("basedOn", "VideoGame", "CreativeWork", None, [], None),
    ("adaptedInto", "Franchise", "CreativeWork", None, [], None),
    ("appearsIn", "Character", "VideoGame", "hasCharacter", [], None),
    ("protagonistOf", "Character", "VideoGame", None, [], None),
    ("antagonistOf", "Character", "VideoGame", None, [], None),
    ("killedBy", "DeceasedCharacter", "Killer", "kills", [], "Dedotta dalla regola KillingEvent"),
    ("victim", "Killing", "DeceasedCharacter", None, [], None),
    ("killer", "Killing", "Killer", None, [], None),
    ("inGame", "Killing", "VideoGame", "hasKilling", [], None),
    ("portrays", "Character", "Person", None, [], None),
    ("mindCopiedFrom", "ArtificialIntelligence", "Human", None, [], "L'IA è stata costruita a partire dalla mente di questo personaggio"),
    ("playableOn", "VideoGame", "Platform", None, [], "Disponibile, anche tramite una nuova edizione"),
    ("techLinkedTo", "VideoGame", "VideoGame", None, [], "Giochi dello studio che ha fatto il motore usato"),
]
SUBPROPERTIES = [("availableOn", "playableOn"), ("protagonistOf", "appearsIn"), ("antagonistOf", "appearsIn")]
CHAINS = [("playableOn", ["hasRemaster", "availableOn"]), ("techLinkedTo", ["madeWith", "engineDevelopedBy", "developerOf"])]

# name, domain, range, functional
DATA_PROPS = [
    ("releaseDate", "VideoGame", "xsd:dateTime", True),
    ("metacriticScore", "VideoGame", "xsd:integer", True),
    ("pegiRating", "VideoGame", "xsd:integer", True),
    ("hasWikidataId", "owl:Thing", "xsd:string", False),
]
KEYS = [("VideoGame", "hasWikidataId")]

RIVAL = [("availableOn", "?g", "?p"), ("ConsolePlatform", "?p"), ("manufacturedBy", "?p", "?m"), ("manufacturerOf", "?h", "?q"), ("ConsolePlatform", "?q"), ("differentFrom", "?h", "?m")]
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
    ("MustPlay", [("metacriticScore", "?g", "?s"), ("xsd:integer", "xsd:minInclusive", 95, "?s")], [("MustPlayGame", "?g")]),
]


def term(x):
    prefix, _, name = x.rpartition(":")
    return {"xsd": XSD, "owl": OWL}[prefix][name] if prefix else VG[name]


def rdf_list(g, items):
    head = BNode()
    Collection(g, head, items)
    return head


def node(g, x):
    if isinstance(x, str):
        return term(x)
    op, *a = x
    b = BNode()
    if op in ("and", "or"):
        g.add((b, RDF.type, OWL.Class))
        g.add((b, OWL.intersectionOf if op == "and" else OWL.unionOf, rdf_list(g, [node(g, y) for y in a])))
    elif op == "some":
        g.add((b, RDF.type, OWL.Restriction))
        g.add((b, OWL.onProperty, VG[a[0]]))
        g.add((b, OWL.someValuesFrom, node(g, a[1])))
    elif op == "min":
        g.add((b, RDF.type, OWL.Restriction))
        g.add((b, OWL.onProperty, VG[a[1]]))
        g.add((b, OWL.minQualifiedCardinality, Literal(a[0], datatype=XSD.nonNegativeInteger)))
        g.add((b, OWL.onClass, node(g, a[2])))
    else:
        facet = BNode()
        g.add((facet, term(a[1]), Literal(a[2])))
        g.add((b, RDF.type, RDFS.Datatype))
        g.add((b, OWL.onDatatype, term(a[0])))
        g.add((b, OWL.withRestrictions, rdf_list(g, [facet])))
    return b


def dl(x):
    if isinstance(x, str):
        return rf"\textsf{{{x}}}"
    op, *a = x
    if op in ("and", "or"):
        return (r" \sqcap " if op == "and" else r" \sqcup ").join(f"({dl(y)})" if isinstance(y, tuple) and y[0] == "or" else dl(y) for y in a)
    if op == "some":
        if isinstance(a[1], tuple) and a[1][0] == "range":
            cmp = r"\geq" if a[1][2] == "xsd:minInclusive" else r"\leq"
            return rf"\exists\,\textit{{{a[0]}}}.\texttt{{integer}}[{cmp} {a[1][3]}]"
        return rf"\exists\,\textit{{{a[0]}}}." + (f"({dl(a[1])})" if isinstance(a[1], tuple) and a[1][0] == "or" else dl(a[1]))
    if op == "min":
        return rf"{{\geq}}{a[0]}\,\textit{{{a[1]}}}.{dl(a[2])}"


def new_graph():
    g = Graph()
    for prefix, ns in [("vg", VG), ("owl", OWL), ("swrl", SWRL), ("var", VAR)]:
        g.bind(prefix, ns)
    return g


def add_class(g, name, parent, comment, definition=None):
    g.add((VG[name], RDF.type, OWL.Class))
    g.add((VG[name], RDFS.label, Literal(name)))
    g.add((VG[name], RDFS.comment, Literal(comment)))
    if parent:
        g.add((VG[name], RDFS.subClassOf, VG[parent]))
    if definition:
        g.add((VG[name], OWL.equivalentClass, node(g, definition)))


def schema():
    g = new_graph()
    g.add((BASE.ontology, RDF.type, OWL.Ontology))
    g.add((BASE.ontology, RDFS.label, Literal("Videogiochi: schema")))
    for name, comment in TOP:
        add_class(g, name, None, comment)
    for name, parent, comment in PRIMITIVE + RULE_TARGETS:
        add_class(g, name, parent, comment)
    for row in DEFINED:
        add_class(g, *row)
    for i, block in enumerate(DISJOINT):
        b = BNode(f"disgiunte{i}")
        g.add((b, RDF.type, OWL.AllDisjointClasses))
        g.add((b, OWL.members, rdf_list(g, [VG[n] for n in block])))
    for name, dom, rng, inv, chars, comment in OBJECT_PROPS:
        loose = [OWL.IrreflexiveProperty, OWL.AsymmetricProperty] if inv and dom != rng else []
        for t in [OWL.ObjectProperty, *loose, *(OWL[f"{c}Property"] for c in chars)]:
            g.add((VG[name], RDF.type, t))
        g.add((VG[name], RDFS.domain, VG[dom]))
        g.add((VG[name], RDFS.range, VG[rng]))
        if comment:
            g.add((VG[name], RDFS.comment, Literal(comment)))
        if inv:
            for t in [OWL.ObjectProperty, *loose]:
                g.add((VG[inv], RDF.type, t))
            g.add((VG[inv], OWL.inverseOf, VG[name]))
    for sub, sup in SUBPROPERTIES:
        g.add((VG[sub], RDFS.subPropertyOf, VG[sup]))
    for p, chain in CHAINS:
        g.add((VG[p], OWL.propertyChainAxiom, rdf_list(g, [VG[c] for c in chain])))
    for name, dom, rng, functional in DATA_PROPS:
        g.add((VG[name], RDF.type, OWL.DatatypeProperty))
        if functional:
            g.add((VG[name], RDF.type, OWL.FunctionalProperty))
        g.add((VG[name], RDFS.domain, term(dom)))
        g.add((VG[name], RDFS.range, term(rng)))
    for c, p in KEYS:
        g.add((VG[c], OWL.hasKey, rdf_list(g, [VG[p]])))
    return g


def atom(g, pred, *args):
    v = [VAR[a[1:]] for a in args if isinstance(a, str) and a.startswith("?")]
    b = BNode()
    if pred == "differentFrom":
        g.add((b, RDF.type, SWRL.DifferentIndividualsAtom))
    elif pred.startswith("xsd:"):
        g.add((b, RDF.type, SWRL.DataRangeAtom))
        g.add((b, SWRL.dataRange, node(g, ("range", pred, args[0], args[1]))))
    elif len(args) == 1:
        g.add((b, RDF.type, SWRL.ClassAtom))
        g.add((b, SWRL.classPredicate, VG[pred]))
    else:
        kind = SWRL.DatavaluedPropertyAtom if pred in {p[0] for p in DATA_PROPS} else SWRL.IndividualPropertyAtom
        g.add((b, RDF.type, kind))
        g.add((b, SWRL.propertyPredicate, VG[pred]))
    for i, x in enumerate(v, 1):
        g.add((b, SWRL[f"argument{i}"], x))
    return b


def atom_list(g, atoms):
    head = RDF.nil
    for a in reversed(atoms):
        cell = BNode()
        g.add((cell, RDF.type, SWRL.AtomList))
        g.add((cell, RDF.first, a))
        g.add((cell, RDF.rest, head))
        head = cell
    return head


def rule_text(atoms, sep=" ^ "):
    return sep.join(f"{a[0]}({', '.join(map(str, a[1:]))})" if not a[0].startswith("xsd:") else f"{a[0]}[>= {a[2]}]({a[3]})" for a in atoms)


def rules():
    g = new_graph()
    onto = BASE["ontology/regole"]
    g.add((onto, RDF.type, OWL.Ontology))
    g.add((onto, RDFS.label, Literal("Videogiochi: regole SWRL")))
    g.add((onto, OWL.imports, BASE.ontology))
    for _, body, head in RULES:
        for at in body + head:
            for a in at[1:]:
                if isinstance(a, str) and a.startswith("?"):
                    g.add((VAR[a[1:]], RDF.type, SWRL.Variable))
    for name, body, head in RULES:
        g.add((VAR[name], RDF.type, SWRL.Imp))
        g.add((VAR[name], RDFS.label, Literal(name)))
        g.add((VAR[name], RDFS.comment, Literal(f"{rule_text(body)} -> {rule_text(head)}")))
        g.add((VAR[name], SWRL.body, atom_list(g, [atom(g, *a) for a in body])))
        g.add((VAR[name], SWRL.head, atom_list(g, [atom(g, *a) for a in head])))
    return g


def latex_table(caption, columns, header, rows):
    lines = [rf"\begingroup\footnotesize\begin{{longtable}}{{{columns}}}", rf"\caption{{{caption}}}\\ \toprule", header + r" \\ \midrule \endfirsthead",
             header + r" \\ \midrule \endhead \bottomrule \endfoot"]
    return "\n".join(lines + [" & ".join(r) + r" \\" for r in rows] + [r"\end{longtable}\endgroup", ""])


def esc(x):
    return str(x).replace("&", r"\&").replace("_", r"\_").replace("#", r"\#")


def appendix():
    tt = lambda x: rf"\texttt{{{x}}}"  # noqa: E731
    kinds = {n: "primitiva" for n, _ in TOP} | {n: "primitiva" for n, _, _ in PRIMITIVE} | {n: "regola SWRL" for n, _, _ in RULE_TARGETS} | {n: "definita" for n, *_ in DEFINED}
    parents = {n: "--" for n, _ in TOP} | {n: p for n, p, _ in PRIMITIVE + RULE_TARGETS} | {n: p for n, p, *_ in DEFINED}
    comments = {n: c for n, c in TOP} | {n: c for n, _, c in PRIMITIVE + RULE_TARGETS} | {n: c for n, _, c, _ in DEFINED}
    out = [r"\section{Le componenti dell'ontologia}\label{app:componenti}", ""]
    out.append(latex_table(f"Le {len(kinds)} classi", "lllp{5.8cm}", r"\textbf{Classe} & \textbf{Padre} & \textbf{Tipo} & \textbf{Descrizione}",
                           [[tt(n), tt(parents[n]), kinds[n], comments[n]] for n in kinds]))
    out.append(latex_table(f"Le {len(OBJECT_PROPS) + sum(1 for p in OBJECT_PROPS if p[3])} object property", "lllp{6cm}", r"\textbf{Proprietà} & \textbf{Dominio} & \textbf{Range} & \textbf{Caratteristiche}",
                           [[tt(n), tt(d), tt(r), ", ".join(([f"inversa {tt(i)}"] if i else []) + [{"Transitive": "transitiva", "Symmetric": "simmetrica"}[c] for c in ch] + [f"catena {' $\\circ$ '.join(c)}" for p, c in CHAINS if p == n] + [f"sotto-proprietà di {tt(s)}" for b, s in SUBPROPERTIES if b == n])]
                            for n, d, r, i, ch, _ in OBJECT_PROPS]))
    out.append(latex_table(f"Le {len(DATA_PROPS)} datatype property", "lllp{6cm}", r"\textbf{Proprietà} & \textbf{Dominio} & \textbf{Range} & \textbf{Caratteristiche}",
                           [[tt(n), tt(d), tt(r), "funzionale" if f else ("chiave di " + tt("VideoGame") if n == "hasWikidataId" else "")] for n, d, r, f in DATA_PROPS]))
    out.append(r"\subsection*{Classi definite}" + "\n" + r"\begingroup\small\begin{align*}")
    out += [rf"\textsf{{{n}}} &\equiv {dl(d)} \\" for n, _, _, d in DEFINED]
    out.append(r"\end{align*}\endgroup" + "\n" + rf"\noindent Disgiunzioni: " + "; ".join(", ".join(block) for block in DISJOINT) + ".\n")
    out.append(r"\subsection*{Regole SWRL}" + "\n" + r"\begin{itemize}\footnotesize")
    out += [rf"\item \textbf{{{name}}}: \texttt{{{rule_text(body, ' $\\wedge$ ')} $\rightarrow$ {rule_text(head)}}}" for name, body, head in RULES]
    out.append(r"\end{itemize}" + "\n")
    data = HERE / "dati.ttl"
    if data.exists():
        g = Graph()
        g.parse(data, format="turtle")
        q = """SELECT ?label (COALESCE(?s, "Giochi singoli") AS ?serie) (YEAR(?d) AS ?anno) ?dev WHERE { ?g vg:hasWikidataId ?id ; rdfs:label ?label .
               OPTIONAL { ?g vg:belongsTo/rdfs:label ?s } OPTIONAL { ?g vg:releaseDate ?d } OPTIONAL { ?g vg:developedBy/rdfs:label ?dev } }
               ORDER BY ?serie ?d"""
        rows = [[esc(x) if x is not None else "--" for x in row] for row in g.query(q, initNs={"vg": VG, "rdfs": RDFS})]
        out.append(latex_table(f"I {len(rows)} giochi del dataset", "p{6.5cm}p{3cm}lp{3.5cm}", r"\textbf{Gioco} & \textbf{Serie} & \textbf{Anno} & \textbf{Sviluppatore}", rows))
    return "\n".join(out)


def main():
    for name, g in {"schema.ttl": schema(), "regole.ttl": rules()}.items():
        g.serialize(destination=HERE / name, format="turtle")
    (HERE / "relazione" / "appendice.tex").write_text(appendix(), encoding="utf-8")
    print(f"classi {len(TOP) + len(PRIMITIVE) + len(RULE_TARGETS) + len(DEFINED)} (definite {len(DEFINED)}), "
          f"object property {len(OBJECT_PROPS) + sum(1 for p in OBJECT_PROPS if p[3])}, datatype property {len(DATA_PROPS)}, regole {len(RULES)}")


if __name__ == "__main__":
    main()
