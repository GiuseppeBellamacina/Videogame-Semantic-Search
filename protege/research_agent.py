"""Agente LangChain che estrae da Wikipedia i fatti di trama dei giochi, citando la fonte di ogni fatto.

    uv run python protege/research_agent.py                    # i giochi dell'ontologia non ancora analizzati
    uv run python protege/research_agent.py Q274897            # solo questo gioco (identificativo Wikidata)
    uv run python protege/research_agent.py --nuovi lista.txt  # giochi nuovi, un titolo per riga
    uv run python protege/research_agent.py --applica          # porta nel dataset i fatti verificati

Modello in RESEARCH_MODEL (provider:modello), chiave nel file .env. L'agente ha due strumenti, `find_game` (Wikidata) e `read_plot` (la trama
su Wikipedia), e il costo è limitato: 5 chiamate al modello, 12 passi del grafo (il predefinito di `create_agent` è 9.999) e 6.000 token in uscita.
Un fatto è tenuto solo se la citazione e il nome del personaggio compaiono davvero nella pagina letta.
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Literal

import httpx
from build_data import slug
from dotenv import load_dotenv
from fetch_wikidata import fetch
from langchain.tools import tool
from pydantic import BaseModel, Field
from rdflib import Graph

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent / ".env")
OUT = HERE / "fonti" / "agente"
DATASET = HERE / "fonti" / "dataset.json"
WIKIPEDIA_API = "https://en.wikipedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
CONTACT = os.environ.get("WIKI_CONTACT", "https://www.mediawiki.org/wiki/API:Etiquette")
HEADERS = {"User-Agent": f"VideogameOntologyBot/1.0 ({CONTACT}) httpx"}
PLOT_TITLES = (
    "plot",
    "synopsis",
    "story",
    "premise",
    "setting and narrative",
    "narrative",
)
MAX_CHARS = 20000
MAX_OUTPUT_TOKENS = 6000
MAX_MODEL_CALLS = 5
RECURSION_LIMIT = 12

PAGES = {}  # URL -> testo letto dall'agente, per controllare le citazioni


class Evidence(BaseModel):
    url: str = Field(description="URL della pagina Wikipedia data")
    quote: str = Field(
        description="Frase copiata alla lettera dalla pagina che dimostra il fatto"
    )


class Character(BaseModel):
    name: str
    role: Literal["protagonist", "antagonist", "other"]
    species: Literal["Human", "Alien"] | None = Field(
        None,
        description="Umano o specie non umana del mondo di gioco, solo se la pagina lo dice",
    )
    built_by: str | None = Field(
        None,
        description="Per un'IA o un robot: chi l'ha costruito nel mondo di gioco (personaggio o organizzazione)",
    )
    playable: bool = Field(
        description="Vero se in questo gioco il giocatore controlla il personaggio"
    )
    portrays_real_person: str | None = Field(
        None, description="Persona storica reale interpretata dal personaggio"
    )
    evidence: Evidence


class Kill(BaseModel):
    victim: str
    killer: str = Field(description="Un singolo personaggio con nome, mai un gruppo")
    certain_in_all_endings: bool = Field(
        description="Falso se dipende dal finale o da una scelta del giocatore"
    )
    evidence: Evidence


class Prequel(BaseModel):
    game: str = Field(
        description="Il gioco la cui storia viene dopo quella di questo gioco"
    )
    evidence: Evidence


class GameFacts(BaseModel):
    qid: str | None = Field(
        None,
        description="Identificativo Wikidata del gioco, se l'hai cercato con find_game",
    )
    characters: list[Character]
    kills: list[Kill]
    prequel_of: list[Prequel] = Field(default_factory=list)


PROMPT = """Sei un assistente di ricerca per un'ontologia OWL dei videogiochi.
Hai due strumenti: find_game (solo se l'identificativo Wikidata non è dato) e read_plot (leggi la trama UNA volta sola, poi rispondi).
1. Elenca protagonisti e antagonisti principali, se il giocatore li controlla in questo gioco, la loro specie (umano o specie aliena)
   solo se è detta esplicitamente, chi ha costruito le IA e i robot, e i personaggi che interpretano persone storiche reali;
   se la pagina dice che il gioco è un prequel di un altro gioco, indicalo.
2. Elenca le uccisioni: vittima e assassino devono essere personaggi con nome (mai gruppi come "the Covenant").
   Segna certain_in_all_endings=false se l'uccisione dipende dal finale o da una scelta; escludi i suicidi.
Ogni fatto deve avere come evidence l'URL della pagina letta e una frase copiata ALLA LETTERA dal testo.
Non usare conoscenze proprie: se il testo non lo dice, non inserirlo.
Se un personaggio compare nell'elenco dei nomi già usati, usa esattamente quel nome."""


def api_get(params, host=WIKIPEDIA_API):
    return httpx.get(host, params=params, headers=HEADERS, timeout=30).json()


def wikipedia_search(query):
    result = api_get(
        {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": 5,
            "format": "json",
        }
    )
    return [hit["title"] for hit in result["query"]["search"]]


def plot_section(title):
    """(URL, testo) della trama di una pagina Wikipedia, sottosezioni comprese. La pagina è ricordata in PAGES."""
    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": 1,
        "redirects": 1,
        "titles": title,
        "format": "json",
    }
    page = next(iter(api_get(params)["query"]["pages"].values()))
    text = page.get("extract", "")
    url = "https://en.wikipedia.org/wiki/" + page.get("title", title).replace(" ", "_")
    headings = list(re.finditer(r"\n(==+) *(.+?) *==+\n", text))
    sections = {}
    for i, heading in enumerate(headings):
        end = next(
            (
                h.start()
                for h in headings[i + 1 :]
                if len(h.group(1)) <= len(heading.group(1))
            ),
            len(text),
        )
        sections.setdefault(heading.group(2), text[heading.end() : end])
    body = sections.get("Plot") or next(
        (body for name, body in sections.items() if name.lower() in PLOT_TITLES), ""
    )
    PAGES[url] = PAGES.get(url, "") + body
    return url, body[:MAX_CHARS]


def wikidata_search(title):
    params = {
        "action": "wbsearchentities",
        "search": title,
        "language": "en",
        "limit": 5,
        "format": "json",
    }
    hits = api_get(params, WIKIDATA_API).get("search", [])
    return [
        {
            "qid": hit["id"],
            "label": hit.get("label"),
            "description": hit.get("description"),
        }
        for hit in hits
    ]


def wikipedia_title(qid):
    params = {
        "action": "wbgetentities",
        "ids": qid,
        "props": "sitelinks",
        "sitefilter": "enwiki",
        "format": "json",
    }
    entity = api_get(params, WIKIDATA_API).get("entities", {}).get(qid, {})
    return (entity.get("sitelinks", {}).get("enwiki") or {}).get("title")


def find_game(title):
    hits = wikidata_search(title)
    return next(
        (hit for hit in hits if "video game" in (hit["description"] or "")), hits[0]
    )


@tool
def find_game_tool(title: str) -> dict:
    """Trova il videogioco su Wikidata: identificativo (qid), nome, descrizione e titolo della pagina Wikipedia. Serve solo se l'identificativo non è dato."""
    game = find_game(title)
    return game | {"wikipedia_page": wikipedia_title(game["qid"])}


@tool
def read_plot(page: str) -> str:
    """Legge la sezione della trama (con le sottosezioni) di una pagina di Wikipedia in inglese: restituisce l'URL e il testo. Chiamalo una volta sola."""
    url, text = plot_section(page)
    return (
        f"{url}\n{text}"
        if text.strip()
        else f"{url}\nNessuna sezione di trama trovata."
    )


def build_agent():
    from langchain.agents import create_agent
    from langchain.agents.middleware import ModelCallLimitMiddleware
    from langchain.chat_models import init_chat_model

    model = init_chat_model(os.environ["RESEARCH_MODEL"], max_tokens=MAX_OUTPUT_TOKENS)
    return create_agent(
        model=model,
        tools=[find_game_tool, read_plot],
        system_prompt=PROMPT,
        response_format=GameFacts,
        middleware=[
            ModelCallLimitMiddleware(run_limit=MAX_MODEL_CALLS, exit_behavior="end")
        ],
    )


def normalize(text):
    return re.sub(r"\W+", " ", text).lower().strip()


def quote_in_page(evidence):
    return normalize(evidence.quote) in normalize(PAGES.get(evidence.url, ""))


def name_in_page(name, url):
    """Almeno una parola di 4 lettere del nome compare nella pagina: una citazione vera non basta se il personaggio è inventato
    (con Dark Souls il modello scrisse "Ashen One", il protagonista di un altro gioco, citando una frase vera).
    """
    page = f" {normalize(PAGES.get(url, ''))} "
    return any(
        f" {word} " in page for word in normalize(name).split() if len(word) >= 4
    )


def canonical_name(name, known):
    """Se il nome è contenuto in uno solo dei nomi già nel dataset ("Gwyn" in "Gwyn, Lord of Sunlight"), usa quello."""
    words = set(normalize(name).split())
    matches = [
        k
        for k in known
        if normalize(k) == normalize(name)
        or (words and words <= set(normalize(k).split()))
    ]
    return matches[0] if len(matches) == 1 else name


def known_names(ds, qid):
    """I personaggi già nel dataset per i giochi della stessa serie: l'agente li riusa invece di inventare varianti."""
    game = next((g for g in ds["giochi"] if g.get("qid") == qid), None)
    series = [
        g
        for g in ds["giochi"]
        if game and game.get("serie") and g.get("serie") == game["serie"]
    ] or ([game] if game else [])
    names = set()
    for g in series:
        names.update(
            g.get("protagonisti", [])
            + g.get("antagonisti", [])
            + g.get("giocabili", [])
            + g.get("altri_personaggi", [])
        )
        names.update(name for pair in g.get("uccisioni", []) for name in pair)
    return sorted(names)


def games_from_ontology():
    g = Graph()
    g.parse(HERE / "dati.ttl", format="turtle")
    query = "SELECT ?titolo ?qid WHERE { ?g vg:hasWikidataId ?qid ; rdfs:label ?titolo } ORDER BY ?titolo"
    namespaces = {
        "vg": "http://www.videogame-ontology.org/ontology#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    }
    return [(str(title), str(qid)) for title, qid in g.query(query, initNs=namespaces)]


def ask_agent(agent, usage, title, qid, ds):
    """Una corsa dell'agente su un gioco: (fatti, token usati)."""
    PAGES.clear()
    usage.usage_metadata.clear()
    names = ", ".join(known_names(ds, qid)) or "(nessuno)"
    if qid:
        page = wikipedia_title(qid) or wikipedia_search(f"{title} video game")[0]
        who = f"Gioco: {title} (Wikidata {qid}, pagina Wikipedia: {page})"
    else:
        who = f"Gioco: {title} (identificativo Wikidata da trovare con find_game)"
    message = {"messages": [("user", f"{who}\nNomi già usati nella serie: {names}")]}
    reply = agent.invoke(
        message, config={"recursion_limit": RECURSION_LIMIT, "callbacks": [usage]}
    )
    tokens = {
        "ingresso": sum(
            u.get("input_tokens", 0) for u in usage.usage_metadata.values()
        ),
        "uscita": sum(u.get("output_tokens", 0) for u in usage.usage_metadata.values()),
    }
    return reply.get("structured_response"), tokens


def keep_verified(facts, known):
    """Divide i fatti dell'agente in (tenuti, scartati)."""
    for character in facts.characters:
        character.name = canonical_name(character.name, known)
    for kill in facts.kills:
        kill.victim, kill.killer = canonical_name(kill.victim, known), canonical_name(
            kill.killer, known
        )
    characters = [
        c
        for c in facts.characters
        if quote_in_page(c.evidence) and name_in_page(c.name, c.evidence.url)
    ]
    named = {
        c.name for c in characters
    }  # vittima e assassino devono essere personaggi elencati: niente gruppi
    kills = [
        k
        for k in facts.kills
        if k.certain_in_all_endings
        and k.victim in named
        and k.killer in named
        and k.killer != k.victim
        and quote_in_page(k.evidence)
    ]
    prequels = [p for p in facts.prequel_of if quote_in_page(p.evidence)]
    kept = characters + kills + prequels
    discarded = [
        fact
        for fact in facts.characters + facts.kills + facts.prequel_of
        if fact not in kept
    ]
    return (characters, kills, prequels), discarded


def record(title, qid, url, tokens, kept, discarded):
    characters, kills, prequels = kept
    return {
        "titolo": title,
        "qid": qid,
        "modello": os.environ["RESEARCH_MODEL"],
        "pagina": url,
        "token": tokens,
        "protagonisti": [c.name for c in characters if c.role == "protagonist"],
        "antagonisti": [c.name for c in characters if c.role == "antagonist"],
        "uccisioni": [[k.victim, k.killer] for k in kills],
        "personaggi_storici": [
            [c.name, c.portrays_real_person]
            for c in characters
            if c.portrays_real_person
        ],
        "giocabili": [c.name for c in characters if c.playable],
        "prequel_di": [p.game for p in prequels],
        "personaggi": {
            c.name: {
                k: v
                for k, v in {"natura": c.species, "costruito_da": c.built_by}.items()
                if v
            }
            for c in characters
        },
        "prove": [fact.model_dump() for fact in characters + kills + prequels],
        "scartati": [fact.model_dump() for fact in discarded],
    }


def research(agent, usage, title, qid, ds):
    facts, tokens = ask_agent(agent, usage, title, qid, ds)
    qid = qid or (facts and facts.qid)
    if facts is None or not qid or not PAGES:
        print(
            f"{title}: nessun risultato valido (pagine lette: {len(PAGES)}); token {tokens}"
        )
        return
    kept, discarded = keep_verified(facts, known_names(ds, qid))
    result = record(title, qid, next(iter(PAGES)), tokens, kept, discarded)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{qid}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    characters, kills, _ = kept
    print(
        f"{title}: {len(characters)} personaggi, {len(kills)} uccisioni verificate, {len(discarded)} fatti scartati; token {tokens}"
    )


def first_number(text):
    match = re.search(r"\d+", text or "")
    return int(match.group()) if match else None


def add_new_game(ds, found):
    """Un gioco non ancora nel dataset: i dati strutturati vengono da Wikidata."""
    wikidata = fetch([found["qid"]])[found["qid"]]
    first = lambda key: (wikidata.get(key) or [None])[0]  # noqa: E731
    platforms = {info["nome"]: key for key, info in ds["piattaforme"].items()} | {
        key: key for key in ds["piattaforme"]
    }
    series = {info["nome"]: key for key, info in ds["serie"].items()}
    titles = {g["titolo"] for g in ds["giochi"]}
    known = [
        p
        for p in wikidata.get("piattaforme", [])
        if p in platforms or slug(p) in platforms
    ]
    game = {
        "titolo": found["titolo"],
        "qid": found["qid"],
        "serie": series.get(first("serie")),
        "data": (first("data") or "")[:10] or None,
        "metacritic": first_number(first("metacritic")),
        "pegi": first_number(first("pegi")),
        "sviluppatore": wikidata.get("sviluppatore", [])[:1],
        "editore": wikidata.get("editore", [])[:1],
        "piattaforme": [platforms.get(p) or platforms[slug(p)] for p in known],
        "registi": wikidata.get("registi", []),
        "motore": first("motore"),
        "seguito_di": [t for t in wikidata.get("seguito_di", []) if t in titles],
    }
    for company in game["sviluppatore"] + game["editore"]:
        ds["aziende"].setdefault(company, {})
    for person in game["registi"]:
        ds["persone"].setdefault(person, {})
    if game["motore"]:
        ds["motori"].setdefault(game["motore"], None)
    ds["giochi"].append({k: v for k, v in game.items() if v not in (None, [])})
    print(
        f"nuovo gioco {found['titolo']}: piattaforme non riconosciute {[p for p in wikidata.get('piattaforme', []) if p not in known]}"
    )
    return ds["giochi"][-1]


def apply_results(ds):
    games = {g["qid"]: g for g in ds["giochi"] if g.get("qid")}
    for file in sorted(OUT.glob("*.json")):
        found = json.loads(file.read_text(encoding="utf-8"))
        game = games.get(found["qid"]) or add_new_game(ds, found)
        for key in (
            "protagonisti",
            "antagonisti",
            "giocabili",
            "uccisioni",
            "personaggi_storici",
            "prequel_di",
        ):
            game[key] = found[key]
        for name, info in found["personaggi"].items():
            ds["personaggi"].setdefault(name, {}).update(info)
    DATASET.write_text(json.dumps(ds, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    os.environ.setdefault("RESEARCH_MODEL", "anthropic:claude-haiku-5-5")
    ds = json.loads(DATASET.read_text(encoding="utf-8"))
    if "--applica" in sys.argv:
        return apply_results(ds)
    from langchain_core.callbacks import UsageMetadataCallbackHandler

    agent, usage = build_agent(), UsageMetadataCallbackHandler()
    if "--nuovi" in sys.argv:
        lines = (
            Path(sys.argv[sys.argv.index("--nuovi") + 1])
            .read_text(encoding="utf-8")
            .splitlines()
        )
        todo = [(line.strip(), None) for line in lines if line.strip()]
    else:
        wanted = set(sys.argv[1:])
        todo = [
            (t, q)
            for t, q in games_from_ontology()
            if q in wanted or (not wanted and not (OUT / f"{q}.json").exists())
        ]
    for title, qid in todo:
        research(agent, usage, title, qid, ds)


if __name__ == "__main__":
    main()
