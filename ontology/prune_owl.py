"""
Prune the OWL file by removing predicates that are not used in queries.
Removes: owl:sameAs, vg:gameDescription, vg:officialWebsite
"""

from pathlib import Path

from rdflib import OWL, Graph, Namespace

VG = Namespace("http://www.videogame-ontology.org/ontology#")

REMOVE_PREDICATES = {
    OWL.sameAs,
    VG.gameDescription,
    VG.officialWebsite,
}

INPUT = Path(__file__).parent / "videogames_wikidata.owl"
OUTPUT = Path(__file__).parent / "videogames_pruned.owl"


def main():
    g = Graph()
    print(f"Loading {INPUT}...")
    g.parse(str(INPUT))
    print(f"Loaded: {len(g):,} triples")

    removed = 0
    for pred in REMOVE_PREDICATES:
        triples = list(g.triples((None, pred, None)))
        removed += len(triples)
        for t in triples:
            g.remove(t)
        print(
            f"  Removed {len(triples):,} triples with predicate {pred.split('#')[-1] if '#' in pred else pred.split('/')[-1]}"
        )

    print(f"\nTotal removed: {removed:,}")
    print(f"Remaining: {len(g):,} triples")
    print(f"Saving to {OUTPUT}...")
    g.serialize(str(OUTPUT), format="xml")
    print("Done.")


if __name__ == "__main__":
    main()
