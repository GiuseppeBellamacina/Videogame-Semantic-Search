"""Agente di ricerca (deepagents) che estrae da Wikipedia i fatti di trama dei giochi di fonti/dataset.json.

    uv run python protege/research_agent.py Q796529            # un gioco, risultato in fonti/agente/Q796529.json
    uv run python protege/research_agent.py                    # tutti i giochi non ancora analizzati
    uv run python protege/research_agent.py --applica          # copia i fatti verificati in fonti/dataset.json

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
    nature: Literal["Human", "ArtificialIntelligence"] | None = Field(None, description="Solo se la pagina lo dice esplicitamente")
    portrays_real_person: str | None = Field(None, description="Persona storica reale interpretata dal personaggio")
    mind_copied_from: str | None = Field(None, description="Per un'IA: il personaggio umano da cui è copiata la mente")
    evidence: Evidence


class Kill(BaseModel):
    victim: str
    killer: str = Field(description="Un singolo personaggio con nome, mai un gruppo")
    certain_in_all_endings: bool = Field(description="Falso se dipende dal finale o da una scelta del giocatore")
    evidence: Evidence


class GameFacts(BaseModel):
    qid: str
    title: str
    characters: list[Character]
    kills: list[Kill]


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


def wikidata_facts(qid: str) -> dict:
    """Dati strutturati del gioco già scaricati da Wikidata (fetch_wikidata.py)."""
    f = HERE / "fonti" / "wikidata" / f"{qid}.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


PROMPT = """Sei un assistente di ricerca per un'ontologia OWL dei videogiochi. Per il gioco indicato:
1. trova la pagina Wikipedia del gioco (wikipedia_search) e leggi la trama (wikipedia_section);
2. elenca protagonisti e antagonisti principali, la loro natura (umano o intelligenza artificiale) solo se è detta esplicitamente,
   i personaggi che interpretano persone storiche reali e, per le IA, l'eventuale umano da cui è copiata la mente;
3. elenca le uccisioni: vittima e assassino devono essere personaggi con nome (mai gruppi come "the Covenant").
   Segna certain_in_all_endings=false se l'uccisione dipende dal finale o da una scelta; escludi i suicidi.
Ogni fatto deve avere come evidence l'URL letto e una frase copiata ALLA LETTERA da quella pagina.
Non usare conoscenze proprie: se la pagina non lo dice, non inserirlo.
Se un personaggio compare in questo elenco, usa esattamente quel nome: {names}"""


def verified(evidence):
    norm = lambda s: re.sub(r"\W+", " ", s).lower().strip()  # noqa: E731
    return norm(evidence.quote) in norm(PAGES.get(evidence.url, ""))


def research(agent, game):
    PAGES.clear()
    result = agent.invoke({"messages": [{"role": "user", "content": f"Gioco: {game['titolo']} (Wikidata {game['qid']})"}]})
    facts: GameFacts = result["structured_response"]
    chars = [c for c in facts.characters if verified(c.evidence)]
    kills = [k for k in facts.kills if k.certain_in_all_endings and k.killer != k.victim and verified(k.evidence)]
    out = {
        "titolo": game["titolo"], "qid": game["qid"], "modello": os.environ["RESEARCH_MODEL"],
        "protagonisti": [c.name for c in chars if c.role == "protagonist"],
        "antagonisti": [c.name for c in chars if c.role == "antagonist"],
        "uccisioni": [[k.victim, k.killer] for k in kills],
        "personaggi_storici": [[c.name, c.portrays_real_person] for c in chars if c.portrays_real_person],
        "personaggi": {c.name: {k: v for k, v in {"natura": c.nature, "mente_copiata_da": c.mind_copied_from}.items() if v} for c in chars},
        "prove": [x.model_dump() for x in chars + kills],
        "scartati": [x.model_dump() for x in facts.characters + facts.kills if x not in chars and x not in kills],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{game['qid']}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{game['titolo']}: {len(chars)} personaggi, {len(kills)} uccisioni verificate, {len(out['scartati'])} fatti scartati")


def apply(ds):
    games = {x["qid"]: x for x in ds["giochi"] if x.get("qid")}
    for f in sorted(OUT.glob("*.json")):
        found = json.loads(f.read_text(encoding="utf-8"))
        game = games[found["qid"]]
        for key in ("protagonisti", "antagonisti", "uccisioni", "personaggi_storici"):
            game[key] = found[key]
        for name, d in found["personaggi"].items():
            ds["personaggi"].setdefault(name, {}).update(d)
    DATASET.write_text(json.dumps(ds, ensure_ascii=False, indent=1), encoding="utf-8")


def main():
    os.environ.setdefault("RESEARCH_MODEL", "openai:gpt-4.1-mini")
    ds = json.loads(DATASET.read_text(encoding="utf-8"))
    if "--applica" in sys.argv:
        return apply(ds)
    agent = create_deep_agent(model=os.environ["RESEARCH_MODEL"], tools=[wikipedia_search, wikipedia_section, wikidata_facts],
                              system_prompt=PROMPT.format(names=", ".join(sorted(ds["personaggi"]))), response_format=GameFacts)
    wanted = set(sys.argv[1:])
    for game in ds["giochi"]:
        if game.get("qid") and (game["qid"] in wanted or (not wanted and not (OUT / f"{game['qid']}.json").exists())):
            research(agent, game)


if __name__ == "__main__":
    main()
