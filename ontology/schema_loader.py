"""Load the schema: videogames.owl only declares owl:imports of the modules in
schema/; rdflib does not follow imports, so resolve them through the Protégé
catalog (catalog-v001.xml) and merge everything into one graph."""

import xml.etree.ElementTree as ET
from pathlib import Path

from rdflib import OWL, Graph

HERE = Path(__file__).parent
ROOT = HERE / "videogames.owl"
MODULES_DIR = HERE / "schema"


def _catalog(root: Path) -> dict[str, Path]:
    cat = root.parent / "catalog-v001.xml"
    if not cat.exists():
        return {}
    return {
        e.get("name"): root.parent / e.get("uri")
        for e in ET.parse(cat).getroot()
        if e.tag.endswith("uri")
    }


def load_tbox(root: Path = ROOT) -> Graph:
    """The root ontology plus every module it imports (recursively)."""
    iris = _catalog(root)
    g = Graph().parse(str(root))
    done: set[str] = set()
    pending = [str(o) for o in g.objects(None, OWL.imports)]
    while pending:
        iri = pending.pop()
        if iri in done:
            continue
        done.add(iri)
        path = iris.get(iri)
        if path is None:
            raise FileNotFoundError(f"owl:imports {iri} is not in catalog-v001.xml")
        m = Graph().parse(str(path))
        g += m
        pending += [str(o) for o in m.objects(None, OWL.imports)]
    return g


def module_files(root: Path = ROOT) -> list[Path]:
    """Module files in import order (the order of the root's owl:imports is the
    order in the catalog, which is the order used for the Turtle copy)."""
    return list(_catalog(root).values())
