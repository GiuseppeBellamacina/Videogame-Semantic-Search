"""Genera dati.ttl (solo asserzioni) da fonti/dataset.json e fonti/correzioni.json.

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
BRANDS = {
    "Sony Interactive Entertainment": VG.PlayStationConsole,
    "Microsoft": VG.XboxConsole,
    "Nintendo": VG.NintendoConsole,
}
MODES = {
    "single-player": VG.SinglePlayer,
    "multiplayer": VG.Multiplayer,
    "co-op": VG.Coop,
}


def slug(text):
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "_", text.replace("'", "").replace("&", "")).strip(
        "_"
    )


def iri(kind, name):
    return VG[f"{kind}/{slug(name)}"] if kind else VG[slug(name)]


def killing_iri(game, victim, killer):
    return VG["killing/" + slug(f"{victim} by {killer} in {game}")]


def add(g, subject, prop, objects):
    """Aggiunge una o più triple, saltando i valori mancanti."""
    for obj in objects if isinstance(objects, list) else [objects]:
        if obj is not None:
            g.add((subject, prop, obj))


def all_different(g, members):
    """OWL non assume che nomi diversi indichino individui diversi: lo dichiariamo."""
    node, head = BNode(), BNode()
    Collection(g, head, sorted(members))
    g.add((node, RDF.type, OWL.AllDifferent))
    g.add((node, OWL.distinctMembers, head))


def add_game(g, game):
    s = iri(None, game["titolo"])
    if not game.get("tipo_omesso"):  # il tipo del primo GTA resta da dedurre
        g.add((s, RDF.type, VG.VideoGame))
    g.add((s, RDFS.label, Literal(game["titolo"])))
    qid, date = game.get("qid"), game.get("data")
    add(g, s, VG.hasWikidataId, qid and Literal(qid))
    add(g, s, RDFS.seeAlso, qid and WD[qid])
    add(
        g,
        s,
        VG.releaseDate,
        date and Literal(date + "T00:00:00", datatype=XSD.dateTime),
    )
    add(
        g, s, VG.metacriticScore, game.get("metacritic") and Literal(game["metacritic"])
    )
    add(g, s, VG.pegiRating, game.get("pegi") and Literal(game["pegi"]))
    add(g, s, VG.developedBy, [iri("company", c) for c in game.get("sviluppatore", [])])
    add(g, s, VG.publishedBy, [iri("company", c) for c in game.get("editore", [])])
    add(
        g, s, VG.availableOn, [VG["platform/" + p] for p in game.get("piattaforme", [])]
    )
    add(g, s, VG.hasGenre, [VG[name] for name in game.get("generi", [])])
    add(g, s, VG.hasGameMode, [MODES[m] for m in game.get("modalita", [])])
    add(g, s, VG.belongsTo, game.get("serie") and VG["franchise/" + game["serie"]])
    add(g, s, VG.sequelOf, [iri(None, t) for t in game.get("seguito_di", [])])
    add(g, s, VG.directedBy, [iri("person", p) for p in game.get("registi", [])])
    add(g, s, VG.madeWith, game.get("motore") and iri("engine", game["motore"]))
    add(g, s, VG.wonAward, [iri("award", a) for a in game.get("premi", [])])
    add(g, s, VG.basedOn, game.get("basato_su") and iri("work", game["basato_su"]))
    add(g, s, VG.prequelOf, [iri(None, t) for t in game.get("prequel_di", [])])
    return s


def add_cast(g, s, game, playing, appearing):
    """Ruoli e uccisioni di un gioco. `playing`: personaggi con un ruolo asserito (non servono come "appare in");
    `appearing`: giochi in cui un personaggio compare senza un ruolo."""
    roles = [
        ("giocabili", VG.playableIn),
        ("protagonisti", VG.protagonistOf),
        ("antagonisti", VG.antagonistOf),
    ]
    for key, prop in roles:
        for name in game.get(key, []):
            g.add((iri("character", name), prop, s))
            playing.setdefault(name, set()).add(s)
    for victim, killer in game.get("uccisioni", []):
        k = killing_iri(game["titolo"], victim, killer)
        g.add((k, RDF.type, VG.Killing))
        g.add((k, RDFS.label, Literal(f"{killer} uccide {victim} ({game['titolo']})")))
        g.add((k, VG.victim, iri("character", victim)))
        g.add((k, VG.killer, iri("character", killer)))
        g.add((k, VG.inGame, s))
        for name in (victim, killer):
            appearing.setdefault(name, set()).add(s)
    for name in game.get("altri_personaggi", []):
        appearing.setdefault(name, set()).add(s)
    for name, real_person in game.get("personaggi_storici", []):
        g.add((iri("character", name), VG.portrays, iri("person", real_person)))
        appearing.setdefault(name, set()).add(s)


def add_games(g, ds):
    playing, appearing = {}, {}
    for game in ds["giochi"]:
        add_cast(g, add_game(g, game), game, playing, appearing)
    for name, games in appearing.items():
        add(
            g,
            iri("character", name),
            VG.appearsIn,
            sorted(games - playing.get(name, set())),
        )


def add_editions(g, ds):
    for edition in ds["edizioni"]:
        s = iri(None, edition["titolo"])
        g.add((s, RDFS.label, Literal(edition["titolo"])))
        add(g, s, VG.remasterOf, [iri(None, t) for t in edition["di"]])
        add(g, s, VG.availableOn, [VG["platform/" + p] for p in edition["piattaforme"]])


def add_characters(g, ds):
    for name, info in ds["personaggi"].items():
        s = iri("character", name)
        g.add((s, RDFS.label, Literal(name)))
        add(g, s, RDF.type, info.get("natura") and VG[info["natura"]])
        add(
            g,
            s,
            VG.portrays,
            info.get("interpreta") and iri("person", info["interpreta"]),
        )
        builder = info.get("costruito_da")
        if builder in ds["personaggi"]:
            g.add((s, VG.builtBy, iri("character", builder)))
        elif builder:
            organization = iri("organization", builder)
            g.add((s, VG.builtBy, organization))
            g.add((organization, RDF.type, VG.FictionalOrganization))
            g.add((organization, RDFS.label, Literal(builder)))


def add_people_and_companies(g, ds):
    for name, info in ds["persone"].items():
        s = iri("person", name)
        g.add((s, RDFS.label, Literal(name)))
        add(
            g,
            s,
            VG.formerEmployeeOf,
            info.get("ex_dipendente_di") and iri("company", info["ex_dipendente_di"]),
        )
        add(g, s, VG.heads, info.get("guida") and iri("company", info["guida"]))
    for name, info in ds["aziende"].items():
        s = iri("company", name)
        g.add((s, RDF.type, VG.Company))
        g.add((s, RDFS.label, Literal(name)))
        add(
            g,
            s,
            VG.subsidiaryOf,
            info.get("controllata_da") and iri("company", info["controllata_da"]),
        )
        add(g, s, VG.foundedBy, [iri("person", p) for p in info.get("fondatori", [])])


def add_platforms_and_engines(g, ds):
    for key, info in ds["piattaforme"].items():
        s = VG["platform/" + key]
        g.add((s, RDF.type, VG[info["classe"]]))
        if info["classe"] == "ConsolePlatform":
            add(g, s, RDF.type, BRANDS.get(info.get("costruttore")))
        g.add((s, RDFS.label, Literal(info["nome"])))
        add(
            g,
            s,
            VG.manufacturedBy,
            info.get("costruttore") and iri("company", info["costruttore"]),
        )
        add(
            g,
            s,
            VG.generation,
            info.get("generazione") and Literal(info["generazione"]),
        )
    for name, developer in ds["motori"].items():
        s = iri("engine", name)
        g.add((s, RDF.type, VG.GameEngine))
        g.add((s, RDFS.label, Literal(name)))
        add(g, s, VG.engineDevelopedBy, developer and iri("company", developer))


def add_catalogue(g, ds):
    """Premi, serie, opere, generi e modalità."""
    for award in sorted({a for game in ds["giochi"] for a in game.get("premi", [])}):
        g.add((iri("award", award), RDF.type, VG.Award))
        g.add((iri("award", award), RDFS.label, Literal(award)))
    for key, info in ds["serie"].items():
        s = VG["franchise/" + key]
        g.add((s, RDF.type, VG.Franchise))
        g.add((s, RDFS.label, Literal(info["nome"])))
        add(g, s, VG.adaptedInto, [iri("work", w) for w in info.get("adattamenti", [])])
    for name, cls in ds["opere"].items():
        g.add((iri("work", name), RDF.type, VG[cls]))
        g.add((iri("work", name), RDFS.label, Literal(name)))
    for genre in sorted({n for game in ds["giochi"] for n in game.get("generi", [])}):
        g.add((VG[genre], RDF.type, VG.Genre))
        g.add((VG[genre], RDFS.label, Literal(genre)))
    for mode in MODES.values():
        g.add((mode, RDF.type, VG.GameMode))
        g.add((mode, RDFS.label, Literal(mode.split("#")[1])))


def build(ds):
    g = Graph()
    g.bind("vg", VG)
    g.bind("owl", OWL)
    for kind in (
        "award character company engine franchise killing organization "
        "person platform work"
    ).split():
        g.bind(kind, Namespace(f"{VG}{kind}/"))
    ontology = BASE["ontology/dati"]
    g.add((ontology, RDF.type, OWL.Ontology))
    g.add((ontology, RDFS.label, Literal("Videogiochi: dati (solo asserzioni)")))
    g.add((ontology, OWL.imports, BASE.ontology))
    add_games(g, ds)
    add_editions(g, ds)
    add_characters(g, ds)
    add_people_and_companies(g, ds)
    add_platforms_and_engines(g, ds)
    add_catalogue(g, ds)
    all_different(g, [iri(None, x["titolo"]) for x in ds["giochi"] + ds["edizioni"]])
    all_different(g, [iri("company", c) for c in ds["aziende"]])
    all_different(g, [iri("character", c) for c in ds["personaggi"]])
    all_different(g, [VG["platform/" + p] for p in ds["piattaforme"]])
    all_different(g, [iri("engine", e) for e in ds["motori"]])
    all_different(
        g,
        [
            killing_iri(x["titolo"], v, k)
            for x in ds["giochi"]
            for v, k in x.get("uccisioni", [])
        ],
    )
    return g


def apply_corrections(ds, corrections):
    games = {game["titolo"]: game for game in ds["giochi"]}
    for correction in corrections:
        games[correction["gioco"]][correction["campo"]] = correction["valore"]


def main():
    ds = json.loads((HERE / "fonti" / "dataset.json").read_text(encoding="utf-8"))
    apply_corrections(
        ds, json.loads((HERE / "fonti" / "correzioni.json").read_text(encoding="utf-8"))
    )
    g = build(ds)
    g.serialize(destination=HERE / "dati.ttl", format="turtle")
    print(
        f"dati.ttl: {len(ds['giochi'])} giochi, {len(ds['edizioni'])} nuove edizioni, {len(ds['personaggi'])} personaggi, {len(g)} triple"
    )


if __name__ == "__main__":
    main()
