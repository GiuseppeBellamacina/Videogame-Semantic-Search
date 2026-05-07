"""
Enrich existing OWL files with advanced ontology constructs:

  - AwardWinningGame   (defined class via equivalentClass + someValuesFrom)
  - FranchiseGame      (defined class via equivalentClass + someValuesFrom)
  - sharedFranchiseWith  (property chain: belongsTo ∘ includes)
  - sharesDeveloperWith  (property chain: developedBy ∘ developerOf)
  - sharesPublisherWith  (property chain: publishedBy ∘ publisherOf)

These axioms enable OWL-RL reasoning to automatically infer:
  - which games have won awards
  - which games belong to a series
  - which games share a franchise, studio, or publisher

Usage
-----
    python enrich_owl.py                           # enriches all .owl files in this directory
    python enrich_owl.py videogames_pruned.owl     # enriches a single file
    python enrich_owl.py --reason videogames_pruned.owl
        # enriches AND materialises inferred triples via targeted reasoning
        # (needed to make AwardWinningGame / sharedFranchiseWith etc. queryable)
        # Much faster than full OWL-RL: only applies the 5 rules our axioms define.
        # Use --max-group N to cap pairwise links per franchise/dev/pub (default 50).
"""

import logging
import sys
from collections import defaultdict
from pathlib import Path

from rdflib import OWL, RDF, RDFS, Graph, Namespace, URIRef
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

VG = Namespace("http://www.videogame-ontology.org/ontology#")
OWL_NS = OWL


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _add_axioms(g: Graph) -> int:
    """
    Add the enrichment axioms to *g* if they are not already present.
    Returns the number of new triples added.
    """
    before = len(g)

    # ── 1. Defined class: AwardWinningGame ──────────────────────────────────
    awg = VG.AwardWinningGame
    if (awg, RDF.type, OWL.Class) not in g:
        g.add((awg, RDF.type, OWL.Class))
        g.add((awg, RDFS.subClassOf, VG.VideoGame))
        g.add((awg, RDFS.label, _lit("Award Winning Game")))
        g.add(
            (
                awg,
                RDFS.comment,
                _lit(
                    "A video game that has received at least one award. "
                    "Instances are inferred by OWL-RL reasoning."
                ),
            )
        )
        # equivalentClass = VideoGame ∩ (wonAward some Award)
        restriction = _blank(
            g,
            [
                (OWL.onProperty, VG.wonAward),
                (OWL.someValuesFrom, VG.Award),
            ],
        )
        intersection = _intersection(g, [VG.VideoGame, restriction])
        equiv_class = _blank(g, [(OWL.intersectionOf, intersection)])
        g.add((awg, OWL.equivalentClass, equiv_class))
        logger.info("  + AwardWinningGame class added")

    # ── 2. Defined class: FranchiseGame ─────────────────────────────────────
    fg = VG.FranchiseGame
    if (fg, RDF.type, OWL.Class) not in g:
        g.add((fg, RDF.type, OWL.Class))
        g.add((fg, RDFS.subClassOf, VG.VideoGame))
        g.add((fg, RDFS.label, _lit("Franchise Game")))
        g.add(
            (
                fg,
                RDFS.comment,
                _lit(
                    "A video game that is part of a franchise or series. "
                    "Instances are inferred by OWL-RL reasoning."
                ),
            )
        )
        restriction = _blank(
            g,
            [
                (OWL.onProperty, VG.belongsTo),
                (OWL.someValuesFrom, VG.Franchise),
            ],
        )
        intersection = _intersection(g, [VG.VideoGame, restriction])
        equiv_class = _blank(g, [(OWL.intersectionOf, intersection)])
        g.add((fg, OWL.equivalentClass, equiv_class))
        logger.info("  + FranchiseGame class added")

    # ── 3. Property: sharedFranchiseWith ────────────────────────────────────
    sfw = VG.sharedFranchiseWith
    if (sfw, RDF.type, OWL.ObjectProperty) not in g:
        g.add((sfw, RDF.type, OWL.ObjectProperty))
        g.add((sfw, RDF.type, OWL.SymmetricProperty))
        g.add((sfw, RDFS.domain, VG.VideoGame))
        g.add((sfw, RDFS.range, VG.VideoGame))
        g.add((sfw, RDFS.label, _lit("shared franchise with")))
        g.add(
            (
                sfw,
                RDFS.comment,
                _lit(
                    "Links two games that belong to the same franchise/series. "
                    "Inferred via property chain: belongsTo ∘ includes."
                ),
            )
        )
        chain = _rdf_list(g, [VG.belongsTo, VG.includes])
        g.add((sfw, OWL.propertyChainAxiom, chain))
        logger.info("  + sharedFranchiseWith property added")

    # ── 4. Property: sharesDeveloperWith ────────────────────────────────────
    sdw = VG.sharesDeveloperWith
    if (sdw, RDF.type, OWL.ObjectProperty) not in g:
        g.add((sdw, RDF.type, OWL.ObjectProperty))
        g.add((sdw, RDF.type, OWL.SymmetricProperty))
        g.add((sdw, RDFS.domain, VG.VideoGame))
        g.add((sdw, RDFS.range, VG.VideoGame))
        g.add((sdw, RDFS.label, _lit("shares developer with")))
        g.add(
            (
                sdw,
                RDFS.comment,
                _lit(
                    "Links two games developed by the same studio. "
                    "Inferred via property chain: developedBy ∘ developerOf."
                ),
            )
        )
        chain = _rdf_list(g, [VG.developedBy, VG.developerOf])
        g.add((sdw, OWL.propertyChainAxiom, chain))
        logger.info("  + sharesDeveloperWith property added")

    # ── 5. Property: sharesPublisherWith ────────────────────────────────────
    spw = VG.sharesPublisherWith
    if (spw, RDF.type, OWL.ObjectProperty) not in g:
        g.add((spw, RDF.type, OWL.ObjectProperty))
        g.add((spw, RDF.type, OWL.SymmetricProperty))
        g.add((spw, RDFS.domain, VG.VideoGame))
        g.add((spw, RDFS.range, VG.VideoGame))
        g.add((spw, RDFS.label, _lit("shares publisher with")))
        g.add(
            (
                spw,
                RDFS.comment,
                _lit(
                    "Links two games published by the same company. "
                    "Inferred via property chain: publishedBy ∘ publisherOf."
                ),
            )
        )
        chain = _rdf_list(g, [VG.publishedBy, VG.publisherOf])
        g.add((spw, OWL.propertyChainAxiom, chain))
        logger.info("  + sharesPublisherWith property added")

    return len(g) - before


# ---------------------------------------------------------------------------
# Targeted materialiser (replaces full OWL-RL)
# ---------------------------------------------------------------------------


def _materialise(g: Graph, max_group: int = 50) -> int:
    """
    Apply only the 5 inference rules our axioms define, with tqdm progress bars.

    Rules:
      1. AwardWinningGame  ← game wonAward _:x
      2. FranchiseGame     ← game belongsTo _:f
      3. sharedFranchiseWith (chain belongsTo ∘ includes)   — symmetric
      4. sharesDeveloperWith (chain developedBy ∘ developerOf) — symmetric
      5. sharesPublisherWith (chain publishedBy ∘ publisherOf) — symmetric

    Groups larger than *max_group* games (same franchise/dev/pub) are skipped
    for the pairwise rules to avoid combinatorial explosion; a warning is logged.
    """
    added = 0

    # ── 1 & 2: class membership ──────────────────────────────────────────────
    award_games: set[URIRef] = set()
    franchise_games: set[URIRef] = set()

    for s, _, _o in g.triples((None, VG.wonAward, None)):
        if isinstance(s, URIRef):
            award_games.add(s)
    for s, _, _o in g.triples((None, VG.belongsTo, None)):
        if isinstance(s, URIRef):
            franchise_games.add(s)

    total_class = len(award_games) + len(franchise_games)
    with tqdm(
        total=total_class,
        desc="  [1/3] Class membership",
        unit="game",
        ncols=80,
        leave=True,
    ) as pbar:
        for game in award_games:
            t = (game, RDF.type, VG.AwardWinningGame)
            if t not in g:
                g.add(t)
                added += 1
            pbar.update(1)
        for game in franchise_games:
            t = (game, RDF.type, VG.FranchiseGame)
            if t not in g:
                g.add(t)
                added += 1
            pbar.update(1)

    # ── helper: build group map and generate symmetric pairs ─────────────────
    def _pairwise(
        prop_fwd: URIRef,
        prop_chain_end: URIRef,
        result_prop: URIRef,
        label: str,
        step: str,
    ) -> int:
        """
        Build groups: entity → set[game] via prop_fwd.
        Then emit (g1, result_prop, g2) for every distinct pair in each group.
        """
        groups: dict[URIRef, set[URIRef]] = defaultdict(set)
        for game, _, entity in g.triples((None, prop_fwd, None)):
            if isinstance(game, URIRef) and isinstance(entity, URIRef):
                groups[entity].add(game)

        # Count pairs up-front for progress bar
        skipped_groups = 0
        pairs: list[tuple[URIRef, URIRef]] = []
        for entity, games in groups.items():
            if len(games) > max_group:
                skipped_groups += 1
                continue
            glist = list(games)
            for i, g1 in enumerate(glist):
                for g2 in glist[i + 1 :]:
                    pairs.append((g1, g2))

        if skipped_groups:
            logger.warning(
                f"  {label}: skipped {skipped_groups} groups with >{max_group} games "
                f"(use --max-group N to raise the limit)"
            )

        new = 0
        with tqdm(
            pairs, desc=f"  [{step}] {label}", unit="pair", ncols=80, leave=True
        ) as pbar:
            for g1, g2 in pbar:
                for a, b in ((g1, g2), (g2, g1)):  # materialise both directions
                    t = (a, result_prop, b)
                    if t not in g:
                        g.add(t)
                        new += 1
                pbar.set_postfix(new=new)
        return new

    # ── 3: sharedFranchiseWith ───────────────────────────────────────────────
    added += _pairwise(
        VG.belongsTo,
        VG.includes,
        VG.sharedFranchiseWith,
        "sharedFranchiseWith",
        "2/3",
    )

    # ── 4 & 5: sharesDeveloperWith / sharesPublisherWith ─────────────────────
    added += _pairwise(
        VG.developedBy,
        VG.developerOf,
        VG.sharesDeveloperWith,
        "sharesDeveloperWith",
        "3a/3",
    )
    added += _pairwise(
        VG.publishedBy,
        VG.publisherOf,
        VG.sharesPublisherWith,
        "sharesPublisherWith",
        "3b/3",
    )

    return added


# ---------------------------------------------------------------------------
# RDF helpers
# ---------------------------------------------------------------------------

from rdflib import BNode, Literal
from rdflib.namespace import XSD


def _lit(s: str) -> Literal:
    return Literal(s, datatype=XSD.string)


def _blank(g: Graph, props: list[tuple]) -> BNode:
    """Create a blank node with the given (predicate, object) pairs."""
    bn = BNode()
    for p, o in props:
        g.add((bn, p, o))
    return bn


def _rdf_list(g: Graph, items: list[URIRef]) -> BNode:
    """Build an rdf:List and return its head blank node."""
    if not items:
        return RDF.nil  # type: ignore[return-value]
    head = BNode()
    current = head
    for i, item in enumerate(items):
        g.add((current, RDF.first, item))
        if i < len(items) - 1:
            nxt = BNode()
            g.add((current, RDF.rest, nxt))
            current = nxt
        else:
            g.add((current, RDF.rest, RDF.nil))
    return head


def _intersection(g: Graph, items: list) -> BNode:
    """Build an owl:intersectionOf blank node containing an rdf:List."""
    lst = _rdf_list(g, items)
    bn = BNode()
    g.add((bn, OWL.intersectionOf, lst))
    return bn


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def enrich_file(path: Path, run_reasoning: bool = False, max_group: int = 50) -> None:
    logger.info(f"Processing: {path.name}")
    g = Graph()
    g.bind("vg", VG)
    g.bind("owl", OWL)
    g.parse(str(path), format="xml")
    before = len(g)
    logger.info(f"  Loaded {before} triples")

    added = _add_axioms(g)

    if added == 0:
        logger.info("  Axioms already up to date")
    else:
        logger.info(f"  Added {added} new axiom triples")

    if run_reasoning:
        if path.name == "videogames.owl":
            logger.info("  Skipping reasoning on schema-only file (videogames.owl)")
        else:
            logger.info("  Running targeted materialisation...")
            inferred = _materialise(g, max_group=max_group)
            logger.info(
                f"  Materialisation done: +{inferred} new triples → {len(g)} total"
            )

    if added == 0 and not run_reasoning:
        logger.info("  Nothing changed — skipping save")
        return

    g.serialize(str(path), format="xml")
    logger.info(f"  Saved {len(g)} triples → {path.name}")


def main() -> None:
    import argparse

    ontology_dir = Path(__file__).parent

    parser = argparse.ArgumentParser(
        description="Enrich OWL files with advanced ontology constructs."
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="OWL files to process (default: all *.owl in this directory)",
    )
    parser.add_argument(
        "--reason",
        action="store_true",
        help="Materialise inferred triples after enriching",
    )
    parser.add_argument(
        "--max-group",
        type=int,
        default=50,
        metavar="N",
        help="Max group size for pairwise chain materialisation (default: 50)",
    )
    ns = parser.parse_args()

    if ns.files:
        targets = [ontology_dir / f for f in ns.files]
    else:
        targets = sorted(ontology_dir.glob("*.owl"))

    if not targets:
        logger.error("No OWL files found.")
        sys.exit(1)

    for target in targets:
        if not target.exists():
            logger.warning(f"File not found: {target}")
            continue
        try:
            enrich_file(target, run_reasoning=ns.reason, max_group=ns.max_group)
        except Exception as e:
            logger.error(f"Failed to enrich {target.name}: {e}")

    logger.info("Done.")


if __name__ == "__main__":
    main()
