"""Write videogames.ttl, the readable Turtle copy of videogames.owl, with the
subjects in the same order as in the .owl file (rdflib would otherwise sort them
alphabetically and put the defined classes first)."""

import re
from pathlib import Path

from rdflib import BNode, Graph
from rdflib.plugins.serializers.turtle import TurtleSerializer

HERE = Path(__file__).parent
BASE = "http://www.videogame-ontology.org/ontology"


def _owl_order(owl: Path) -> dict[str, int]:
    """URI -> position of its first top-level element in the RDF/XML file."""
    order: dict[str, int] = {}
    for m in re.finditer(
        r'^    <[\w:]+ rdf:(?:about|ID)="([^"]+)"',
        owl.read_text(encoding="utf-8"),
        re.M,
    ):
        ref = m.group(1)
        uri = BASE + ref if ref.startswith("#") else ref
        order.setdefault(uri, len(order))
    return order


def write(
    owl: Path = HERE / "videogames.owl", ttl: Path = HERE / "videogames.ttl"
) -> None:
    g = Graph().parse(str(owl))
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
