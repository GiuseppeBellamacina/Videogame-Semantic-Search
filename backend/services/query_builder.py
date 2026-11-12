"""
Assisted query builder: turns a list of structured filters on VideoGame into a
SPARQL SELECT. Everything user-supplied is validated against a whitelist or
escaped, so the generated query cannot be altered by the input.
"""

import re

from backend.config import ONTOLOGY_NS

PREFIXES = (
    f"PREFIX vg: <{ONTOLOGY_NS}>\n"
    "PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"
    "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
    "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>\n"
)

# field -> definition. kind: entity | number | year | text | class
FIELDS: dict[str, dict] = {
    "developedBy": {
        "label": "Developer",
        "kind": "entity",
        "target": "Developer",
        "name": "developerName",
    },
    "publishedBy": {
        "label": "Publisher",
        "kind": "entity",
        "target": "Publisher",
        "name": "publisherName",
    },
    "hasGenre": {
        "label": "Genre",
        "kind": "entity",
        "target": "Genre",
        "name": "genreName",
    },
    "availableOn": {
        "label": "Platform",
        "kind": "entity",
        "target": "Platform",
        "name": "platformName",
    },
    "belongsTo": {
        "label": "Franchise",
        "kind": "entity",
        "target": "Franchise",
        "name": "franchiseName",
    },
    "hasCharacter": {
        "label": "Character",
        "kind": "entity",
        "target": "Character",
        "name": "characterName",
    },
    "wonAward": {
        "label": "Award",
        "kind": "entity",
        "target": "Award",
        "name": "awardName",
    },
    "madeWith": {
        "label": "Game engine",
        "kind": "entity",
        "target": "GameEngine",
        "name": "engineName",
    },
    "hasGameMode": {
        "label": "Game mode",
        "kind": "entity",
        "target": "GameMode",
        "name": None,
    },
    "metacriticScore": {"label": "Metacritic score", "kind": "number"},
    "releaseYear": {"label": "Release year", "kind": "year"},
    "gameName": {"label": "Title", "kind": "text"},
    "countryOfOrigin": {"label": "Country of origin", "kind": "text"},
    "isA": {
        "label": "Category",
        "kind": "class",
        "options": [
            "AwardWinningGame",
            "FranchiseGame",
            "SinglePlayerGame",
            "MultiplayerGame",
            "CoopGame",
            "PCGame",
            "ConsoleGame",
            "MobileGame",
            "NintendoGame",
            "PlayStationGame",
            "XboxGame",
            "HighlyRatedGame",
            "RecentGame",
            "SequelGame",
            "StandaloneGame",
            "MultiConsoleGame",
            "NintendoPublishedGame",
        ],
    },
}
OPS = {
    "entity": ["is", "is_not"],
    "number": ["=", ">=", "<=", ">", "<"],
    "year": ["=", ">=", "<="],
    "text": ["contains", "equals"],
    "class": ["is", "is_not"],
}
NUM_OPS = {"=", ">=", "<=", ">", "<"}
ORDERS = {
    "name": "?gameName",
    "score_desc": "DESC(?score)",
    "date_desc": "DESC(?releaseDate)",
    "date_asc": "?releaseDate",
}
_URI_RE = re.compile(
    r"^" + re.escape(ONTOLOGY_NS.rsplit("/", 1)[0]) + r"/[^\s<>\"{}|\\^`]+$"
)


class BuilderError(ValueError):
    pass


def schema() -> dict:
    return {
        "fields": [{"field": k, **v, "ops": OPS[v["kind"]]} for k, v in FIELDS.items()],
        "orders": list(ORDERS),
    }


def _lit(value: str) -> str:
    esc = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", " ")
        .replace("\r", " ")
    )
    return f'"{esc}"'


# relations shown when the builder returns a graph
GRAPH_RELATIONS = [
    "developedBy",
    "publishedBy",
    "hasGenre",
    "availableOn",
    "belongsTo",
    "madeWith",
    "hasGameMode",
    "hasCharacter",
    "wonAward",
    "sequelOf",
]


def build(
    filters: list[dict], order_by: str = "name", limit: int = 50, output: str = "table"
) -> str:
    if output not in ("table", "graph", "count"):
        raise BuilderError(f"Unknown output '{output}'")
    if order_by not in ORDERS:
        raise BuilderError(f"Unknown order '{order_by}'")
    limit = max(1, min(int(limit), 500))

    body: list[str] = [
        "?game rdf:type vg:VideoGame .",
        "?game vg:gameName ?gameName .",
        "OPTIONAL { ?game vg:releaseDate ?releaseDate }",
        "OPTIONAL { ?game vg:metacriticScore ?score }",
    ]
    select = ["?game", "?gameName", "?releaseDate", "?score"]

    for i, f in enumerate(filters):
        field, op, value = f.get("field"), f.get("op"), f.get("value")
        d = FIELDS.get(field or "")
        if d is None or value in (None, ""):
            raise BuilderError(f"Invalid filter: {f}")
        kind = d["kind"]
        if op not in OPS[kind]:
            raise BuilderError(f"Operator '{op}' not valid for {field}")
        v, n = f"?f{i}", f"?f{i}Name"

        if kind == "entity":
            value = str(value)
            if _URI_RE.match(value):
                match = f"?game vg:{field} <{value}> ."
                link = None
            else:
                # free text: match the entity by name
                name_pat = (
                    f"{v} rdfs:label {n}"
                    if d["name"] is None
                    else f"{v} vg:{d['name']} {n}"
                )
                match = (
                    f"?game vg:{field} {v} . {name_pat} . "
                    f"FILTER(CONTAINS(LCASE(STR({n})), {_lit(value.lower())}))"
                )
                link = (v, n)
            if op == "is":
                body.append(match)
                if link:
                    select += list(link)
            else:
                body.append(f"FILTER NOT EXISTS {{ {match} }}")
        elif kind == "number":
            body.append(f"?game vg:metacriticScore {v} . FILTER({v} {op} {int(value)})")
        elif kind == "year":
            body.append(
                f"?game vg:releaseDate {v} . FILTER(YEAR({v}) {op} {int(value)})"
            )
        elif kind == "text":
            expr = (
                f"CONTAINS(LCASE(STR({v})), {_lit(str(value).lower())})"
                if op == "contains"
                else f"LCASE(STR({v})) = {_lit(str(value).lower())}"
            )
            body.append(f"?game vg:{field} {v} . FILTER({expr})")
        elif kind == "class":
            if value not in d["options"]:
                raise BuilderError(f"Unknown category '{value}'")
            pat = f"?game rdf:type vg:{value} ."
            body.append(pat if op == "is" else f"FILTER NOT EXISTS {{ {pat} }}")

    where = "\n  ".join(body)
    if output == "count":
        return f"{PREFIXES}SELECT (COUNT(DISTINCT ?game) AS ?n) WHERE {{\n  {where}\n}}"
    select_query = (
        f"SELECT DISTINCT {' '.join(select)} WHERE {{\n  {where}\n}}\n"
        f"ORDER BY {ORDERS[order_by]}\nLIMIT {limit}"
    )
    if output == "table":
        return PREFIXES + select_query
    rels = ", ".join(f"vg:{r}" for r in GRAPH_RELATIONS)
    return (
        f"{PREFIXES}CONSTRUCT {{ ?game ?p ?o }}\nWHERE {{\n"
        f"  {{ {select_query.replace(chr(10), chr(10) + '    ')} }}\n"
        f"  ?game ?p ?o .\n  FILTER(?p IN ({rels}))\n}}"
    )
