"""
One-shot pipeline: Wikidata fetch -> TBox/ABox merge -> reasoning -> .owl + .ttl

Stages (each prints its progress; the fetch is checkpointed per query x month
in ontology/.cache/wikidata, so an interrupted run resumes where it stopped):

  1. fetch     Wikidata -> ABox (+ dedup)               -> .cache/stage1_fetched.nt
  2. reason    V2 axioms -> strip DL-only axioms -> OWL-RL closure
               -> targeted materialisation (enrich_owl._materialise)
               -> SPARQL CONSTRUCT rules (scripts/construct_reasoner.py)
                                                          -> .cache/stage2_reasoned.nt
  3. validate  TBox checks + sanity counts of inferred classes
  4. write     videogames_full.owl (RDF/XML) and videogames_full.ttl (Turtle)

Usage (from the repo root):
    uv run python ontology/build_ontology.py                    # everything
    uv run python ontology/build_ontology.py --years 2024       # quick smoke test
    uv run python ontology/build_ontology.py --from-stage reason  # reuse stage 1
"""

from __future__ import annotations

import argparse
import logging
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path

from rdflib import OWL, RDF, Graph
from tqdm import tqdm

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "scripts"))

import construct_reasoner as cr  # noqa: E402
import enrich_owl as eo  # noqa: E402
import populate_wikidata as pw  # noqa: E402
import validate_tbox as vt  # noqa: E402

logger = logging.getLogger("build_ontology")

VG = eo.VG
STAGES = ["fetch", "reason", "validate", "write"]

# Classes that must be non-empty on the full dataset (inferred or typed)
SANITY_CLASSES = [
    "VideoGame", "Developer", "Publisher", "Genre", "Platform", "GameMode",
    "AwardWinningGame", "FranchiseGame", "SinglePlayerGame", "MultiplayerGame",
    "PCGame", "ConsoleGame", "PlayStationGame", "HighlyRatedGame", "RecentGame",
    "SequelGame", "StandaloneGame", "MultiConsoleGame", "NintendoPublishedGame",
]


def _bind(g: Graph) -> Graph:
    g.bind("vg", VG)
    g.bind("owl", OWL)
    return g


@contextmanager
def _heartbeat(label: str, g: Graph, every: int = 15):
    """owlrl has no progress hook: print elapsed time and graph size while it runs."""
    stop = threading.Event()
    t0 = time.time()

    def run() -> None:
        while not stop.wait(every):
            tqdm.write(f"  [{label}] {time.time() - t0:.0f}s elapsed, {len(g)} triples")

    threading.Thread(target=run, daemon=True).start()
    try:
        yield
    finally:
        stop.set()


def _timed(label: str):
    class _T:
        def __enter__(self):
            self.t = time.time()
            tqdm.write(f">> {label} ...")

        def __exit__(self, *exc):
            tqdm.write(f"OK {label} ({time.time() - self.t:.0f}s)")

    return _T()


def stage_fetch(years: list[int], cache_dir: Path, out: Path) -> Graph:
    g = pw.populate_from_wikidata(years=years, cache_dir=cache_dir / "wikidata")
    with _timed(f"Saving fetched graph ({len(g)} triples)"):
        g.serialize(str(out), format="nt")
    return g


def stage_reason(g: Graph, max_group: int, keep_dl: bool, out: Path) -> Graph:
    _bind(g)
    steps = [
        "V2 axioms", "strip DL-only", "OWL-RL closure", "materialise",
        "CONSTRUCT rules", "restore DL-only" if keep_dl else "finalise",
    ]
    with tqdm(total=len(steps), desc="Reasoning", unit="step", ncols=90) as bar:

        def step(i: int) -> None:
            bar.set_postfix_str(steps[i])

        step(0)
        eo._add_axioms(g)
        bar.update()

        step(1)
        eo.strip_dl_only_axioms(g)
        bar.update()

        step(2)
        import owlrl

        t0, n0 = time.time(), len(g)
        tqdm.write(f"  OWL-RL closure on {n0} triples (no percentage available, see the heartbeat lines)")
        with _heartbeat("OWL-RL", g):
            owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(g)
        tqdm.write(f"  OWL-RL: +{len(g) - n0} triples in {time.time() - t0:.0f}s")
        bar.update()

        step(3)
        inferred = eo._materialise(g, max_group=max_group)
        tqdm.write(f"  Materialisation: +{inferred} triples")
        bar.update()

        step(4)
        # shared_genre/engine_with are quadratic in the games per genre/engine (rdflib builds
        # every pair before the cap applies): fine on small data, unusable on the full dataset
        selected = {r.name for r in cr.RULES if not r.high_volume}
        counts = cr.apply_all(g, cr.RULES, max_pairs=0, selected=selected)
        tqdm.write(f"  CONSTRUCT rules: +{sum(counts.values())} triples")
        bar.update()

        step(5)
        if keep_dl:
            eo.restore_dl_only_axioms(g)
        bar.update()

    with _timed(f"Saving reasoned graph ({len(g)} triples)"):
        g.serialize(str(out), format="nt")
    return g


def stage_validate(g: Graph) -> None:
    tbox = Graph()
    tbox.parse(str(HERE / "videogames.owl"))
    findings = vt.validate(tbox)
    errors = [f for f in findings if f.severity == "ERROR"]
    tqdm.write(f"TBox validation: {len(errors)} errors, {len(findings)} findings")
    for f in errors:
        tqdm.write(f"  ERROR {f.code}: {f.message}")

    tqdm.write("Class instance counts:")
    for name in tqdm(SANITY_CLASSES, desc="Sanity counts", unit="class", ncols=90):
        n = sum(1 for _ in g.subjects(RDF.type, VG[name]))
        flag = "  <-- EMPTY" if n == 0 else ""
        tqdm.write(f"  {name:<18} {n:>8}{flag}")


def stage_write(g: Graph, out_stem: Path) -> None:
    for fmt, ext in (("xml", ".owl"), ("turtle", ".ttl")):
        path = out_stem.with_suffix(ext)
        with _timed(f"Writing {path.name}"):
            g.serialize(str(path), format=fmt)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--from-stage", choices=STAGES, default="fetch",
                    help="start at this stage, loading earlier results from the cache dir")
    ap.add_argument("--years", default=None,
                    help="year or range, e.g. 2024 or 2020-2026 (default: 2010-2026)")
    ap.add_argument("--cache-dir", type=Path, default=HERE / ".cache")
    ap.add_argument("--output", type=Path, default=HERE / "videogames_full",
                    help="output path without extension")
    ap.add_argument("--max-group", type=int, default=50,
                    help="cap for pairwise franchise/developer/publisher links")
    ap.add_argument("--keep-dl-axioms", action="store_true",
                    help="restore DL-only axioms in the output (not owlrl-safe)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(levelname)s  %(message)s")
    logging.getLogger("populate_wikidata").setLevel(logging.WARNING)

    years = pw.YEARS
    if args.years:
        a, _, b = args.years.partition("-")
        years = list(range(int(a), int(b or a) + 1))

    args.cache_dir.mkdir(parents=True, exist_ok=True)
    f1 = args.cache_dir / "stage1_fetched.nt"
    f2 = args.cache_dir / "stage2_reasoned.nt"
    start = STAGES.index(args.from_stage)

    g: Graph | None = None
    if start <= 0:
        g = stage_fetch(years, args.cache_dir, f1)
    if start <= 1:
        if g is None:
            g = Graph().parse(str(f1), format="nt")
        g = stage_reason(g, args.max_group, args.keep_dl_axioms, f2)
    if g is None:
        with _timed(f"Loading {f2.name}"):
            g = _bind(Graph().parse(str(f2), format="nt"))
    if start <= 2:
        stage_validate(g)
    stage_write(g, args.output)
    tqdm.write(f"Done: {args.output.with_suffix('.owl')} and .ttl")


if __name__ == "__main__":
    main()
