"""Bring an existing videogames_full.owl up to the current schema and data model WITHOUT a refetch.

A full build takes hours (fetch + owlrl). When only the schema and the company model changed, the
dataset is the same, so the output of a build can be reproduced with targeted edits on the built file:

  1. schema      every class/property/blank-node triple is replaced by the schema a build would write
                 (TBox + V2 axioms, owlrl closure, same cleaning as build_ontology._clean_tbox)
  2. alignments  the triples owlrl derived from the old owl:equivalentClass/equivalentProperty
                 alignments (dcterms:issued/title on every game, wd:Q* types) are dropped: the new
                 alignments are skos:closeMatch and derive nothing
  3. companies   a developer and a publisher with the same normalised name become ONE individual with
                 both roles (same rule as populate_wikidata.deduplicate_graph); sameCompanyAs is dropped
  4. closure     every Developer/Publisher individual gets rdf:type Company

It is not a substitute for a build (it cannot redo the fetch-time dedup of nominals), but the result
answers the same queries. The original files are copied to --backup first.

    uv run python ontology/scripts/retrofit_full.py            # patch ontology/output/videogames_full.*
    uv run python ontology/scripts/retrofit_full.py --dry-run  # compute and report, write nothing
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path

import pyoxigraph as ox
from rdflib import BNode, Graph, Literal, URIRef

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))  # build_ontology.py

import build_ontology as bo  # noqa: E402  (its _clean_* helpers are the build's own)
import enrich_owl as eo  # noqa: E402
import populate_wikidata as pw  # noqa: E402
import schema_loader  # noqa: E402

VG = "http://www.videogame-ontology.org/ontology#"
RDF_TYPE = ox.NamedNode("http://www.w3.org/1999/02/22-rdf-syntax-ns#type")
OWL = "http://www.w3.org/2002/07/owl#"
DCT = "http://purl.org/dc/terms/"
WD = "http://www.wikidata.org/entity/"
PREFIXES = f"PREFIX vg: <{VG}> PREFIX owl: <{OWL}> PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> "


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def _term(t):
    if isinstance(t, URIRef):
        return ox.NamedNode(str(t))
    if isinstance(t, BNode):
        return ox.BlankNode(str(t))
    if isinstance(t, Literal):
        if t.language:
            return ox.Literal(str(t), language=t.language)
        return ox.Literal(str(t), datatype=ox.NamedNode(str(t.datatype)) if t.datatype else None)
    raise TypeError(t)


def new_schema() -> Graph:
    """The schema triples a build would write: the same steps as stage_reason, on the TBox only."""
    import owlrl

    g = schema_loader.load_tbox()
    eo._add_axioms(g)
    eo.strip_dl_only_axioms(g)
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(g)
    bo._clean_closure(g)
    bo._clean_tbox(g, keep_dl=False)
    return g


def separate_colliding_games(st: ox.Store) -> None:
    """A game titled like a schema term shares its IRI with the class (the game "Platform" is vg:Platform):
    move its data to <IRI>_Game, as populate_wikidata.make_uri does for new builds."""
    game = ox.NamedNode(VG + "VideoGame")
    as_class = {s for (s,) in st.query(f"SELECT DISTINCT ?s WHERE {{ ?s a <{OWL}Class> }}")}
    moved = 0
    for c in as_class:
        if not isinstance(c, ox.NamedNode) or not any(True for _ in st.quads_for_pattern(c, RDF_TYPE, game)):
            continue
        new = ox.NamedNode(c.value + "_Game")
        for q in list(st.quads_for_pattern(c, None, None)):
            if q.predicate.value.startswith(VG) or (
                q.predicate == RDF_TYPE and isinstance(q.object, ox.NamedNode) and q.object.value.startswith(VG)
            ):
                st.remove(q)
                st.add(ox.Quad(new, q.predicate, q.object))
                moved += 1
        for q in list(st.quads_for_pattern(None, None, c)):
            if q.predicate.value.startswith(VG):
                st.remove(q)
                st.add(ox.Quad(q.subject, q.predicate, new))
                moved += 1
    log(f"games sharing an IRI with a schema term: {moved} triples moved")


def replace_schema(st: ox.Store, schema: Graph) -> None:
    """Drop every class/property/ontology/blank-node triple of the store, then add the new schema."""
    kinds = ("Class", "ObjectProperty", "DatatypeProperty", "Ontology", "AnnotationProperty")
    subjects = set()
    for k in kinds:
        for (s,) in st.query(f"SELECT DISTINCT ?s WHERE {{ ?s a <{OWL}{k}> }}"):
            if isinstance(s, ox.NamedNode):
                subjects.add(s)
    # a game can share its IRI with a class (the game "Platform" is vg:Platform): keep its data and
    # drop only the schema predicates, or the game would vanish with the class
    game = ox.NamedNode(VG + "VideoGame")
    schema_preds = {ox.NamedNode(OWL + p) for p in ("equivalentClass", "disjointWith")} | {
        ox.NamedNode("http://www.w3.org/2000/01/rdf-schema#subClassOf")
    }
    old = 0
    for s in subjects:
        shared = any(True for _ in st.quads_for_pattern(s, RDF_TYPE, game))
        for q in list(st.quads_for_pattern(s, None, None)):
            if shared and q.predicate not in schema_preds and not (
                q.predicate == RDF_TYPE and isinstance(q.object, ox.NamedNode) and q.object.value.startswith(OWL)
            ):
                continue
            st.remove(q)
            old += 1
    for q in list(st.quads_for_pattern(None, None, None)):
        if isinstance(q.subject, ox.BlankNode) or isinstance(q.object, ox.BlankNode):
            st.remove(q)
            old += 1
    st.extend(ox.Quad(_term(s), _term(p), _term(o)) for s, p, o in schema)
    log(f"schema: {old} old schema triples removed, {len(schema)} new ones added")


def drop_alignment_noise(st: ox.Store) -> None:
    """What owlrl derived from the old equivalentClass/equivalentProperty alignments."""
    n = 0
    for p in ("issued", "title", "description"):
        for q in list(st.quads_for_pattern(None, ox.NamedNode(DCT + p), None)):
            st.remove(q)
            n += 1
    for w in ("Q7889", "Q210167", "Q193564", "Q65956376"):
        for q in list(st.quads_for_pattern(None, RDF_TYPE, ox.NamedNode(WD + w))):
            st.remove(q)
            n += 1
    log(f"alignments: {n} derived triples dropped")


def merge_companies(st: ox.Store) -> int:
    """Developer and publisher with the same normalised name -> one individual (both roles)."""
    for q in list(st.quads_for_pattern(None, ox.NamedNode(VG + "sameCompanyAs"), None)):
        st.remove(q)
    by_name: dict[str, dict[str, list[ox.NamedNode]]] = defaultdict(lambda: {"dev": [], "pub": []})
    for kind, prop in (("dev", "developerName"), ("pub", "publisherName")):
        for s, n in st.query(f"SELECT ?s ?n WHERE {{ ?s <{VG}{prop}> ?n }}"):
            by_name[pw.dedup_name(prop, n.value)][kind].append(s)
    nominals = {s for (s,) in st.query(f"SELECT ?s WHERE {{ ?s a <{OWL}NamedIndividual> }}")}
    names = {ox.NamedNode(VG + n) for n in ("developerName", "publisherName")}

    def weight(u: ox.NamedNode) -> int:
        return sum(1 for _ in st.quads_for_pattern(u, None, None)) + sum(
            1 for _ in st.quads_for_pattern(None, None, u)
        )

    merged = 0
    for sides in by_name.values():
        uris = sides["dev"] + [u for u in sides["pub"] if u not in sides["dev"]]
        if not sides["dev"] or not sides["pub"] or len(uris) < 2:
            continue
        uris.sort(key=lambda u: (u in nominals, weight(u)), reverse=True)  # as deduplicate_graph
        canonical = uris[0]
        for dup in uris[1:]:
            for q in list(st.quads_for_pattern(dup, None, None)):
                st.remove(q)
                if q.predicate in names and any(True for _ in st.quads_for_pattern(canonical, q.predicate, None)):
                    continue  # one name per property: the canonical one
                st.add(ox.Quad(canonical, q.predicate, q.object))
            for q in list(st.quads_for_pattern(None, None, dup)):
                st.remove(q)
                st.add(ox.Quad(q.subject, q.predicate, canonical))
            merged += 1
    log(f"companies: {merged} developer/publisher pairs merged into one individual")
    return merged


def add_company_types(st: ox.Store) -> None:
    before = len(st)
    st.update(PREFIXES + "INSERT { ?x a vg:Company } WHERE { ?x a ?c . ?c rdfs:subClassOf* vg:Company }")
    log(f"closure: +{len(st) - before} rdf:type vg:Company")


def summary(st: ox.Store) -> dict:
    def one(q: str) -> int:
        return int(next(iter(st.query(PREFIXES + q)))[0].value)

    return {
        "triples": len(st),
        "games": one("SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE { ?x a vg:VideoGame }"),
        "developers": one("SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE { ?x a vg:Developer }"),
        "publishers": one("SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE { ?x a vg:Publisher }"),
        "both roles": one("SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE { ?x a vg:Developer, vg:Publisher }"),
        "companies": one("SELECT (COUNT(DISTINCT ?x) AS ?n) WHERE { ?x a vg:Company }"),
        "sameCompanyAs": one("SELECT (COUNT(*) AS ?n) WHERE { ?a vg:sameCompanyAs ?b }"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    out = HERE.parent / "output"
    ap.add_argument("--input", type=Path, default=out / "videogames_full.owl")
    ap.add_argument("--output", type=Path, default=out / "videogames_full", help="path without extension")
    ap.add_argument("--backup", type=Path, default=HERE.parent / ".cache" / "retrofit-backup")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    log(f"loading {args.input.name}")
    st = ox.Store()
    st.bulk_load(path=str(args.input), format=ox.RdfFormat.RDF_XML)
    before = summary(st)
    log(f"before: {before}")

    schema = new_schema()
    separate_colliding_games(st)
    replace_schema(st, schema)
    drop_alignment_noise(st)
    merge_companies(st)
    add_company_types(st)
    after = summary(st)
    log(f"after:  {after}")
    if args.dry_run:
        log("dry run: nothing written")
        return 0

    # new files get their own names: the originals are touched only once both are written
    new = {ext: args.output.with_name(f"{args.output.name}.retrofit{ext}") for ext in (".owl", ".ttl")}
    default = ox.DefaultGraph()
    log("writing RDF/XML")
    st.dump(str(new[".owl"]), format=ox.RdfFormat.RDF_XML, from_graph=default)
    log("writing Turtle")
    st.dump(
        str(new[".ttl"]),
        format=ox.RdfFormat.TURTLE,
        from_graph=default,
        prefixes={
            "vg": VG,
            "owl": OWL,
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
            "xsd": "http://www.w3.org/2001/XMLSchema#",
            "skos": "http://www.w3.org/2004/02/skos/core#",
        },
    )
    assert all(f.stat().st_size > 1_000_000 for f in new.values()), "a new file is empty: originals untouched"
    args.backup.mkdir(parents=True, exist_ok=True)
    for ext, f in new.items():
        orig = args.output.with_suffix(ext)
        if orig.exists() and not (args.backup / orig.name).exists():
            shutil.copy2(orig, args.backup / orig.name)  # keep the first original, never overwrite it
        shutil.move(str(f), str(orig))
    log(f"done; originals in {args.backup}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
