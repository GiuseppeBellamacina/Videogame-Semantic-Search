"""Scarica da Wikidata i dati strutturati dei giochi di fonti/dataset.json e li confronta con il dataset.

    uv run python protege/fetch_wikidata.py            # scarica (con cache) e mostra le differenze
    uv run python protege/fetch_wikidata.py Q17452     # un solo gioco

Una sola query per tutti i giochi; le risposte sono salvate in fonti/wikidata/<qid>.json, così la generazione dei dati non richiede la rete.
"""

import json
import sys
import time
from pathlib import Path
from urllib.error import HTTPError

from SPARQLWrapper import JSON, SPARQLWrapper

HERE = Path(__file__).resolve().parent
CACHE = HERE / "fonti" / "wikidata"
ENDPOINT = "https://query.wikidata.org/sparql"
PROPERTIES = {
    "data": "P577",
    "sviluppatore": "P178",
    "editore": "P123",
    "piattaforme": "P400",
    "registi": "P57",
    "motore": "P408",
    "pegi": "P908",
    "seguito_di": "P155",
    "serie": "P179",
    "premi": "P166",
    "basato_su": "P144",
}
QUERY = """
SELECT ?gioco ?campo ?valore ?valoreLabel WHERE {
  VALUES ?gioco { %s }
  { VALUES (?campo ?p) { %s }
    ?gioco ?p ?valore . }
  UNION
  { BIND("metacritic" AS ?campo)
    ?gioco p:P444 [ ps:P444 ?valore ; pq:P447 wd:Q150248 ] . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en,mul". }
}"""


def query(qids):
    pairs = " ".join(f'("{k}" wdt:{p})' for k, p in PROPERTIES.items())
    sparql = SPARQLWrapper(ENDPOINT, agent="videogame-ontology-course-project/1.0")
    sparql.setQuery(QUERY % (" ".join("wd:" + q for q in qids), pairs))
    sparql.setReturnFormat(JSON)
    for _ in range(5):
        try:
            return sparql.query().convert()["results"]["bindings"]
        except HTTPError as e:
            if e.code != 429:
                raise
            time.sleep(65)  # il servizio pubblico limita le richieste
    raise RuntimeError("Wikidata non risponde")


def fetch(qids):
    missing = [q for q in qids if not (CACHE / f"{q}.json").exists()]
    if missing:
        out = {q: {} for q in missing}
        for r in query(missing):
            qid = r["gioco"]["value"].rsplit("/", 1)[1]
            values = out[qid].setdefault(r["campo"]["value"], [])
            value = r.get("valoreLabel", r["valore"])["value"]
            if value not in values:
                values.append(value)
        CACHE.mkdir(parents=True, exist_ok=True)
        for qid, data in out.items():
            (CACHE / f"{qid}.json").write_text(
                json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True),
                encoding="utf-8",
            )
    return {
        q: json.loads((CACHE / f"{q}.json").read_text(encoding="utf-8")) for q in qids
    }


def differences(game, wd):
    diffs = []
    if "pegi" in wd and game.get("pegi") and f"PEGI {game['pegi']}" not in wd["pegi"]:
        diffs.append(f"pegi: dataset {game['pegi']}, Wikidata {wd['pegi']}")
    if (
        "data" in wd
        and game.get("data")
        and not any(d.startswith(game["data"]) for d in wd["data"])
    ):
        diffs.append(f"data: dataset {game['data']}, Wikidata {sorted(wd['data'])[:2]}")
    for field in ("sviluppatore", "editore", "registi"):
        missing = [v for v in game.get(field, []) if v not in wd.get(field, [])]
        if missing and field in wd:
            diffs.append(f"{field}: {missing} non su Wikidata ({wd[field]})")
    return diffs


def main():
    ds = json.loads((HERE / "fonti" / "dataset.json").read_text(encoding="utf-8"))
    games = [
        x
        for x in ds["giochi"]
        if x.get("qid") and (not sys.argv[1:] or x["qid"] in sys.argv[1:])
    ]
    wd = fetch([x["qid"] for x in games])
    for game in games:
        for d in differences(game, wd[game["qid"]]):
            print(f"{game['titolo']}: {d}")


if __name__ == "__main__":
    main()
