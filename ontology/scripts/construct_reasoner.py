"""
Construct-based reasoner that complements owlrl for inferences outside OWL 2 RL.

**Role**: owlrl materialises OWL 2 RL (someValuesFrom, hasValue, intersectionOf,
subClassOf, inverseOf, SymmetricProperty, TransitiveProperty, propertyChainAxiom).
It does NOT handle: datatype restrictions (minInclusive / maxInclusive), qualified
cardinality, pure complementOf, and certain custom classifications.

This module fills those gaps via SPARQL CONSTRUCT queries applied to an rdflib
graph. Run it **after** owlrl materialisation to get complete inference coverage.

Usage
-----
    uv run python construct_reasoner.py videogames.owl
    uv run python construct_reasoner.py videogames.owl --dry-run
    uv run python construct_reasoner.py videogames.owl --rules R1,R4,R7
    uv run python construct_reasoner.py videogames.owl --max-pairs 5000
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

from rdflib import Graph

# ---------------------------------------------------------------------------
# Logging (same style as enrich_owl.py)
# ---------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Rule:
    """A SPARQL CONSTRUCT inference rule."""

    name: str
    description: str
    query: str
    high_volume: bool = False


# ---------------------------------------------------------------------------
# Rule definitions: one SPARQL CONSTRUCT query per file in ontology/rules/, run
# in file-name order. First line = description; a "# high-volume" line marks the
# pairwise rules that are capped and skipped by the build pipeline.
# ---------------------------------------------------------------------------
RULES_DIR = Path(__file__).resolve().parent.parent / "rules"


def load_rules(directory: Path = RULES_DIR) -> list[Rule]:
    rules = []
    for f in sorted(directory.glob("*.rq")):
        text = f.read_text(encoding="utf-8")
        comments = [ln[1:].strip() for ln in text.splitlines() if ln.startswith("#")]
        rules.append(
            Rule(
                name=f.stem.split("_", 1)[1],
                description=comments[0] if comments else f.stem,
                query=text,
                high_volume=any(c.startswith("high-volume") for c in comments),
            )
        )
    return rules


RULES: list[Rule] = load_rules()

# Set of rule names considered "high volume" (for cap enforcement)
_HIGH_VOLUME_NAMES: set[str] = {r.name for r in RULES if r.high_volume}


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def load_graph(path: Path) -> Graph:
    """Load an RDF graph from *path*, auto-detecting the serialisation format.

    Tries xml, turtle, then nt. Raises ValueError if none can parse the file.
    """
    g = Graph()
    for fmt in ("xml", "turtle", "nt"):
        try:
            g.parse(str(path), format=fmt)
            logger.info(
                "Loaded %d triples from %s (format: %s)", len(g), path.name, fmt
            )
            return g
        except Exception:
            g = Graph()
    raise ValueError(f"Cannot parse {path} — tried xml, turtle, nt")


def apply_rule(g: Graph, rule: Rule, max_pairs: int) -> int:
    """Execute *rule.query* against *g*, add inferred triples, return count added.

    High-volume rules are capped at *max_pairs* new triples; if the cap is hit a
    warning is logged and the rule stops adding further triples.
    """
    try:
        results = g.query(rule.query)
    except Exception as exc:
        logger.error("Rule '%s' failed (query error): %s", rule.name, exc)
        return 0

    added = 0
    for triple in results:
        # (s, p, o) — rdflib returns tuples from CONSTRUCT
        if triple not in g:
            if rule.high_volume and added >= max_pairs:
                logger.warning(
                    "Rule '%s': hit max-pairs cap (%d). Stopping this rule.",
                    rule.name,
                    max_pairs,
                )
                break
            g.add(triple)
            added += 1

    return added


def apply_all(
    g: Graph,
    rules: list[Rule],
    max_pairs: int,
    selected: set[str] | None = None,
) -> dict[str, int]:
    """Apply every rule in *rules* (or only those in *selected*) to *g*.

    Returns a mapping of rule name → triples added.
    """
    counts: dict[str, int] = {}
    for rule in rules:
        if selected is not None and rule.name not in selected:
            continue

        added = apply_rule(g, rule, max_pairs=max_pairs)
        counts[rule.name] = added
        logger.info(
            "  %s: +%d triples%s",
            rule.name,
            added,
            " [capped]" if (rule.high_volume and added >= max_pairs) else "",
        )
    return counts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    known_rules = {r.name for r in RULES}
    parser = argparse.ArgumentParser(
        description="SPARQL CONSTRUCT reasoner — complements owlrl for "
        "inferences outside OWL 2 RL (datatype restrictions, "
        "negation-as-failure, classification chains, inverse completions)."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to input .owl file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: <input>_constructed.owl)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print counts without writing the output file",
    )
    parser.add_argument(
        "--rules",
        type=str,
        default=None,
        help="Comma-separated rule names to apply (default: all). "
        f"Known: {', '.join(sorted(known_rules))}",
    )
    parser.add_argument(
        "--max-pairs",
        type=int,
        default=10_000,
        metavar="N",
        help="Max triples per high-volume rule (default: 10000)",
    )
    args = parser.parse_args(argv)
    return args


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    # Validate input
    if not args.input.exists():
        logger.error("Input file not found: %s", args.input)
        sys.exit(1)

    # Resolve selected rule names
    selected: set[str] | None = None
    if args.rules:
        selected = {n.strip() for n in args.rules.split(",")}
        unknown = selected - {r.name for r in RULES}
        if unknown:
            logger.error("Unknown rule names: %s", ", ".join(sorted(unknown)))
            sys.exit(1)

    # Determine output path
    output: Path
    if args.output:
        output = args.output
    else:
        stem = args.input.stem
        suffix = args.input.suffix  # e.g. .owl
        output = args.input.with_name(f"{stem}_constructed{suffix}")

    # Load
    g = load_graph(args.input)

    # Apply
    if selected:
        logger.info(
            "Applying %d selected rule(s): %s",
            len(selected),
            ", ".join(sorted(selected)),
        )
    else:
        logger.info("Applying all %d rule(s)", len(RULES))

    counts = apply_all(g, RULES, max_pairs=args.max_pairs, selected=selected)
    total_new = sum(counts.values())

    # Report
    logger.info("─" * 50)
    logger.info("Total new triples: %d", total_new)

    if total_new == 0:
        logger.info("No new triples inferred.")

    if args.dry_run:
        logger.info("Dry-run: output NOT written.")
    else:
        g.serialize(str(output), format="xml")
        logger.info("Output written to %s (%d triples)", output, len(g))


if __name__ == "__main__":
    main()
