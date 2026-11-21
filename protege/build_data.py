"""Genera dati.ttl (solo asserzioni) da fonti/dataset.json.

    uv run python protege/build_data.py
"""

import json
import re
import unicodedata
from pathlib import Path

from rdflib import OWL, RDF, RDFS, XSD, BNode, Graph, Literal, Namespace
from rdflib.collection import Collection

HERE = Path(__file__).resolve().parent
BASE = Namespace("http://www.videogame-ontology.org/")
VG = Namespace("http://www.videogame-ontology.org/ontology#")
WD = Namespace("http://www.wikidata.org/entity/")
MODE = {"single-player": VG.SinglePlayer, "multiplayer": VG.Multiplayer, "co-op": VG.Coop}


def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "_", s.replace("'", "").replace("&", "")).strip("_")


def iri(kind, name):
    return VG[f"{kind}/{slug(name)}"] if kind else VG[slug(name)]


def killing(game, victim, killer):
    return VG["killing/" + slug(f"{victim} by {killer} in {game}")]


def add(g, s, p, objs):
    for o in objs if isinstance(objs, list) else [objs]:
        if o is not None:
            g.add((s, p, o))


def all_different(g, members):
    b = BNode()
    head = BNode()
    Collection(g, head, sorted(members))
    g.add((b, RDF.type, OWL.AllDifferent))
    g.add((b, OWL.distinctMembers, head))


def build(ds):
    g = Graph()
    g.bind("vg", VG)
    g.bind("owl", OWL)
    onto = BASE["ontology/dati"]
    g.add((onto, RDF.type, OWL.Ontology))
    g.add((onto, RDFS.label, Literal("Videogiochi: dati (solo asserzioni)")))
    g.add((onto, OWL.imports, BASE.ontology))

    appears, own = {}, {}
    for x in ds["giochi"]:
        s = iri(None, x["titolo"])
        if not x.get("tipo_omesso"):  # il tipo del primo GTA resta da dedurre
            g.add((s, RDF.type, VG.VideoGame))
        g.add((s, RDFS.label, Literal(x["titolo"])))
        add(g, s, VG.hasWikidataId, x.get("qid") and Literal(x["qid"]))
        add(g, s, RDFS.seeAlso, x.get("qid") and WD[x["qid"]])
        add(g, s, VG.releaseDate, x.get("data") and Literal(x["data"] + "T00:00:00", datatype=XSD.dateTime))
        add(g, s, VG.metacriticScore, x.get("metacritic") and Literal(x["metacritic"]))
        add(g, s, VG.pegiRating, x.get("pegi") and Literal(x["pegi"]))
        add(g, s, VG.developedBy, [iri("company", c) for c in x.get("sviluppatore", [])])
        add(g, s, VG.publishedBy, [iri("company", c) for c in x.get("editore", [])])
        add(g, s, VG.availableOn, [VG["platform/" + p] for p in x.get("piattaforme", [])])
        add(g, s, VG.hasGenre, [VG[n] for n in x.get("generi", [])])
        add(g, s, VG.hasGameMode, [MODE[m] for m in x.get("modalita", [])])
        add(g, s, VG.belongsTo, x.get("serie") and VG["franchise/" + x["serie"]])
        add(g, s, VG.sequelOf, [iri(None, t) for t in x.get("seguito_di", [])])
        add(g, s, VG.directedBy, [iri("person", p) for p in x.get("registi", [])])
        add(g, s, VG.madeWith, x.get("motore") and iri("engine", x["motore"]))
        add(g, s, VG.wonAward, [iri("award", a) for a in x.get("premi", [])])
        add(g, s, VG.basedOn, x.get("basato_su") and iri("work", x["basato_su"]))
        add(g, s, VG.prequelOf, [iri(None, t) for t in x.get("prequel_di", [])])
        for c in x.get("giocabili", []):
            g.add((iri("character", c), VG.playableIn, s))
            own.setdefault(c, set()).add(s)
        for c in x.get("protagonisti", []):
            g.add((iri("character", c), VG.protagonistOf, s))
            own.setdefault(c, set()).add(s)
        for c in x.get("antagonisti", []):
            g.add((iri("character", c), VG.antagonistOf, s))
            own.setdefault(c, set()).add(s)
        for victim, killer in x.get("uccisioni", []):
            k = killing(x["titolo"], victim, killer)
            g.add((k, RDF.type, VG.Killing))
            g.add((k, RDFS.label, Literal(f"{killer} uccide {victim} ({x['titolo']})")))
            g.add((k, VG.victim, iri("character", victim)))
            g.add((k, VG.killer, iri("character", killer)))
            g.add((k, VG.inGame, s))
            for c in (victim, killer):
                appears.setdefault(c, set()).add(s)
        for c in x.get("altri_personaggi", []):
            appears.setdefault(c, set()).add(s)
        for c, real in x.get("personaggi_storici", []):
            g.add((iri("character", c), VG.portrays, iri("person", real)))
            appears.setdefault(c, set()).add(s)
    for c, games in appears.items():
        add(g, iri("character", c), VG.appearsIn, sorted(games - own.get(c, set())))

    for x in ds["edizioni"]:
        s = iri(None, x["titolo"])
        g.add((s, RDFS.label, Literal(x["titolo"])))
        add(g, s, VG.remasterOf, [iri(None, t) for t in x["di"]])
        add(g, s, VG.availableOn, [VG["platform/" + p] for p in x["piattaforme"]])

    for c, d in ds["personaggi"].items():
        s = iri("character", c)
        g.add((s, RDFS.label, Literal(c)))
        add(g, s, RDF.type, d.get("natura") and VG[d["natura"]])
        add(g, s, VG.portrays, d.get("interpreta") and iri("person", d["interpreta"]))
        builder = d.get("costruito_da")
        if builder in ds["personaggi"]:
            g.add((s, VG.builtBy, iri("character", builder)))
        elif builder:
            g.add((s, VG.builtBy, iri("organization", builder)))
            g.add((iri("organization", builder), RDF.type, VG.FictionalOrganization))
            g.add((iri("organization", builder), RDFS.label, Literal(builder)))
    for p, d in ds["persone"].items():
        s = iri("person", p)
        g.add((s, RDFS.label, Literal(p)))
        add(g, s, VG.formerEmployeeOf, d.get("ex_dipendente_di") and iri("company", d["ex_dipendente_di"]))
        add(g, s, VG.heads, d.get("guida") and iri("company", d["guida"]))
    for c, d in ds["aziende"].items():
        s = iri("company", c)
        g.add((s, RDF.type, VG.Company))
        g.add((s, RDFS.label, Literal(c)))
        add(g, s, VG.subsidiaryOf, d.get("controllata_da") and iri("company", d["controllata_da"]))
        add(g, s, VG.foundedBy, [iri("person", p) for p in d.get("fondatori", [])])
    for p, d in ds["piattaforme"].items():
        s = VG["platform/" + p]
        g.add((s, RDF.type, VG[d["classe"]]))
        g.add((s, RDFS.label, Literal(d["nome"])))
        add(g, s, VG.manufacturedBy, d.get("costruttore") and iri("company", d["costruttore"]))
        add(g, s, VG.generation, d.get("generazione") and Literal(d["generazione"]))
    for e, dev in ds["motori"].items():
        g.add((iri("engine", e), RDF.type, VG.GameEngine))
        g.add((iri("engine", e), RDFS.label, Literal(e)))
        add(g, iri("engine", e), VG.engineDevelopedBy, dev and iri("company", dev))
    for a in sorted({a for x in ds["giochi"] for a in x.get("premi", [])}):
        g.add((iri("award", a), RDF.type, VG.Award))
        g.add((iri("award", a), RDFS.label, Literal(a)))
    for f, d in ds["serie"].items():
        s = VG["franchise/" + f]
        g.add((s, RDF.type, VG.Franchise))
        g.add((s, RDFS.label, Literal(d["nome"])))
        add(g, s, VG.adaptedInto, [iri("work", w) for w in d.get("adattamenti", [])])
    for w, cls in ds["opere"].items():
        g.add((iri("work", w), RDF.type, VG[cls]))
        g.add((iri("work", w), RDFS.label, Literal(w)))
    for n in sorted({n for x in ds["giochi"] for n in x.get("generi", [])}):
        g.add((VG[n], RDF.type, VG.Genre))
        g.add((VG[n], RDFS.label, Literal(n)))
    for m in MODE.values():
        g.add((m, RDF.type, VG.GameMode))
        g.add((m, RDFS.label, Literal(m.split("#")[1])))

    # OWL non assume che nomi diversi indichino individui diversi: lo dichiariamo
    all_different(g, [iri(None, x["titolo"]) for x in ds["giochi"] + ds["edizioni"]])
    all_different(g, [iri("company", c) for c in ds["aziende"]])
    all_different(g, [iri("character", c) for c in ds["personaggi"]])
    all_different(g, [VG["platform/" + p] for p in ds["piattaforme"]])
    all_different(g, [iri("engine", e) for e in ds["motori"]])
    all_different(g, [iri("award", a) for a in {a for x in ds["giochi"] for a in x.get("premi", [])}])
    all_different(g, [killing(x["titolo"], v, k) for x in ds["giochi"] for v, k in x.get("uccisioni", [])])
    return g


def apply_corrections(ds, corrections):
    games = {x["titolo"]: x for x in ds["giochi"]}
    for c in corrections:
        games[c["gioco"]][c["campo"]] = c["valore"]


def main():
    ds = json.loads((HERE / "fonti" / "dataset.json").read_text(encoding="utf-8"))
    apply_corrections(ds, json.loads((HERE / "fonti" / "correzioni.json").read_text(encoding="utf-8")))
    g = build(ds)
    g.serialize(destination=HERE / "dati.ttl", format="turtle")
    print(f"dati.ttl: {len(ds['giochi'])} giochi, {len(ds['edizioni'])} nuove edizioni, {len(ds['personaggi'])} personaggi, {len(g)} triple")


if __name__ == "__main__":
    main()
