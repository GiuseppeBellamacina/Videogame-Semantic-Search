"""Company model: a developer and a publisher with the same name are ONE individual with both roles.
Synthetic graph only, no Wikidata and no build (uv run pytest ontology/scripts)."""

import enrich_owl as eo
import owlrl
import populate_wikidata as pw
import schema_loader
import validate_tbox as vt
from rdflib import OWL, RDF, Graph, Literal, URIRef

VG = pw.VG


def _graph() -> Graph:
    g = Graph()
    dev, pub = VG["dev/FromSoftware"], VG["pub/FromSoftware"]
    g.add((dev, RDF.type, VG.Developer))
    g.add((dev, VG.developerName, Literal("FromSoftware")))
    g.add((pub, RDF.type, VG.Publisher))
    g.add((pub, VG.publisherName, Literal("FromSoftware, Inc.")))  # same company after normalisation
    g.add((VG.GameA, VG.developedBy, dev))
    g.add((VG.GameB, VG.publishedBy, pub))
    return g


def test_same_name_developer_and_publisher_become_one_company():
    g = _graph()
    assert pw.deduplicate_graph(g) == 1
    companies = {s for s in g.subjects(RDF.type, VG.Developer)} & {s for s in g.subjects(RDF.type, VG.Publisher)}
    assert len(companies) == 1
    (c,) = companies
    assert (c, VG.developerName, None) in g and (c, VG.publisherName, None) in g
    assert (VG.GameA, VG.developedBy, c) in g and (VG.GameB, VG.publishedBy, c) in g


def test_declared_nominal_wins_over_a_variant_with_more_triples():
    g = Graph()
    nominal, variant = VG["pub/Nintendo"], VG["dev/Nintendo_Co_Ltd"]
    g.add((nominal, RDF.type, OWL.NamedIndividual))
    g.add((nominal, RDF.type, VG.Publisher))
    g.add((nominal, VG.publisherName, Literal("Nintendo")))
    g.add((variant, RDF.type, VG.Developer))
    g.add((variant, VG.developerName, Literal("Nintendo Co., Ltd.")))
    for i in range(5):
        g.add((VG[f"g{i}"], VG.developedBy, variant))
    pw.deduplicate_graph(g)
    assert (VG["g0"], VG.developedBy, nominal) in g and (variant, None, None) not in g


def test_both_roles_are_consistent_under_the_schema_and_owlrl():
    g = schema_loader.load_tbox()
    eo.strip_dl_only_axioms(g)
    c = VG["dev/FromSoftware"]
    g.add((c, RDF.type, VG.Developer))
    g.add((c, RDF.type, VG.Publisher))  # both roles: used to be an inconsistency (disjoint)
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(g)
    assert (c, RDF.type, VG.Company) in g
    # owlrl reports an inconsistency (disjoint classes, ...) as agent-ont:error triples
    assert not list(g.triples((None, URIRef("http://www.daml.org/2002/03/agents/agent-ont#error"), None)))
    assert not vt.check_unsatisfiable_disjoint(schema_loader.load_tbox())


def test_developer_and_publisher_are_derived_from_the_roles():
    g = schema_loader.load_tbox()
    eo.strip_dl_only_axioms(g)
    c, game = VG["company/X"], VG["game/X"]
    g.add((c, RDF.type, VG.Company))
    g.add((game, RDF.type, VG.VideoGame))
    g.add((c, VG.developerOf, game))  # no asserted Developer type
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(g)
    assert (c, RDF.type, VG.Developer) in g
    assert (c, RDF.type, VG.Publisher) not in g  # only the roles it plays


def test_a_game_titled_like_a_schema_term_gets_its_own_iri():
    assert pw.make_uri(str(VG), "Platform") == VG["Platform_Game"]
    assert pw.make_uri(str(VG), "Elden Ring") == VG["Elden_Ring"]
    assert pw.make_uri(str(VG) + "dev/", "Platform") == VG["dev/Platform"]  # other namespaces are not affected
