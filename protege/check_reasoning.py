"""Verifica con HermiT le deduzioni attese (strumento extra, usa owlready2).

    uv run --with owlready2==0.46 python protege/check_reasoning.py
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
JAVA = HERE.parent / "Protege-5.6.9-win" / "Protege-5.6.9" / "jre" / "bin" / "java.exe"
o.JAVA_EXE = os.environ.get("JAVA_EXE") or (str(JAVA) if JAVA.exists() else "java")
failures = []


def merged(file, extra=()):
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
    nt = Path(tempfile.gettempdir()) / f"vg_check_{name}.nt"
    merged(file, extra).serialize(nt, format="nt", encoding="utf-8")
    w = o.World()
    try:
        with w.get_ontology("file://" + nt.as_posix()).load():
            o.sync_reasoner_hermit(w, infer_property_values=True, debug=0)
    except o.OwlReadyInconsistentOntologyError:
        print(f"[{name}] inconsistente")
        return None
    print(f"[{name}] consistente")
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
        check(is_a(w, i, cls), f"{i} è {cls}")
    for i in no:
        check(not is_a(w, i, cls), f"{i} non è {cls}")


EXPECTED = [
    ("VideoGame", ["Grand_Theft_Auto"], []),
    ("GameDirector", ["person/Hidetaka_Miyazaki", "person/Casey_Hudson"], []),
    ("StudioHead", ["person/Hidetaka_Miyazaki"], ["person/Casey_Hudson"]),
    ("Remaster", ["The_Legend_of_Zelda_Ocarina_of_Time_3D"], []),
    ("MortalCharacter", ["character/Gwyn_Lord_of_Sunlight", "character/Cesare_Borgia"], ["character/Mario"]),
    ("Developer", ["company/Black_Isle_Studios"], ["company/Microsoft"]),
    ("PlatformHolder", ["company/Nintendo", "company/Microsoft", "company/Sony_Interactive_Entertainment"], ["company/Xbox_Game_Studios"]),
    ("FirstPartyGame", ["Mass_Effect", "Fallout_4", "The_Legend_of_Zelda_Breath_of_the_Wild"], ["Mass_Effect_2", "Assassins_Creed_II"]),
    ("FoundedByVeterans", ["company/Obsidian_Entertainment"], ["company/Valve"]),
    ("LateEntry", ["Assassins_Creed_Revelations", "The_Legend_of_Zelda_Spirit_Tracks", "Grand_Theft_Auto_III"], ["Super_Mario_Galaxy_2"]),
    ("AcclaimedSequel", ["Grand_Theft_Auto_IV", "Portal_2"], []),
    ("GOTYWinner", ["The_Witcher_3_Wild_Hunt", "Fallout_4"], ["The_Witcher"]),
    ("RemasteredClassic", ["The_Legend_of_Zelda_Ocarina_of_Time", "Mass_Effect"], ["Fallout_3"]),
    ("RemasterCollection", ["Super_Mario_3D_All_Stars", "Mass_Effect_Legendary_Edition"], ["The_Legend_of_Zelda_Ocarina_of_Time_3D"]),
    ("StillPlayable", ["Grand_Theft_Auto_III", "The_Legend_of_Zelda_Breath_of_the_Wild", "Fallout_4", "Assassins_Creed_IV_Black_Flag"], ["Mass_Effect", "Halo_Reach"]),
    ("LiteraryAdaptation", ["The_Witcher_3_Wild_Hunt"], ["Mass_Effect"]),
    ("AuteurGame", ["Dark_Souls", "Dark_Souls_III"], ["Dark_Souls_II"]),
    ("LongRunningFranchise", ["franchise/Grand_Theft_Auto", "franchise/Assassins_Creed", "franchise/Fallout", "franchise/The_Legend_of_Zelda"], ["franchise/Super_Mario", "franchise/Portal"]),
    ("TransmediaFranchise", ["franchise/The_Witcher", "franchise/Fallout", "franchise/Super_Mario", "franchise/Halo"], ["franchise/Grand_Theft_Auto", "franchise/The_Legend_of_Zelda"]),
    ("FranchiseWithStudioChange", ["franchise/Halo", "franchise/Fallout"], ["franchise/Super_Mario"]),
    ("RecurringCharacter", ["character/Link", "character/Geralt_of_Rivia", "character/Ezio_Auditore_da_Firenze", "character/Chell"], ["character/Niko_Bellic"]),
    ("RecurringVillain", ["character/Bowser", "character/Ganondorf", "character/GLaDOS"], ["character/Mario"]),
    ("RogueAI", ["character/GLaDOS", "character/Wheatley"], ["character/Cortana"]),
    ("HistoricalCharacter", ["character/Leonardo_da_Vinci", "character/Cesare_Borgia"], ["character/Ezio_Auditore_da_Firenze"]),
    ("FirstPartyOnRivalConsole", ["Mass_Effect", "Fallout_4", "Fallout_New_Vegas"], ["Halo_4", "The_Legend_of_Zelda_Breath_of_the_Wild", "Mass_Effect_2"]),
    ("SequelByDifferentStudio", ["Halo_4", "Fallout_3"], ["Grand_Theft_Auto_VI", "Dark_Souls_III"]),
    ("VeteransReturn", ["Fallout_New_Vegas"], ["Fallout_3"]),
    ("EngineChangeSequel", ["Grand_Theft_Auto_IV", "The_Witcher_2_Assassins_of_Kings", "Fallout_4"], ["Grand_Theft_Auto_V", "Mass_Effect_2"]),
    ("ExternalEngineGame", ["Mass_Effect", "The_Witcher", "Grand_Theft_Auto_III", "Fallout_3", "Fallout_New_Vegas"], ["The_Witcher_3_Wild_Hunt", "Portal_2"]),
    ("InHouseEngineGame", ["The_Witcher_3_Wild_Hunt", "Fallout_4", "Portal_2"], ["Mass_Effect"]),
    ("ReturningDirectorSequel", ["Mass_Effect_2", "Fallout_4", "Dark_Souls_III", "The_Legend_of_Zelda_Tears_of_the_Kingdom"], ["Halo_4"]),
    ("DefeatedVillain", ["character/Cesare_Borgia", "character/Eredin", "character/Gwyn_Lord_of_Sunlight", "character/Demise"], ["character/Bowser"]),
    ("MustPlayGame", ["The_Legend_of_Zelda_Ocarina_of_Time", "Grand_Theft_Auto_IV"], ["Fallout_4"]),
]
RELATIONS = [
    ("Grand_Theft_Auto_V", "sequelOf", "Grand_Theft_Auto"),
    ("company/Halo_Studios", "subsidiaryOf", "company/Microsoft"),
    ("The_Witcher", "techLinkedTo", "Mass_Effect"),
    ("Grand_Theft_Auto_III", "playableOn", "platform/PlayStation_5"),
    ("Fallout_4", "publishedByGroup", "company/Microsoft"),
]


def main():
    w = reason("schema", HERE / "schema.ttl")
    check(w is not None and not list(w.inconsistent_classes()), "schema consistente, nessuna classe insoddisfacibile")
    w = reason("videogiochi", HERE / "videogiochi.ttl")
    check(w is not None, "videogiochi.ttl consistente")
    if w is None:
        sys.exit(1)
    check(not list(w.inconsistent_classes()), "nessuna classe insoddisfacibile")
    for cls, yes, no in EXPECTED:
        types(w, cls, yes, no)
    for s, p, x in RELATIONS:
        check(related(w, s, p, x), f"{s} {p} {x}")
    test = HERE / "test"
    for f in ["errore_disgiunzione", "errore_funzionale", "errore_cardinalita", "errore_chiave"]:
        check(reason(f, test / f"{f}.ttl") is None, f"{f} inconsistente")
    check(reason("deduzione_sameas", test / "deduzione_sameas.ttl") is not None, "deduzione_sameas consistente")
    nx, switch = URIRef(VG + "platform/Nintendo_NX"), URIRef(VG + "platform/Nintendo_Switch")
    check(reason("sameas_negato", test / "deduzione_sameas.ttl", [(nx, OWL.differentFrom, switch)]) is None, "deduzione_sameas implica NX = Nintendo Switch")
    print("\nTUTTI I CONTROLLI SUPERATI" if not failures else f"\n{len(failures)} FALLITI: " + "; ".join(failures))
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
