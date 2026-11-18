"""Self-check of the two OWL 2 DL checks of validate_tbox.py (uv run pytest ontology/scripts)."""

from rdflib import OWL, RDF, RDFS, Graph, URIRef

import validate_tbox as v


def test_non_simple_property_with_asymmetry_is_an_error():
    g, p, q = Graph(), URIRef("http://x/p"), URIRef("http://x/q")
    g.add((p, RDF.type, OWL.TransitiveProperty))
    g.add((p, RDF.type, OWL.AsymmetricProperty))
    g.add((p, OWL.inverseOf, q))  # the inverse of a transitive property is not simple either
    g.add((q, RDF.type, OWL.FunctionalProperty))
    assert [f.code for f in v.check_global_restrictions(g)] == ["NON_SIMPLE_PROPERTY_AXIOM"] * 2


def test_xsd_date_is_outside_the_datatype_map():
    g, d = Graph(), URIRef("http://x/d")
    g.add((d, RDF.type, OWL.DatatypeProperty))
    g.add((d, RDFS.range, URIRef("http://www.w3.org/2001/XMLSchema#date")))
    assert [f.code for f in v.check_owl2_datatypes(g)] == ["DATATYPE_OUTSIDE_OWL2_MAP"]
