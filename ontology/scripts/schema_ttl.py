"""Write videogames.ttl, the readable Turtle copy of the schema (videogames.owl and
its modules merged), with the subjects in the same order as in the module files
(rdflib would otherwise sort them alphabetically and put the defined classes first)."""

import re
from pathlib import Path

from rdflib import BNode, Graph
from rdflib.plugins.serializers.turtle import TurtleSerializer

import schema_loader

HERE = Path(__file__).resolve().parent.parent  # ontology/
BASE = "http://www.videogame-ontology.org/ontology"


def _owl_order(owl: Path) -> dict[str, int]:
    """URI -> position of its first top-level element, module after module."""
    order: dict[str, int] = {}
    for f in [owl, *schema_loader.module_files(owl)]:
        for m in re.finditer(
            r'^    <[\w:]+ rdf:(?:about|ID)="([^"]+)"',
            f.read_text(encoding="utf-8"),
            re.M,
        ):
            ref = m.group(1)
            uri = BASE + ref if ref.startswith("#") else ref
            order.setdefault(uri, len(order))
    return order


def write(
    owl: Path = HERE / "videogames.owl", ttl: Path = HERE / "output" / "videogames.ttl"
) -> None:
    ttl.parent.mkdir(parents=True, exist_ok=True)
    g = schema_loader.load_tbox(owl)
    g.bind("vg", BASE + "#")
    pos = _owl_order(owl)

    class Ordered(TurtleSerializer):
        def orderSubjects(self):  # noqa: N802 (rdflib API)
            subjects = super().orderSubjects()
            # blank nodes keep rdflib's order: it prints them after the nodes that use them
            named = [s for s in subjects if not isinstance(s, BNode)]
            named.sort(key=lambda s: (pos.get(str(s), len(pos)), str(s)))
            return named + [s for s in subjects if isinstance(s, BNode)]

    with ttl.open("wb") as f:
        Ordered(g).serialize(f)


if __name__ == "__main__":
    write()
