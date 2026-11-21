"""Agente di ricerca (deepagents) che estrae da Wikipedia i fatti di trama dei giochi di fonti/dataset.json.

    uv run python protege/research_agent.py                    # tutti i giochi dell'ontologia (query SPARQL su dati.ttl) non ancora analizzati
    uv run python protege/research_agent.py Q796529            # solo questi giochi, risultato in fonti/agente/Q796529.json
    uv run python protege/research_agent.py --nuovi lista.txt  # giochi nuovi, un titolo per riga: l'agente trova da solo Wikidata e Wikipedia
    uv run python protege/research_agent.py --applica          # porta nel dataset i fatti verificati (e, per i giochi nuovi, i dati di Wikidata)

Modello in RESEARCH_MODEL (formato provider:modello, es. openai:gpt-4.1-mini), chiave in .env.
Ogni fatto ha l'URL e una citazione: se la citazione non compare nel testo scaricato, il fatto viene scartato.
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Literal

import httpx
from deepagents import create_deep_agent
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from rdflib import Graph

from build_data import slug
from fetch_wikidata import fetch

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")
OUT = HERE / "fonti" / "agente"
DATASET = HERE / "fonti" / "dataset.json"
WIKI = "https://en.wikipedia.org/w/api.php"
# Wikimedia chiede uno user-agent descrittivo; WIKI_CONTACT in .env può aggiungere un contatto
HEADERS = {"User-Agent": f"VideogameOntologyBot/1.0 ({os.environ.get('WIKI_CONTACT', 'https://www.mediawiki.org/wiki/API:Etiquette')}) httpx"}
PAGES = {}


class Evidence(BaseModel):
    url: str = Field(description="URL della pagina Wikipedia letta con wikipedia_section")
    quote: str = Field(description="Frase copiata alla lettera dalla pagina che dimostra il fatto")


class Character(BaseModel):
    name: str
    role: Literal["protagonist", "antagonist", "other"]
    species: Literal["Human", "Alien"] | None = Field(None, description="Umano o specie non umana del mondo di gioco, solo se la pagina lo dice")
    built_by: str | None = Field(None, description="Per un'IA o un robot: chi l'ha costruito nel mondo di gioco (personaggio o organizzazione)")
    playable: bool = Field(description="Vero se in questo gioco il giocatore controlla il personaggio")
    portrays_real_person: str | None = Field(None, description="Persona storica reale interpretata dal personaggio")
    evidence: Evidence


class Kill(BaseModel):
    victim: str
    killer: str = Field(description="Un singolo personaggio con nome, mai un gruppo")
    certain_in_all_endings: bool = Field(description="Falso se dipende dal finale o da una scelta del giocatore")
    evidence: Evidence


class Prequel(BaseModel):
    game: str = Field(description="Il gioco la cui storia viene dopo quella di questo gioco")
    evidence: Evidence


class GameFacts(BaseModel):
    qid: str = Field(description="Identificativo Wikidata del gioco (se non è dato, trovalo con wikidata_search)")
    title: str
    characters: list[Character]
    kills: list[Kill]
    prequel_of: list[Prequel] = Field(default_factory=list)


def wikipedia_search(query: str) -> list[str]:
    """Cerca su Wikipedia in inglese e restituisce i titoli delle pagine più pertinenti."""
    r = httpx.get(WIKI, params={"action": "query", "list": "search", "srsearch": query, "srlimit": 5, "format": "json"}, headers=HEADERS)
    return [x["title"] for x in r.json()["query"]["search"]]


def wikipedia_section(title: str, section: str = "Plot") -> str:
    """Restituisce il testo di una sezione (Plot, Synopsis, Story, Characters...) di una pagina Wikipedia, con il suo URL."""
    r = httpx.get(WIKI, params={"action": "query", "prop": "extracts", "explaintext": 1, "redirects": 1, "titles": title, "format": "json"}, headers=HEADERS)
    page = next(iter(r.json()["query"]["pages"].values()))
    text = page.get("extract", "")
    url = "https://en.wikipedia.org/wiki/" + page.get("title", title).replace(" ", "_")
    parts = re.split(r"\n==+ *(.+?) *==+\n", text)
    sections = dict(zip(parts[1::2], parts[2::2]))
    body = sections.get(section) or next((v for k, v in sections.items() if k.lower() in ("plot", "synopsis", "story", "premise")), None)
    if body is None:
        return f"{url}\nSezione '{section}' non trovata. Sezioni disponibili: {', '.join(sections)}"
    PAGES[url] = PAGES.get(url, "") + body
    return f"{url}\n{body[:15000]}"


def wikidata_search(title: str) -> list[dict]:
    """Cerca un'entità su Wikidata e restituisce identificativo, nome e descrizione dei risultati."""
    r = httpx.get("https://www.wikidata.org/w/api.php", params={"action": "wbsearchentities", "search": title, "language": "en", "limit": 5, "format": "json"}, headers=HEADERS)
    return [{"qid": x["id"], "label": x.get("label"), "description": x.get("description")} for x in r.json().get("search", [])]


def wikidata_facts(qid: str) -> dict:
    """Dati strutturati del gioco già scaricati da Wikidata (fetch_wikidata.py)."""
    f = HERE / "fonti" / "wikidata" / f"{qid}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


PROMPT = """Sei un assistente di ricerca per un'ontologia OWL dei videogiochi. Per il gioco indicato:
1. se l'identificativo Wikidata non è dato, trovalo (wikidata_search); trova la pagina Wikipedia del gioco (wikipedia_search) e leggi la trama (wikipedia_section);
2. elenca protagonisti e antagonisti principali, se il giocatore li controlla in questo gioco, la loro specie (umano o specie aliena)
   solo se è detta esplicitamente, chi ha costruito le IA e i robot, e i personaggi che interpretano persone storiche reali;
   se la pagina dice che il gioco è un prequel di un altro gioco, indicalo;
3. elenca le uccisioni: vittima e assassino devono essere personaggi con nome (mai gruppi come "the Covenant").
   Segna certain_in_all_endings=false se l'uccisione dipende dal finale o da una scelta; escludi i suicidi.
Ogni fatto deve avere come evidence l'URL letto e una frase copiata ALLA LETTERA da quella pagina.
Non usare conoscenze proprie: se la pagina non lo dice, non inserirlo.
Se un personaggio compare in questo elenco, usa esattamente quel nome: {names}"""


def verified(evidence):
    norm = lambda s: re.sub(r"\W+", " ", s).lower().strip()  # noqa: E731
    return norm(evidence.quote) in norm(PAGES.get(evidence.url, ""))


def games_from_ontology():
    g = Graph()
    g.parse(HERE / "dati.ttl", format="turtle")
    q = "SELECT ?titolo ?qid WHERE { ?g vg:hasWikidataId ?qid ; rdfs:label ?titolo } ORDER BY ?titolo"
    return [(str(t), str(q)) for t, q in g.query(q, initNs={"vg": "http://www.videogame-ontology.org/ontology#", "rdfs": "http://www.w3.org/2000/01/rdf-schema#"})]


def research(agent, title, qid=None):
    PAGES.clear()
    request = f"Gioco: {title}" + (f" (Wikidata {qid})" if qid else " (identificativo Wikidata da trovare)")
    facts: GameFacts = agent.invoke({"messages": [{"role": "user", "content": request}]})["structured_response"]
    chars = [c for c in facts.characters if verified(c.evidence)]
    kills = [k for k in facts.kills if k.certain_in_all_endings and k.killer != k.victim and verified(k.evidence)]
    prequels = [x for x in facts.prequel_of if verified(x.evidence)]
    out = {
        "titolo": title, "qid": qid or facts.qid, "modello": os.environ["RESEARCH_MODEL"],
        "protagonisti": [c.name for c in chars if c.role == "protagonist"],
        "antagonisti": [c.name for c in chars if c.role == "antagonist"],
        "uccisioni": [[k.victim, k.killer] for k in kills],
        "personaggi_storici": [[c.name, c.portrays_real_person] for c in chars if c.portrays_real_person],
        "giocabili": [c.name for c in chars if c.playable],
        "prequel_di": [x.game for x in prequels],
        "personaggi": {c.name: {k: v for k, v in {"natura": c.species, "costruito_da": c.built_by}.items() if v} for c in chars},
        "prove": [x.model_dump() for x in chars + kills + prequels],
        "scartati": [x.model_dump() for x in facts.characters + facts.kills + facts.prequel_of if x not in chars + kills + prequels],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{out['qid']}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{title}: {len(chars)} personaggi, {len(kills)} uccisioni verificate, {len(out['scartati'])} fatti scartati")


def new_game(ds, found):
    """Un gioco che non è ancora nel dataset: i dati strutturati vengono da Wikidata."""
    wd = fetch([found["qid"]])[found["qid"]]
    first = lambda k: (wd.get(k) or [None])[0]  # noqa: E731
    platforms = {d["nome"]: key for key, d in ds["piattaforme"].items()} | {key: key for key in ds["piattaforme"]}
    series = {d["nome"]: key for key, d in ds["serie"].items()}
    titles = {x["titolo"] for x in ds["giochi"]}
    number = lambda s: int(re.search(r"\d+", s).group()) if s and re.search(r"\d+", s) else None  # noqa: E731
    game = {"titolo": found["titolo"], "qid": found["qid"], "serie": series.get(first("serie")), "data": (first("data") or "")[:10] or None,
            "metacritic": number(first("metacritic")), "pegi": number(first("pegi")),
            "sviluppatore": wd.get("sviluppatore", [])[:1], "editore": wd.get("editore", [])[:1],
            "piattaforme": [platforms.get(p) or platforms[slug(p)] for p in wd.get("piattaforme", []) if p in platforms or slug(p) in platforms],
            "registi": wd.get("registi", []), "motore": first("motore"), "seguito_di": [t for t in wd.get("seguito_di", []) if t in titles]}
    for c in game["sviluppatore"] + game["editore"]:
        ds["aziende"].setdefault(c, {})
    for p in game["registi"]:
        ds["persone"].setdefault(p, {})
    if game["motore"]:
        ds["motori"].setdefault(game["motore"], None)
    ds["giochi"].append({k: v for k, v in game.items() if v not in (None, [])})
    print(f"nuovo gioco {found['titolo']}: piattaforme non riconosciute {[p for p in wd.get('piattaforme', []) if p not in platforms and slug(p) not in platforms]}")
    return ds["giochi"][-1]


def apply(ds):
    games = {x["qid"]: x for x in ds["giochi"] if x.get("qid")}
    for f in sorted(OUT.glob("*.json")):
        found = json.loads(f.read_text(encoding="utf-8"))
        game = games.get(found["qid"]) or new_game(ds, found)
        for key in ("protagonisti", "antagonisti", "giocabili", "uccisioni", "personaggi_storici", "prequel_di"):
            game[key] = found[key]
        for name, d in found["personaggi"].items():
            ds["personaggi"].setdefault(name, {}).update(d)
    DATASET.write_text(json.dumps(ds, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    os.environ.setdefault("RESEARCH_MODEL", "openai:gpt-4.1-mini")
    ds = json.loads(DATASET.read_text(encoding="utf-8"))
    if "--applica" in sys.argv:
        return apply(ds)
    agent = create_deep_agent(model=os.environ["RESEARCH_MODEL"], tools=[wikidata_search, wikidata_facts, wikipedia_search, wikipedia_section],
                              system_prompt=PROMPT.format(names=", ".join(sorted(ds["personaggi"]))), response_format=GameFacts)
    if "--nuovi" in sys.argv:
        titles = Path(sys.argv[sys.argv.index("--nuovi") + 1]).read_text(encoding="utf-8").splitlines()
        todo = [(t.strip(), None) for t in titles if t.strip()]
    else:
        wanted = set(sys.argv[1:])
        todo = [(t, q) for t, q in games_from_ontology() if q in wanted or (not wanted and not (OUT / f"{q}.json").exists())]
    for title, qid in todo:
        research(agent, title, qid)


if __name__ == "__main__":
    main()
