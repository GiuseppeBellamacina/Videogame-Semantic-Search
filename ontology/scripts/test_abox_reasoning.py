"""The test instances of Appendix A (ontology/tests/test_abox.ttl) go through the real reasoning stage
(uv run pytest ontology/scripts); no Wikidata, no build."""

import sys
import tempfile
from pathlib import Path

import schema_loader
from rdflib import OWL, RDF, Graph

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import build_ontology as bo  # noqa: E402

VG = bo.VG
ABOX = Path(__file__).resolve().parent.parent / "tests" / "test_abox.ttl"


def _reasoned() -> Graph:
    g = schema_loader.load_tbox()
    g += Graph().parse(ABOX)
    return bo.stage_reason(g, 50, False, Path(tempfile.mkdtemp()) / "r.nt")


def _types(g: Graph, name: str) -> set[str]:
    return {str(o).split("#")[-1] for o in g.objects(VG[name], RDF.type) if str(o).startswith(str(VG))}


def test_classifications_of_the_appendix():
    g = _reasoned()
    assert {"MultiplayerGame", "SinglePlayerGame", "ConsoleGame", "PlayStationGame", "PCGame", "WindowsGame",
            "HighlyRatedGame", "RecentGame", "AwardWinningGame", "StandaloneGame"} <= _types(g, "GameA")
    assert "RecentGame" not in _types(g, "GameB") and "NintendoGame" in _types(g, "GameB")
    assert "SequelGame" in _types(g, "GameC") and "StandaloneGame" not in _types(g, "GameC")


def test_company_roles_are_inferred_and_no_spurious_sameas():
    g = _reasoned()
    assert {"Company", "Developer"} <= _types(g, "Dev1")
    assert "Publisher" not in _types(g, "Dev1")
    assert not [t for t in g.subject_objects(OWL.sameAs) if t[0] != t[1]]
    assert (VG.Dev1, VG.developerOf, VG.GameA) in g and (VG.GameA, VG.sharesDeveloperWith, VG.GameC) in g
