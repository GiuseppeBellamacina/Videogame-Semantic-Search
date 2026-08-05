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
from dataclasses import dataclass, field
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
# Common SPARQL prefix block
# ---------------------------------------------------------------------------
_PREFIXES = """
PREFIX vg: <http://www.videogame-ontology.org/ontology#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
"""

# ---------------------------------------------------------------------------
# Rule definitions
# ---------------------------------------------------------------------------


def _q(body: str) -> str:
    """Return a CONSTRUCT query with standard prefixes prepended."""
    return _PREFIXES + body


RULES: list[Rule] = [
    # ── R1 : HighlyRatedGame ──────────────────────────────────────────────
    Rule(
        name="classify_highly_rated",
        description="Classify games with metacriticScore >= 85 as HighlyRatedGame",
        query=_q(
            """CONSTRUCT { ?g a vg:HighlyRatedGame . }
WHERE { ?g a vg:VideoGame . ?g vg:metacriticScore ?s . FILTER(?s >= 85) }"""
        ),
    ),
    # ── R2 : RecentGame ───────────────────────────────────────────────────
    Rule(
        name="classify_recent",
        description="Classify games with releaseDate >= 2020-01-01 as RecentGame",
        query=_q(
            """CONSTRUCT { ?g a vg:RecentGame . }
WHERE {
    ?g a vg:VideoGame .
    ?g vg:releaseDate ?d .
    FILTER(?d >= "2020-01-01"^^xsd:date)
}"""
        ),
    ),
    # ── R3 : StandaloneGame ───────────────────────────────────────────────
    Rule(
        name="classify_standalone",
        description="Classify games without any sequelOf link as StandaloneGame",
        query=_q(
            """CONSTRUCT { ?g a vg:StandaloneGame . }
WHERE { ?g a vg:VideoGame . FILTER NOT EXISTS { ?g vg:sequelOf ?any } }"""
        ),
    ),
    # ── R4 : SequelGame ───────────────────────────────────────────────────
    Rule(
        name="classify_sequel",
        description="Classify games that have a sequelOf link as SequelGame",
        query=_q(
            """CONSTRUCT { ?g a vg:SequelGame . }
WHERE { ?g vg:sequelOf ?any . }"""
        ),
    ),
    # ── R5a : PCGame ──────────────────────────────────────────────────────
    Rule(
        name="classify_pc_game",
        description="Classify games available on a PCPlatform as PCGame",
        query=_q(
            """CONSTRUCT { ?g a vg:PCGame . }
WHERE { ?g vg:availableOn ?p . ?p a vg:PCPlatform . }"""
        ),
    ),
    # ── R5b : ConsoleGame ─────────────────────────────────────────────────
    Rule(
        name="classify_console_game",
        description="Classify games available on a ConsolePlatform as ConsoleGame",
        query=_q(
            """CONSTRUCT { ?g a vg:ConsoleGame . }
WHERE { ?g vg:availableOn ?p . ?p a vg:ConsolePlatform . }"""
        ),
    ),
    # ── R5c : MobileGame ──────────────────────────────────────────────────
    Rule(
        name="classify_mobile_game",
        description="Classify games available on a MobilePlatform as MobileGame",
        query=_q(
            """CONSTRUCT { ?g a vg:MobileGame . }
WHERE { ?g vg:availableOn ?p . ?p a vg:MobilePlatform . }"""
        ),
    ),
    # ── R5d : NintendoGame ────────────────────────────────────────────────
    Rule(
        name="classify_nintendo_game",
        description="Classify games available on a NintendoPlatform as NintendoGame",
        query=_q(
            """CONSTRUCT { ?g a vg:NintendoGame . }
WHERE { ?g vg:availableOn ?p . ?p a vg:NintendoPlatform . }"""
        ),
    ),
    # ── R5e : PlayStationGame ─────────────────────────────────────────────
    Rule(
        name="classify_playstation_game",
        description="Classify games on a PlayStationPlatform as PlayStationGame",
        query=_q(
            """CONSTRUCT { ?g a vg:PlayStationGame . }
WHERE { ?g vg:availableOn ?p . ?p a vg:PlayStationPlatform . }"""
        ),
    ),
    # ── R5f : XboxGame ────────────────────────────────────────────────────
    Rule(
        name="classify_xbox_game",
        description="Classify games available on an XboxPlatform as XboxGame",
        query=_q(
            """CONSTRUCT { ?g a vg:XboxGame . }
WHERE { ?g vg:availableOn ?p . ?p a vg:XboxPlatform . }"""
        ),
    ),
    # ── R6a : MultiplayerGame ─────────────────────────────────────────────
    Rule(
        name="classify_multiplayer_game",
        description="Classify games with MultiplayerMode as MultiplayerGame",
        query=_q(
            """CONSTRUCT { ?g a vg:MultiplayerGame . }
WHERE { ?g vg:hasGameMode ?m . ?m a vg:MultiplayerMode . }"""
        ),
    ),
    # ── R6b : SinglePlayerGame ────────────────────────────────────────────
    Rule(
        name="classify_singleplayer_game",
        description="Classify games with SinglePlayerMode as SinglePlayerGame",
        query=_q(
            """CONSTRUCT { ?g a vg:SinglePlayerGame . }
WHERE { ?g vg:hasGameMode ?m . ?m a vg:SinglePlayerMode . }"""
        ),
    ),
    # ── R6c : CoopGame ────────────────────────────────────────────────────
    Rule(
        name="classify_coop_game",
        description="Classify games with CoopMode as CoopGame",
        query=_q(
            """CONSTRUCT { ?g a vg:CoopGame . }
WHERE { ?g vg:hasGameMode ?m . ?m a vg:CoopMode . }"""
        ),
    ),
    # ── R7 : Inverse hasSequel ────────────────────────────────────────────
    Rule(
        name="inverse_has_sequel",
        description="Complete inverse: if A sequelOf B then B hasSequel A",
        query=_q(
            """CONSTRUCT { ?b vg:hasSequel ?a . }
WHERE {
    ?a vg:sequelOf ?b .
    FILTER NOT EXISTS { ?b vg:hasSequel ?a }
}"""
        ),
    ),
    # ── R8 : Inverse awardWonBy ───────────────────────────────────────────
    Rule(
        name="inverse_award_won_by",
        description="Complete inverse: if G wonAward A then A awardWonBy G",
        query=_q(
            """CONSTRUCT { ?a vg:awardWonBy ?g . }
WHERE {
    ?g vg:wonAward ?a .
    FILTER NOT EXISTS { ?a vg:awardWonBy ?g }
}"""
        ),
    ),
    # ── R9a : Inverse genreOf ─────────────────────────────────────────────
    Rule(
        name="inverse_genre_of",
        description="Complete inverse: if G hasGenre Gen then Gen genreOf G",
        query=_q(
            """CONSTRUCT { ?genre vg:genreOf ?g . }
WHERE {
    ?g vg:hasGenre ?genre .
    FILTER NOT EXISTS { ?genre vg:genreOf ?g }
}"""
        ),
    ),
    # ── R9b : Inverse platformFor ─────────────────────────────────────────
    Rule(
        name="inverse_platform_for",
        description="Complete inverse: if G availableOn P then P platformFor G",
        query=_q(
            """CONSTRUCT { ?p vg:platformFor ?g . }
WHERE {
    ?g vg:availableOn ?p .
    FILTER NOT EXISTS { ?p vg:platformFor ?g }
}"""
        ),
    ),
    # ── R9c : Inverse engineUsedIn ────────────────────────────────────────
    Rule(
        name="inverse_engine_used_in",
        description="Complete inverse: if G madeWith E then E engineUsedIn G",
        query=_q(
            """CONSTRUCT { ?e vg:engineUsedIn ?g . }
WHERE {
    ?g vg:madeWith ?e .
    FILTER NOT EXISTS { ?e vg:engineUsedIn ?g }
}"""
        ),
    ),
    # ── R9d : Inverse modeInGame ──────────────────────────────────────────
    Rule(
        name="inverse_mode_in_game",
        description="Complete inverse: if G hasGameMode M then M modeInGame G",
        query=_q(
            """CONSTRUCT { ?m vg:modeInGame ?g . }
WHERE {
    ?g vg:hasGameMode ?m .
    FILTER NOT EXISTS { ?m vg:modeInGame ?g }
}"""
        ),
    ),
    # ── R10 : sharedGenreWith ─────────────────────────────────────────────
    Rule(
        name="shared_genre_with",
        description="Pairwise: games with same genre → sharedGenreWith",
        query=_q(
            """CONSTRUCT { ?g1 vg:sharedGenreWith ?g2 . }
WHERE {
    ?g1 vg:hasGenre ?gen .
    ?g2 vg:hasGenre ?gen .
    FILTER(STR(?g1) < STR(?g2))
}"""
        ),
        high_volume=True,
    ),
    # ── R11 : sharedEngineWith ────────────────────────────────────────────
    Rule(
        name="shared_engine_with",
        description="Pairwise: games with same engine → sharedEngineWith",
        query=_q(
            """CONSTRUCT { ?g1 vg:sharedEngineWith ?g2 . }
WHERE {
    ?g1 vg:madeWith ?e .
    ?g2 vg:madeWith ?e .
    FILTER(STR(?g1) < STR(?g2))
}"""
        ),
        high_volume=True,
    ),
]

# Set of rule names considered "high volume" (for cap enforcement)
_HIGH_VOLUME_NAMES: set[str] = {
    r.name for r in RULES if r.high_volume
}


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
            logger.info("Loaded %d triples from %s (format: %s)", len(g), path.name, fmt)
            return g
        except Exception:
            g = Graph()
    raise ValueError(f"Cannot parse {path} — tried xml, turtle, nt")


def apply_rule(g: Graph, rule: Rule, max_pairs: int) -> int:
    """Execute *rule.query* against *g*, add inferred triples, return count added.

    High-volume rules are capped at *max_pairs* new triples; if the cap is hit a
    warning is logged and the rule stops adding further triples.
    """
    before = len(g)

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
