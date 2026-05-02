"""
Remove games from 2010-2014 and their associated triples from the pruned OWL.
Also removes orphaned entities (developers, publishers, etc.) that are no longer
connected to any remaining game.
"""

from pathlib import Path

from rdflib import RDF, XSD, Graph, Literal, Namespace, URIRef

VG = Namespace("http://www.videogame-ontology.org/ontology#")

INPUT = Path(__file__).parent / "videogames_pruned.owl"
OUTPUT = Path(__file__).parent / "videogames_pruned_2015.owl"

# Classes whose instances should be removed if orphaned
ENTITY_CLASSES = {
    VG.Developer,
    VG.Publisher,
    VG.Genre,
    VG.Platform,
    VG.Character,
    VG.Franchise,
    VG.Award,
    VG.GameEngine,
}


def main():
    g = Graph()
    print(f"Loading {INPUT}...")
    g.parse(str(INPUT))
    initial = len(g)
    print(f"Loaded: {initial:,} triples")

    # Step 1: Find all VideoGame instances with releaseDate in 2010-2014
    print("\nFinding games from 2010-2014...")
    games_to_remove = set()

    for game, _, date_literal in g.triples((None, VG.releaseDate, None)):
        try:
            year = int(str(date_literal)[:4])
            if 2010 <= year <= 2014:
                games_to_remove.add(game)
        except (ValueError, IndexError):
            continue

    print(f"  Found {len(games_to_remove):,} games to remove (2010-2014)")

    # Step 2: Remove all triples where game is subject or object
    print("Removing game triples...")
    removed = 0
    for game in games_to_remove:
        # Triples where game is subject
        for t in list(g.triples((game, None, None))):
            g.remove(t)
            removed += 1
        # Triples where game is object (inverse properties like developerOf, publisherOf, etc.)
        for t in list(g.triples((None, None, game))):
            g.remove(t)
            removed += 1

    print(f"  Removed {removed:,} triples from games")

    # Step 3: Find remaining games (to check for orphans)
    print("\nFinding remaining games...")
    remaining_games = set()
    for game, _, _ in g.triples((None, RDF.type, VG.VideoGame)):
        remaining_games.add(game)
    print(f"  {len(remaining_games):,} games remaining")

    # Step 4: Remove orphaned entities
    # An entity is orphaned if no remaining game references it
    print("Finding orphaned entities...")
    orphan_removed = 0

    for cls in ENTITY_CLASSES:
        cls_name = str(cls).split("#")[-1]
        instances = set(s for s, _, _ in g.triples((None, RDF.type, cls)))
        orphans = set()

        for instance in instances:
            # Check if any triple references this instance (as object from a game)
            referenced = False
            for s, p, o in g.triples((None, None, instance)):
                if s in remaining_games:
                    referenced = True
                    break
            if not referenced:
                # Also check if the instance references any remaining game (inverse props)
                for s, p, o in g.triples((instance, None, None)):
                    if o in remaining_games:
                        referenced = True
                        break
            if not referenced:
                orphans.add(instance)

        # Remove orphan triples
        for orphan in orphans:
            for t in list(g.triples((orphan, None, None))):
                g.remove(t)
                orphan_removed += 1
            for t in list(g.triples((None, None, orphan))):
                g.remove(t)
                orphan_removed += 1

        if orphans:
            print(f"  {cls_name}: {len(orphans):,} orphaned (removed)")

    print(f"\n  Total orphan triples removed: {orphan_removed:,}")

    final = len(g)
    print(f"\nSummary:")
    print(f"  Initial: {initial:,} triples")
    print(f"  Game triples removed: {removed:,}")
    print(f"  Orphan triples removed: {orphan_removed:,}")
    print(f"  Total removed: {initial - final:,}")
    print(f"  Final: {final:,} triples")

    print(f"\nSaving to {OUTPUT}...")
    g.serialize(str(OUTPUT), format="xml")
    print("Done.")


if __name__ == "__main__":
    main()
