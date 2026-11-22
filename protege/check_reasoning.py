"""Verifica con HermiT (via owlready2) le deduzioni attese e i test di inconsistenza.

uv run --with owlready2==0.46 python protege/check_reasoning.py
"""

import os
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import owlready2 as owl2
from rdflib import Graph, URIRef
from rdflib.namespace import OWL

HERE = Path(__file__).resolve().parent
VG = "http://www.videogame-ontology.org/ontology#"
CATALOG_URI = "{urn:oasis:names:tc:entity:xmlns:xml:catalog}uri"
# il JRE incluso in Protégé (cartella scompattata con o senza il suffisso -win)
BUNDLED_JAVA = [
    HERE.parent / d / "jre" / "bin" / "java.exe"
    for d in ("Protege-5.6.9", "Protege-5.6.9-win/Protege-5.6.9")
]
owl2.JAVA_EXE = os.environ.get("JAVA_EXE") or next(
    (str(j) for j in BUNDLED_JAVA if j.exists()), "java"
)

results = []  # (superato, descrizione)


def merge_imports(file, extra=()):
    """Il file e tutte le ontologie che importa (risolte con il catalogo), in un solo grafo senza `owl:imports`."""
    merged, todo, seen = Graph(), [Path(file)], set()
    while todo:
        current = todo.pop()
        if current in seen:
            continue
        seen.add(current)
        part = Graph().parse(current)
        catalog = {
            u.get("name"): (current.parent / u.get("uri")).resolve()
            for u in ET.parse(current.parent / "catalog-v001.xml").iter(CATALOG_URI)
        }
        todo += [catalog[str(imported)] for imported in part.objects(None, OWL.imports)]
        merged += part
    merged.remove((None, OWL.imports, None))
    for triple in extra:
        merged.add(triple)
    return merged


def reason(name, file, extra=()):
    """Avvia HermiT. Restituisce il mondo di owlready2, oppure None se l'ontologia è inconsistente."""
    ntriples = Path(tempfile.gettempdir()) / f"vg_check_{name}.nt"
    merge_imports(file, extra).serialize(ntriples, format="nt", encoding="utf-8")
    world = owl2.World()
    try:
        with world.get_ontology("file://" + ntriples.as_posix()).load():
            owl2.sync_reasoner_hermit(world, infer_property_values=True, debug=0)
    except owl2.OwlReadyInconsistentOntologyError:
        print(f"[{name}] inconsistente")
        return None
    print(f"[{name}] consistente")
    return world


def check(ok, what):
    results.append((ok, what))
    print(f"   {'ok  ' if ok else 'FAIL'} {what}")


def is_a(world, individual, cls):
    return any(
        getattr(c, "iri", None) == VG + cls
        for c in world[VG + individual].INDIRECT_is_a
    )


def related(world, subject, prop, obj):
    return world[VG + obj] in getattr(
        world[VG + subject], "INDIRECT_" + world[VG + prop].python_name
    )


def check_types(world, cls, yes, no=()):
    for individual in yes:
        check(is_a(world, individual, cls), f"{individual} è {cls}")
    for individual in no:
        check(not is_a(world, individual, cls), f"{individual} non è {cls}")


# attese e relazioni calcolate a parte dal dataset in Python, non dal reasoner; una riga per voce: black le lascia stare
# fmt: off
EXPECTED = [
    ("VideoGame", ["Grand_Theft_Auto"], []),
    ("GameDirector", ["person/Hidetaka_Miyazaki", "person/Casey_Hudson"], []),
    ("StudioHead", ["person/Hidetaka_Miyazaki"], ["person/Casey_Hudson"]),
    ("Remaster", ["The_Legend_of_Zelda_Ocarina_of_Time_3D"], []),
    ("DeceasedCharacter", ["character/Gwyn_Lord_of_Sunlight", "character/Cesare_Borgia"], ["character/Mario"]),
    ("Killer", ["character/Ezio_Auditore_da_Firenze", "character/Geralt_of_Rivia", "character/Chosen_Undead"], ["character/Mario"]),
    ("MultipleKiller", ["character/Jason_Brody", "character/Link", "character/Niko_Bellic"], ["character/Midna", "character/Mario"]),
    ("ViolentStoryGame", ["Far_Cry_3", "Grand_Theft_Auto_IV", "The_Legend_of_Zelda_Twilight_Princess"], ["Super_Mario_Odyssey", "Portal_2", "The_Legend_of_Zelda_Four_Swords"]),
    ("RealisticViolenceGame", ["Far_Cry_3", "Grand_Theft_Auto_IV", "Halo_3", "Assassins_Creed_Origins", "Cyberpunk_2077"], ["The_Legend_of_Zelda_Twilight_Princess"]),
    ("FantasyViolenceGame", ["The_Legend_of_Zelda_Twilight_Princess", "The_Legend_of_Zelda_Skyward_Sword"], ["Far_Cry_3", "The_Legend_of_Zelda_Ocarina_of_Time"]),
    ("Synthetic", ["character/Cortana", "character/GLaDOS", "character/343_Guilty_Spark"], ["character/Catherine_Halsey", "character/The_Weapon"]),
    ("PlayerCharacter", ["character/Link", "character/Chell", "character/Arbiter", "character/Zelda"], ["character/Cortana", "character/Ganondorf"]),
    ("KilledMoreThanOnce", ["character/Ganondorf"], ["character/Catalina"]),
    ("ReturningCharacter", ["character/Ganondorf", "character/Catalina"], ["character/Gwyn_Lord_of_Sunlight"]),
    ("ReturnAfterDeathGame", ["The_Legend_of_Zelda_Breath_of_the_Wild", "Grand_Theft_Auto_San_Andreas"], ["The_Legend_of_Zelda_Twilight_Princess"]),
    ("PrequelGame", ["Halo_Reach", "Grand_Theft_Auto_San_Andreas"], ["Halo_4"]),
    ("PrequelReturn", ["Grand_Theft_Auto_San_Andreas"], ["The_Legend_of_Zelda_Breath_of_the_Wild"]),
    ("CurrentGenerationConsole", ["platform/PlayStation_5", "platform/Nintendo_Switch_2"], ["platform/Nintendo_Switch", "platform/PlayStation_4"]),
    ("Adaptation", ["Cyberpunk_2077", "The_Walking_Dead"], ["Elden_Ring"]),
    ("Developer", ["company/Black_Isle_Studios"], ["company/Microsoft"]),
    ("PlatformHolder", ["company/Nintendo", "company/Microsoft", "company/Sony_Interactive_Entertainment"], ["company/Xbox_Game_Studios"]),
    ("FirstPartyGame", ["Mass_Effect", "Fallout_4", "The_Legend_of_Zelda_Breath_of_the_Wild"], ["Mass_Effect_2", "Assassins_Creed_II"]),
    ("FoundedByVeterans", ["company/Obsidian_Entertainment", "company/AdHoc_Studio"], ["company/Valve"]),
    ("LateEntry", ["Assassins_Creed_Revelations", "The_Legend_of_Zelda_Spirit_Tracks", "Grand_Theft_Auto_III"], ["Super_Mario_Bros_2"]),
    ("AcclaimedSequel", ["Grand_Theft_Auto_IV", "Portal_2"], []),
    ("GOTYWinner", ["The_Witcher_3_Wild_Hunt", "Fallout_4"], ["The_Witcher"]),
    ("RemasteredClassic", ["The_Legend_of_Zelda_Ocarina_of_Time", "Mass_Effect"], ["Fallout_3"]),
    ("RemasterCollection", ["Super_Mario_3D_All_Stars", "Mass_Effect_Legendary_Edition"], ["The_Legend_of_Zelda_Ocarina_of_Time_3D"]),
    ("StillPlayable", ["Grand_Theft_Auto_III", "The_Legend_of_Zelda_Breath_of_the_Wild", "Fallout_4", "Assassins_Creed_IV_Black_Flag", "Halo_Combat_Evolved"], ["Mass_Effect", "Halo_Reach"]),
    ("LiteraryAdaptation", ["The_Witcher_3_Wild_Hunt"], ["Mass_Effect"]),
    ("AuteurGame", ["Dark_Souls", "Dark_Souls_III"], ["Dark_Souls_II"]),
    ("LongRunningFranchise", ["franchise/Grand_Theft_Auto", "franchise/Assassins_Creed", "franchise/Fallout", "franchise/The_Legend_of_Zelda", "franchise/Super_Mario"], ["franchise/Portal"]),
    ("TransmediaFranchise", ["franchise/The_Witcher", "franchise/Fallout", "franchise/Super_Mario", "franchise/Halo"], ["franchise/Grand_Theft_Auto", "franchise/The_Legend_of_Zelda"]),
    ("FranchiseWithStudioChange", ["franchise/Halo", "franchise/Fallout", "franchise/Far_Cry"], ["franchise/Portal"]),
    ("RecurringCharacter", ["character/Zelda", "character/Link", "character/Geralt_of_Rivia", "character/Ezio_Auditore_da_Firenze", "character/Chell"], ["character/Niko_Bellic"]),
    ("RecurringVillain", ["character/Bowser", "character/Ganondorf", "character/GLaDOS"], ["character/Mario"]),
    ("RogueAI", ["character/GLaDOS", "character/Wheatley", "character/Cortana"], ["character/The_Weapon"]),
    ("HistoricalCharacter", ["character/Leonardo_da_Vinci", "character/Cesare_Borgia"], ["character/Ezio_Auditore_da_Firenze"]),
    ("FirstPartyOnRivalConsole", ["Mass_Effect", "Fallout_4", "Fallout_New_Vegas", "Minecraft"], ["Halo_4", "The_Legend_of_Zelda_Breath_of_the_Wild", "Mass_Effect_2"]),
    ("SequelByDifferentStudio", ["Halo_4", "Fallout_3", "Far_Cry_2", "Far_Cry_6"], ["Grand_Theft_Auto_VI", "Dark_Souls_III", "Far_Cry_3"]),
    ("VeteransReturn", ["Fallout_New_Vegas"], ["Fallout_3"]),
    ("EngineChangeSequel", ["Grand_Theft_Auto_IV", "The_Witcher_2_Assassins_of_Kings", "Fallout_4", "Far_Cry_2", "Far_Cry_3"], ["Grand_Theft_Auto_V", "Mass_Effect_2", "Far_Cry_4"]),
    ("ExternalEngineGame", ["Mass_Effect", "The_Witcher", "Grand_Theft_Auto_III", "Fallout_3", "Fallout_New_Vegas", "Far_Cry_6"], ["The_Witcher_3_Wild_Hunt", "Portal_2", "Far_Cry_5"]),
    ("InHouseEngineGame", ["The_Witcher_3_Wild_Hunt", "Fallout_4", "Portal_2"], ["Mass_Effect"]),
    ("ReturningDirectorSequel", ["Mass_Effect_2", "Fallout_4", "Dark_Souls_III", "The_Legend_of_Zelda_Tears_of_the_Kingdom"], ["Halo_4"]),
    ("DefeatedVillain", ["character/Cesare_Borgia", "character/Eredin", "character/Gwyn_Lord_of_Sunlight", "character/Demise"], ["character/Bowser"]),
    ("MustPlayGame", ["The_Legend_of_Zelda_Ocarina_of_Time", "Grand_Theft_Auto_IV", "Halo_Combat_Evolved"], ["Fallout_4", "Halo_3"]),
    ("Remaster", ["The_Legend_of_Zelda_Ocarina_of_Time_2026", "Halo_Campaign_Evolved"], []),
    ("ProlificDirector", ["person/Hidetaka_Miyazaki", "person/Shigeru_Miyamoto"], ["person/Josh_Holmes"]),
    ("ProlificDeveloper", ["company/Bungie", "company/Rockstar_North"], ["company/Obsidian_Entertainment"]),
    ("FirstPartyStudio", ["company/Halo_Studios", "company/Mojang_Studios", "company/Nintendo_EPD", "company/Bethesda_Game_Studios"], ["company/BioWare", "company/Capcom", "company/Ubisoft_Montreal"]),
    ("VillainSlayer", ["character/Link", "character/Ezio_Auditore_da_Firenze", "character/Geralt_of_Rivia"], ["character/Mario", "character/Chell"]),
    ("TragicProtagonist", ["character/Gustave", "character/Haytham_Kenway"], ["character/Link"]),
    ("Turncoat", ["character/Cortana"], ["character/Master_Chief"]),
    ("HistoricalGame", ["Assassins_Creed_II", "Assassins_Creed_Origins"], ["The_Witcher_3_Wild_Hunt"]),
    ("SciFiGame", ["Halo_Infinite", "Portal_2", "Mass_Effect", "Mass_Effect_2", "Mass_Effect_3"], ["The_Legend_of_Zelda_Breath_of_the_Wild"]),
    ("RogueAIGame", ["Halo_5_Guardians", "Portal"], ["Halo_4"]),
    ("PreviousGenerationConsole", ["platform/Nintendo_Switch", "platform/PlayStation_4"], ["platform/PlayStation_5", "platform/Nintendo_Switch_2"]),
    ("CrossGenerationGame", ["The_Legend_of_Zelda_Ocarina_of_Time", "Grand_Theft_Auto_III", "Minecraft"], ["Mass_Effect", "The_Legend_of_Zelda_Majoras_Mask"]),
    ("GroupEngineGame", ["Grand_Theft_Auto_V", "Assassins_Creed_Mirage", "Far_Cry_6"], ["Grand_Theft_Auto_III", "Mass_Effect", "Assassins_Creed_II", "The_Witcher_3_Wild_Hunt"]),
    ("SameGroupSequel", ["Assassins_Creed_Origins", "Super_Mario_World", "Fallout_New_Vegas"], ["Halo_4", "Fallout_3"]),
    ("SelfPublishedGame", ["Portal_2", "Minecraft", "Dispatch"], ["Halo_4", "Grand_Theft_Auto_V"]),
    ("ClassicGame", ["Grand_Theft_Auto_III", "The_Legend_of_Zelda_Ocarina_of_Time", "Halo_Combat_Evolved", "Super_Mario_Bros_2"], ["Grand_Theft_Auto_V", "Elden_Ring", "The_Legend_of_Zelda_Ocarina_of_Time_3D"]),
    ("ClassicStillPlayable", ["Grand_Theft_Auto_III", "Grand_Theft_Auto_San_Andreas", "Grand_Theft_Auto_Vice_City", "Halo_Combat_Evolved", "The_Legend_of_Zelda_Ocarina_of_Time"], ["Grand_Theft_Auto_IV", "The_Legend_of_Zelda_Majoras_Mask", "Halo_Infinite"]),
]

RELATIONS = [
    ("Grand_Theft_Auto_V", "sequelOf", "Grand_Theft_Auto"),
    ("company/Halo_Studios", "subsidiaryOf", "company/Microsoft"),
    ("The_Witcher", "techLinkedTo", "Mass_Effect"),
    ("Grand_Theft_Auto_III", "playableOn", "platform/PlayStation_5"),
    ("Fallout_4", "publishedByGroup", "company/Microsoft"),
    ("character/Vaas_Montenegro", "killedBy", "character/Jason_Brody"),
    ("company/Obsidian_Entertainment", "inGroupOf", "company/Microsoft"),
    ("company/Bethesda_Game_Studios", "inGroupOf", "company/Microsoft"),
]
# fmt: on


def main():
    schema = reason("schema", HERE / "schema.ttl")
    check(
        schema is not None and not list(schema.inconsistent_classes()),
        "schema consistente, nessuna classe insoddisfacibile",
    )
    world = reason("videogiochi", HERE / "videogiochi.ttl")
    check(world is not None, "videogiochi.ttl consistente")
    if world is None:
        sys.exit(1)
    check(not list(world.inconsistent_classes()), "nessuna classe insoddisfacibile")
    for cls, yes, no in EXPECTED:
        check_types(world, cls, yes, no)
    for subject, prop, obj in RELATIONS:
        check(related(world, subject, prop, obj), f"{subject} {prop} {obj}")

    tests = HERE / "test"
    for name in [
        "errore_disgiunzione",
        "errore_funzionale",
        "errore_cardinalita",
        "errore_chiave",
        "errore_proprieta_disgiunte",
    ]:
        check(reason(name, tests / f"{name}.ttl") is None, f"{name} inconsistente")
    check(
        reason("deduzione_sameas", tests / "deduzione_sameas.ttl") is not None,
        "deduzione_sameas consistente",
    )
    nx, switch = URIRef(VG + "platform/Nintendo_NX"), URIRef(
        VG + "platform/Nintendo_Switch"
    )
    contradiction = reason(
        "sameas_negato",
        tests / "deduzione_sameas.ttl",
        [(nx, OWL.differentFrom, switch)],
    )
    check(contradiction is None, "deduzione_sameas implica NX = Nintendo Switch")

    failures = [what for ok, what in results if not ok]
    if not failures:
        (HERE / "relazione" / "controlli.tex").write_text(
            f"\\newcommand{{\\nControlli}}{{{len(results)}}}\n", encoding="utf-8"
        )
    print(
        "\nTUTTI I CONTROLLI SUPERATI"
        if not failures
        else f"\n{len(failures)} FALLITI: " + "; ".join(failures)
    )
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
