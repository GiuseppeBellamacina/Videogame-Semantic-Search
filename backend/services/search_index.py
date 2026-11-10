"""
In-memory label index for autosuggest. Built once when the ontology is loaded:
one entry per named entity (games, developers, genres...), searched by
prefix / word-prefix / substring with a simple ranking.
"""

import logging

import pyoxigraph as ox

from backend.config import ONTOLOGY_NS

logger = logging.getLogger(__name__)

# entity type -> property holding its name
NAME_PROPS = {
    "VideoGame": "gameName",
    "Developer": "developerName",
    "Publisher": "publisherName",
    "Genre": "genreName",
    "Platform": "platformName",
    "Franchise": "franchiseName",
    "Character": "characterName",
    "Award": "awardName",
    "GameEngine": "engineName",
}
RDFS_LABEL = "http://www.w3.org/2000/01/rdf-schema#label"
RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"

# type -> [(lowercase label, label, uri)]
_index: dict[str, list[tuple[str, str, str]]] = {}


def build(store: ox.Store) -> None:
    _index.clear()
    for etype, prop in NAME_PROPS.items():
        entries = {
            (q.object.value.lower(), q.object.value, q.subject.value)
            for q in store.quads_for_pattern(None, ox.NamedNode(ONTOLOGY_NS + prop), None)
            if isinstance(q.subject, ox.NamedNode)
        }
        _index[etype] = sorted(entries)
    # GameMode individuals are named by rdfs:label
    modes = ox.NamedNode(ONTOLOGY_NS + "GameMode")
    entries = set()
    for q in store.quads_for_pattern(None, ox.NamedNode(RDF_TYPE), modes):
        for lq in store.quads_for_pattern(q.subject, ox.NamedNode(RDFS_LABEL), None):
            entries.add((lq.object.value.lower(), lq.object.value, q.subject.value))
    _index["GameMode"] = sorted(entries)
    logger.info(
        "Search index: " + ", ".join(f"{t}={len(v)}" for t, v in _index.items())
    )


def _rank(label_low: str, q: str) -> int | None:
    """0 = prefix, 1 = word prefix, 2 = substring, None = no match."""
    if label_low.startswith(q):
        return 0
    pos = label_low.find(q)
    if pos < 0:
        return None
    return 1 if label_low[pos - 1] in " -:(" else 2


def suggest(q: str, types: list[str] | None = None, limit: int = 8) -> list[dict]:
    q = q.strip().lower()
    if len(q) < 2:
        return []
    hits: list[tuple[int, int, str, str, str]] = []
    for etype in types or list(_index):
        for low, label, uri in _index.get(etype, []):
            r = _rank(low, q)
            if r is not None:
                hits.append((r, len(low), label, uri, etype))
    hits.sort()
    return [
        {"label": label, "uri": uri, "type": etype}
        for _, _, label, uri, etype in hits[:limit]
    ]


def suggest_text(text: str, types: list[str] | None = None, limit: int = 8) -> dict:
    """Suggest completions for the trailing words of free text: tries the last
    4, 3, 2, 1 words and returns the longest suffix that has matches."""
    words = text.split()
    for n in range(min(4, len(words)), 0, -1):
        suffix = " ".join(words[-n:])
        if n == 1 and len(suffix) < 3:
            continue  # avoid noise from short stop words ("di", "su")
        hits = suggest(suffix, types, limit)
        if hits:
            return {"match": suffix, "suggestions": hits}
    return {"match": "", "suggestions": []}
