"""Genera videogiochi.ttl (il file da aprire in Protégé) e i casi di test in test/.

uv run python protege/generate_tests.py
"""

from pathlib import Path

from rdflib import OWL, RDF, RDFS, XSD, BNode, Graph, Literal, Namespace

HERE = Path(__file__).resolve().parent
BASE = Namespace("http://www.videogame-ontology.org/")
VG = Namespace("http://www.videogame-ontology.org/ontology#")


def ontology(iri, comment, imports):
    g = Graph()
    g.bind("vg", VG)
    g.bind("owl", OWL)
    g.add((iri, RDF.type, OWL.Ontology))
    g.add((iri, RDFS.comment, Literal(comment)))
    for i in imports:
        g.add((iri, OWL.imports, BASE[i]))
    return g


def at_most_one_platform(g, game):
    r = BNode()
    g.add((r, RDF.type, OWL.Restriction))
    g.add((r, OWL.onProperty, VG.availableOn))
    g.add((r, OWL.maxCardinality, Literal(1, datatype=XSD.nonNegativeInteger)))
    g.add((game, RDF.type, r))


def disgiunzione(g):
    deck = VG["platform/Steam_Deck"]
    g.add((deck, RDF.type, VG.ConsolePlatform))
    g.add((deck, RDF.type, VG.PCPlatform))
    g.add((deck, RDFS.label, Literal("Steam Deck")))


def funzionale(g):
    g.add((VG.Portal_2, VG.metacriticScore, Literal(90)))


def cardinalita(g):
    at_most_one_platform(g, VG.The_Legend_of_Zelda_Breath_of_the_Wild)


def chiave(g):
    g.add((VG.GTA_V_copia, RDF.type, VG.VideoGame))
    g.add((VG.GTA_V_copia, RDFS.label, Literal("GTA V (record duplicato)")))
    g.add((VG.GTA_V_copia, VG.hasWikidataId, Literal("Q17452")))
    g.add((VG.GTA_V_copia, OWL.differentFrom, VG.Grand_Theft_Auto_V))


def sameas(g):
    nx = VG["platform/Nintendo_NX"]
    g.add((nx, RDFS.label, Literal("NX")))
    g.add((VG.Splatoon_2, RDF.type, VG.VideoGame))
    g.add((VG.Splatoon_2, RDFS.label, Literal("Splatoon 2")))
    g.add((VG.Splatoon_2, VG.availableOn, VG["platform/Nintendo_Switch"]))
    g.add((VG.Splatoon_2, VG.availableOn, nx))
    at_most_one_platform(g, VG.Splatoon_2)


def proprieta_disgiunte(g):
    g.add(
        (
            VG.The_Legend_of_Zelda_Ocarina_of_Time_3D,
            VG.prequelOf,
            VG.The_Legend_of_Zelda_Ocarina_of_Time,
        )
    )


TESTS = [
    (
        "errore_disgiunzione",
        "disgiunzione",
        "Atteso: inconsistente (console e PC sono classi disgiunte)",
        disgiunzione,
    ),
    (
        "errore_funzionale",
        "funzionale",
        "Atteso: inconsistente (metacriticScore è funzionale e Portal 2 ha già 95)",
        funzionale,
    ),
    (
        "errore_cardinalita",
        "cardinalita",
        "Atteso: inconsistente (al più una piattaforma, ma Breath of the Wild è uscito su Wii U e Switch, dichiarate diverse)",
        cardinalita,
    ),
    (
        "errore_chiave",
        "chiave",
        "Atteso: inconsistente (stesso hasWikidataId, chiave di VideoGame, ma dichiarati diversi)",
        chiave,
    ),
    (
        "errore_proprieta_disgiunte",
        "proprieta_disgiunte",
        "Atteso: inconsistente (remasterOf e prequelOf sono disgiunte: Ocarina of Time 3D è remaster di Ocarina of Time, non può esserne il prequel)",
        proprieta_disgiunte,
    ),
    (
        "deduzione_sameas",
        "sameas",
        "Atteso: consistente; il reasoner deduce NX = Nintendo Switch (NX è il nome in codice della Switch)",
        sameas,
    ),
]


def main():
    g = ontology(
        BASE["ontology/videogiochi"],
        "Videogiochi: schema, dati e regole",
        ["ontology", "ontology/dati", "ontology/regole"],
    )
    g.serialize(destination=HERE / "videogiochi.ttl", format="turtle")
    for file, name, comment, fill in TESTS:
        g = ontology(
            BASE[f"ontology/test/{name}"], comment, ["ontology/dati", "ontology/regole"]
        )
        fill(g)
        g.serialize(destination=HERE / "test" / f"{file}.ttl", format="turtle")
    print(f"videogiochi.ttl e {len(TESTS)} test generati")


if __name__ == "__main__":
    main()
