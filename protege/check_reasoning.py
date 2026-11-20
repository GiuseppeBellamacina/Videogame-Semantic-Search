"""Self-check without the Protégé GUI: HermiT on the same files Protégé opens, plus the
expected inferences, SWRL conclusions and inconsistencies.

    uv run --with owlready2==0.46 python protege/check_reasoning.py

Extra tool, the only file outside the style of the course examples: it uses owlready2 to
call HermiT from Python. Java comes from the Protégé install (its JRE) or from JAVA_EXE.
"""

import os
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import owlready2 as o
from rdflib import Graph, URIRef
from rdflib.namespace import OWL

HERE = Path(__file__).resolve().parent
VG = "http://www.videogame-ontology.org/ontology#"
JAVA = [p / "Protege-5.6.9-win" / "Protege-5.6.9" / "jre" / "bin" / "java.exe" for p in (HERE.parent, HERE.parent.parent / "Videogame-Semantic-Search")]
o.JAVA_EXE = os.environ.get("JAVA_EXE") or str(next((j for j in JAVA if j.exists()), "java"))
failures = []


def merged(file, extra=()):
    """The file plus everything it imports, resolved through the catalog of its folder."""
    g, todo, seen = Graph(), [Path(file)], set()
    while todo:
        f = todo.pop()
        if f not in seen:
            seen.add(f)
            part = Graph().parse(f)
            catalog = {u.get("name"): (f.parent / u.get("uri")).resolve() for u in ET.parse(f.parent / "catalog-v001.xml").iter("{urn:oasis:names:tc:entity:xmlns:xml:catalog}uri")}
            todo += [catalog[str(i)] for i in part.objects(None, OWL.imports)]
            g += part
    g.remove((None, OWL.imports, None))
    for t in extra:
        g.add(t)
    return g


def reason(name, file, extra=()):
    """HermiT on the file (and its imports): the world, or None if the ontology is inconsistent."""
    nt = Path(tempfile.gettempdir()) / f"vg_check_{name}.nt"
    merged(file, extra).serialize(nt, format="nt", encoding="utf-8")
    w = o.World()
    try:
        with w.get_ontology("file://" + nt.as_posix()).load():
            o.sync_reasoner_hermit(w, infer_property_values=True, debug=0)
    except o.OwlReadyInconsistentOntologyError:
        print(f"[{name}] INCONSISTENT")
        return None
    print(f"[{name}] consistent")
    return w


def check(ok, what):
    print(f"   {'ok  ' if ok else 'FAIL'} {what}")
    if not ok:
        failures.append(what)


def is_a(w, ind, cls):
    return any(getattr(c, "iri", None) == VG + cls for c in w[VG + ind].INDIRECT_is_a)


def related(w, s, p, obj):
    return w[VG + obj] in getattr(w[VG + s], "INDIRECT_" + w[VG + p].python_name)


def types(w, cls, yes, no=()):
    for i in yes:
        check(is_a(w, i, cls), f"{i} is {cls}")
    for i in no:
        check(not is_a(w, i, cls), f"{i} is NOT {cls}")


def main():
    w = reason("schema", HERE / "schema_generated.ttl")
    check(w is not None and not list(w.inconsistent_classes()), "schema: consistent, no unsatisfiable classes")

    w = reason("videogames", HERE / "videogames.ttl")  # schema + demo + SWRL rules
    check(w is not None, "videogames.ttl (schema + demo + rules) is consistent")
    if w is None:
        sys.exit(1)
    check(not list(w.inconsistent_classes()), "no unsatisfiable classes")
    print(" sequel chains, domain/range")
    check(related(w, "Grand_Theft_Auto_V", "sequelOf", "Grand_Theft_Auto"), "GTA V sequelOf GTA, never asserted (transitivity)")
    check(related(w, "Grand_Theft_Auto", "hasSequel", "Grand_Theft_Auto_VI"), "GTA hasSequel GTA VI (inverse + transitivity)")
    check(is_a(w, "Grand_Theft_Auto", "VideoGame"), "untyped GTA is a VideoGame (domain/range)")
    print(" defined classes")
    types(w, "LateEntry", ["Grand_Theft_Auto_III", "Dark_Souls_III", "The_Witcher_3_Wild_Hunt", "Mass_Effect_3"], ["Grand_Theft_Auto_2", "Dark_Souls_II", "Portal_2"])
    types(w, "LongRunningOriginal", ["Grand_Theft_Auto", "Dark_Souls", "The_Witcher", "Mass_Effect"], ["Portal", "Grand_Theft_Auto_VI"])
    types(w, "AcclaimedSequel", ["Grand_Theft_Auto_IV", "Portal_2", "Mass_Effect_2"], ["Grand_Theft_Auto_V", "The_Legend_of_Zelda_Ocarina_of_Time"])
    types(w, "RecentGame", ["The_Legend_of_Zelda_Tears_of_the_Kingdom", "Grand_Theft_Auto_VI"], ["The_Legend_of_Zelda_Breath_of_the_Wild"])
    types(w, "MultiPlatformGame", ["Grand_Theft_Auto_V", "The_Legend_of_Zelda_Breath_of_the_Wild"], ["The_Legend_of_Zelda_Tears_of_the_Kingdom"])
    types(w, "BandaiNamcoPublishedGame", ["Dark_Souls", "Dark_Souls_II"], ["The_Witcher"])
    types(w, "Developer", ["dev/Bungie"], ["pub/Atari"])
    types(w, "Publisher", ["pub/Atari", "dev/FromSoftware"], ["dev/Bungie"])
    check(related(w, "Mass_Effect", "sharesDeveloperWith", "Mass_Effect_3"), "Mass Effect sharesDeveloperWith Mass Effect 3 (chain)")
    print(" groups and series")
    check(related(w, "dev/Halo_Studios", "subsidiaryOf", "pub/Microsoft"), "Halo Studios subsidiaryOf Microsoft (transitivity)")
    types(w, "PlatformHolder", ["pub/Nintendo", "pub/Microsoft", "pub/Sony_Interactive_Entertainment"], ["pub/Xbox_Game_Studios", "pub/Electronic_Arts"])
    types(w, "FirstPartyGame", ["The_Legend_of_Zelda_Breath_of_the_Wild", "Halo_4", "Mass_Effect"], ["Mass_Effect_2", "Grand_Theft_Auto_V"])
    types(w, "LongRunningFranchise", ["franchise/Grand_Theft_Auto", "franchise/Dark_Souls", "franchise/Mass_Effect"], ["franchise/Portal", "franchise/Halo", "franchise/The_Legend_of_Zelda"])
    types(w, "FranchiseWithStudioChange", ["franchise/Halo"], ["franchise/Grand_Theft_Auto", "franchise/Dark_Souls"])
    print(" SWRL rules")
    types(w, "SelfPublishedGame", ["Portal", "Dark_Souls", "The_Witcher_3_Wild_Hunt"], ["The_Legend_of_Zelda_Ocarina_of_Time", "Grand_Theft_Auto_VI"])
    types(w, "SequelByDifferentStudio", ["Halo_4"], ["Grand_Theft_Auto_VI", "Dark_Souls_III"])
    types(w, "FirstPartyOnRivalConsole", ["Mass_Effect"], ["Halo_4", "Mass_Effect_2", "The_Legend_of_Zelda_Ocarina_of_Time"])
    types(w, "CouchCoopCandidate", ["Portal_2", "Halo_Reach"], ["Halo_4", "The_Witcher"])
    types(w, "MustPlayGame", ["The_Legend_of_Zelda_Ocarina_of_Time", "Grand_Theft_Auto_IV", "Portal_2"], ["Mass_Effect_2", "Dark_Souls"])

    inc = HERE / "inconsistencies"
    for f in ["inc1_disjoint", "inc2_functional", "inc3_cardinality", "inc4_key"]:
        check(reason(f, inc / f"{f}.ttl") is None, f"{f} is inconsistent")
    check(reason("inc3b_sameas", inc / "inc3b_sameas.ttl") is not None, "inc3b_sameas is consistent")
    # KB |= NX = Switch exactly when KB + {NX != Switch} is inconsistent
    nx, switch = URIRef(VG + "platform/Nintendo_NX"), URIRef(VG + "platform/Nintendo_Switch")
    check(reason("inc3b_different", inc / "inc3b_sameas.ttl", [(nx, OWL.differentFrom, switch)]) is None, "inc3b entails NX sameAs Nintendo Switch")

    print("\nALL CHECKS PASSED" if not failures else f"\n{len(failures)} FAILED: " + "; ".join(failures))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
