"""
TBox (schema) validator for the videogame ontology.

Checks the ontology schema for well-formedness and consistency:
  - Dangling references to undeclared classes/properties
  - Unsatisfiable classes due to disjointness conflicts
  - Circular subclass hierarchies
  - Inverse property consistency
  - Mutually exclusive property type conflicts
  - Missing domain/range, labels, unused classes
  - Restriction completeness and datatype restriction syntax

Usage
-----
    uv run python validate_tbox.py ../videogames.owl
    uv run python validate_tbox.py ../videogames.owl --strict
    uv run python validate_tbox.py ../videogames.owl --report report.json
    uv run python validate_tbox.py ../videogames.owl -v
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from rdflib import OWL, RDF, RDFS, BNode, Graph, Literal, Namespace, URIRef
from rdflib.namespace import XSD

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VG = Namespace("http://www.videogame-ontology.org/ontology#")

KNOWN_TYPES = {OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty}

ENTITY_TYPES = {
    OWL.Class,
    OWL.ObjectProperty,
    OWL.DatatypeProperty,
    OWL.Restriction,
}

REFERENCE_PREDICATES = {
    RDFS.subClassOf,
    RDFS.domain,
    RDFS.range,
    OWL.inverseOf,
    OWL.equivalentClass,
    OWL.onProperty,
    OWL.someValuesFrom,
    OWL.allValuesFrom,
    OWL.hasValue,
    OWL.hasKey,
    OWL.members,
}

MUTUALLY_EXCLUSIVE_PROPERTY_PAIRS = [
    (OWL.SymmetricProperty, OWL.AsymmetricProperty),
    (OWL.ReflexiveProperty, OWL.IrreflexiveProperty),
]

RESTRICTION_VALUE_PREDICATES = {
    OWL.someValuesFrom,
    OWL.allValuesFrom,
    OWL.hasValue,
    OWL.cardinality,
    OWL.minCardinality,
    OWL.maxCardinality,
    OWL.qualifiedCardinality,
}

# Symmetric chain-inferred properties — exclude from missing domain/range
SYMMETRIC_CHAIN_PROPERTIES = {
    VG.sharedFranchiseWith,
    VG.sharesDeveloperWith,
    VG.sharesPublisherWith,
}

KNOWN_TOP_LEVEL_CLASSES = {
    VG.VideoGame,
    VG.Developer,
    VG.Publisher,
    VG.Genre,
    VG.Platform,
    VG.Character,
    VG.Franchise,
    VG.Award,
    VG.GameEngine,
    VG.AwardWinningGame,
    VG.FranchiseGame,
}

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    """A single validation finding (error, warning, or info)."""

    severity: str  # "ERROR" | "WARNING" | "INFO"
    code: str  # short code e.g. "DANGLING_DOMAIN"
    message: str  # human-readable
    subjects: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def _short(uri: URIRef | BNode) -> str:
    """Return a compact representation of a URI or blank node."""
    if isinstance(uri, BNode):
        return str(uri)
    if str(uri).startswith(str(VG)):
        return "vg:" + str(uri)[len(str(VG)) :]
    return uri.n3()


def _is_vg_entity(uri: URIRef) -> bool:
    """Check whether a URI belongs to the videogame ontology namespace."""
    return str(uri).startswith(str(VG))


# ---------------------------------------------------------------------------
# Graph loading
# ---------------------------------------------------------------------------


def load_graph(path: Path) -> Graph:
    """Load an RDF graph with auto-detected format (xml, turtle, nt)."""
    suffix = path.suffix.lower()
    fmt_map: dict[str, str] = {
        ".owl": "xml",
        ".rdf": "xml",
        ".ttl": "turtle",
        ".nt": "nt",
        ".n3": "n3",
    }
    fmt = fmt_map.get(suffix)
    g = Graph()
    g.bind("vg", VG)
    g.bind("owl", OWL)
    g.parse(str(path), format=fmt)
    logger.info("Loaded %d triples from %s", len(g), path.name)
    return g


# ---------------------------------------------------------------------------
# Utility: collect declared entities
# ---------------------------------------------------------------------------

# Type aliases for clarity
_EntitySet = set[URIRef]
_DeclaredMap = dict[URIRef, set[URIRef]]  # URI → types (e.g. {owl:Class})


def _collect_declared_entities(g: Graph) -> tuple[_EntitySet, _EntitySet]:
    """Return (classes, properties) declared in the ontology namespace.

    Classes = URIs with rdf:type owl:Class (or subclasses via rdfs:subClassOf).
    Properties = URIs with rdf:type owl:ObjectProperty or owl:DatatypeProperty.
    Only includes entities in the VG namespace.
    """
    declared_classes: _EntitySet = set()
    declared_properties: _EntitySet = set()

    for s, _, o in g.triples((None, RDF.type, None)):
        if not isinstance(s, URIRef):
            continue
        if not _is_vg_entity(s):
            continue
        if o in {OWL.Class}:
            declared_classes.add(s)
        elif o in {OWL.ObjectProperty, OWL.DatatypeProperty}:
            declared_properties.add(s)

    return declared_classes, declared_properties


def _collect_all_declared(g: Graph) -> _EntitySet:
    """Return the union of all declared classes + properties in VG namespace."""
    classes, props = _collect_declared_entities(g)
    return classes | props


# ---------------------------------------------------------------------------
# Traversal helpers
# ---------------------------------------------------------------------------


def _transitive_superclasses(g: Graph, cls: URIRef) -> set[URIRef]:
    """Return the set of all superclasses (transitive closure) of *cls*."""
    result: set[URIRef] = set()
    queue = deque([cls])
    while queue:
        current = queue.popleft()
        for _, _, parent in g.triples((current, RDFS.subClassOf, None)):
            if isinstance(parent, URIRef) and parent not in result:
                result.add(parent)
                queue.append(parent)
    return result


def _all_subclasses(g: Graph, cls: URIRef) -> set[URIRef]:
    """Return the set of all classes that are (transitively) subclasses of *cls*."""
    result: set[URIRef] = set()
    queue = deque([cls])
    while queue:
        current = queue.popleft()
        for child, _, _ in g.triples((None, RDFS.subClassOf, current)):
            if isinstance(child, URIRef) and child not in result:
                result.add(child)
                queue.append(child)
    return result


# ---------------------------------------------------------------------------
# Check 1 — Dangling references
# ---------------------------------------------------------------------------


def check_dangling_references(g: Graph) -> list[Finding]:
    """ERROR: every object of a reference predicate must resolve to a declared entity
    or be a blank node (restrictions are allowed as blank nodes)."""
    findings: list[Finding] = []
    declared = _collect_all_declared(g)

    for s, p, o in g.triples((None, None, None)):
        if p not in REFERENCE_PREDICATES:
            continue
        if not isinstance(o, URIRef):
            continue  # blank nodes and literals are fine
        if not _is_vg_entity(o):
            continue  # external references (XSD, rdf, etc.) are fine
        if o not in declared:
            findings.append(
                Finding(
                    severity="ERROR",
                    code="DANGLING_REFERENCE",
                    message=(
                        f"{_short(p)} points to {_short(o)} "
                        f"which is not declared as owl:Class, "
                        f"owl:ObjectProperty, or owl:DatatypeProperty"
                    ),
                    subjects=[_short(s), _short(p), _short(o)],
                )
            )

    return findings


# ---------------------------------------------------------------------------
# Check 2 — Unsatisfiable disjoint classes
# ---------------------------------------------------------------------------


def check_unsatisfiable_disjoint(g: Graph) -> list[Finding]:
    """ERROR: a class that is subclass of both A and B where A and B are disjoint."""
    findings: list[Finding] = []

    # ── Build disjoint pairs set ──
    disjoint_pairs: set[tuple[URIRef, URIRef]] = set()

    # 2a: owl:AllDisjointClass → expand pairwise
    for adc, _, _ in g.triples((None, RDF.type, OWL.AllDisjointClasses)):
        members: list[URIRef] = []
        # Walk the rdf:List of owl:members
        member_node = g.value(adc, OWL.members)
        while member_node and member_node != RDF.nil:
            item = g.value(member_node, RDF.first)
            if isinstance(item, URIRef):
                members.append(item)
            member_node = g.value(member_node, RDF.rest)

        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                a, b = members[i], members[j]
                disjoint_pairs.add((a, b))
                disjoint_pairs.add((b, a))

    # 2b: owl:disjointWith
    for s, _, o in g.triples((None, OWL.disjointWith, None)):
        if isinstance(s, URIRef) and isinstance(o, URIRef):
            disjoint_pairs.add((s, o))
            disjoint_pairs.add((o, s))

    if not disjoint_pairs:
        return findings

    # ── For each class C, check if any two disjoint superclasses include C ──
    classes, _ = _collect_declared_entities(g)
    for cls in sorted(classes, key=str):
        supers = _transitive_superclasses(g, cls)
        if not supers:
            continue
        supers_list = list(supers)
        for i in range(len(supers_list)):
            for j in range(i + 1, len(supers_list)):
                a, b = supers_list[i], supers_list[j]
                if (a, b) in disjoint_pairs:
                    findings.append(
                        Finding(
                            severity="ERROR",
                            code="UNSATISFIABLE_DISJOINT",
                            message=(
                                f"{_short(cls)} is subclass of both "
                                f"{_short(a)} and {_short(b)} "
                                f"which are declared disjoint"
                            ),
                            subjects=[_short(cls), _short(a), _short(b)],
                        )
                    )

    return findings


# ---------------------------------------------------------------------------
# Check 3 — Circular subclass hierarchy
# ---------------------------------------------------------------------------


def check_circular_subclass(g: Graph) -> list[Finding]:
    """ERROR: cycles in the rdfs:subClassOf graph."""
    findings: list[Finding] = []

    # Build adjacency and in-degree map
    adj: dict[URIRef, list[URIRef]] = defaultdict(list)
    nodes: set[URIRef] = set()

    for s, _, o in g.triples((None, RDFS.subClassOf, None)):
        if isinstance(s, URIRef) and isinstance(o, URIRef):
            if not _is_vg_entity(s) and not _is_vg_entity(o):
                continue
            adj.setdefault(s, []).append(o)
            nodes.add(s)
            nodes.add(o)

    # Check direct self-loops
    for s, _, o in g.triples((None, RDFS.subClassOf, None)):
        if s == o and isinstance(s, URIRef):
            findings.append(
                Finding(
                    severity="ERROR",
                    code="CIRCULAR_SUBCLASS",
                    message=f"{_short(s)} is a subclass of itself",
                    subjects=[_short(s)],
                )
            )

    # DFS-based cycle detection using white/gray/black coloring
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[URIRef, int] = {n: WHITE for n in nodes}

    def dfs(u: URIRef, path: list[URIRef]) -> None:
        color[u] = GRAY
        path.append(u)
        for v in adj.get(u, []):
            if v not in color:
                color[v] = WHITE
            if color[v] == GRAY:
                # Found cycle: extract from path
                cycle_start = path.index(v)
                cycle = path[cycle_start:]
                findings.append(
                    Finding(
                        severity="ERROR",
                        code="CIRCULAR_SUBCLASS",
                        message=(
                            f"Circular subclass chain: "
                            f"{' → '.join(_short(n) for n in cycle)}"
                        ),
                        subjects=[_short(n) for n in cycle],
                    )
                )
            elif color[v] == WHITE:
                dfs(v, path)
        path.pop()
        color[u] = BLACK

    for node in list(nodes):
        if color.get(node, WHITE) == WHITE:
            dfs(node, [])

    return findings


# ---------------------------------------------------------------------------
# Check 4 — Inverse consistency
# ---------------------------------------------------------------------------


def check_inverse_consistency(g: Graph) -> list[Finding]:
    """Check owl:inverseOf consistency and Symmetric/Asymmetric conflicts."""
    findings: list[Finding] = []

    # 4a: inverseOf bidirectional check (WARNING if A → B declared but B → A not)
    inverse_map: dict[URIRef, URIRef] = {}
    for s, _, o in g.triples((None, OWL.inverseOf, None)):
        if isinstance(s, URIRef) and isinstance(o, URIRef):
            inverse_map[s] = o

    for a, b in inverse_map.items():
        # Check that b inverseOf a is also declared
        if b in inverse_map:
            if inverse_map[b] != a:
                findings.append(
                    Finding(
                        severity="WARNING",
                        code="INVERSE_MISMATCH",
                        message=(
                            f"{_short(a)} owl:inverseOf {_short(b)} "
                            f"but {_short(b)} owl:inverseOf {_short(inverse_map[b])}"
                        ),
                        subjects=[_short(a), _short(b), _short(inverse_map[b])],
                    )
                )
        else:
            findings.append(
                Finding(
                    severity="WARNING",
                    code="INVERSE_NOT_BIDIRECTIONAL",
                    message=(
                        f"{_short(a)} owl:inverseOf {_short(b)} "
                        f"but {_short(b)} owl:inverseOf {_short(a)} is not declared"
                    ),
                    subjects=[_short(a), _short(b)],
                )
            )

    # 4b: Symmetric + Asymmetric conflict (ERROR)
    for s, types, _ in g.triples((None, RDF.type, None)):
        if not isinstance(s, URIRef):
            continue
        if not _is_vg_entity(s):
            continue

    # Better: iterate over property URIs
    _, props = _collect_declared_entities(g)
    for prop in props:
        types = set(g.objects(prop, RDF.type))
        if OWL.SymmetricProperty in types and OWL.AsymmetricProperty in types:
            findings.append(
                Finding(
                    severity="ERROR",
                    code="SYMMETRIC_ASYMMETRIC_CONFLICT",
                    message=(
                        f"{_short(prop)} is declared both SymmetricProperty "
                        f"and AsymmetricProperty"
                    ),
                    subjects=[_short(prop)],
                )
            )

    return findings


# ---------------------------------------------------------------------------
# Check 5 — Property type conflicts
# ---------------------------------------------------------------------------


def check_property_type_conflict(g: Graph) -> list[Finding]:
    """ERROR: mutually exclusive property types (Symmetric/Asymmetric,
    Reflexive/Irreflexive)."""
    findings: list[Finding] = []

    _, props = _collect_declared_entities(g)

    for prop in props:
        types = set(g.objects(prop, RDF.type))
        for left, right in MUTUALLY_EXCLUSIVE_PROPERTY_PAIRS:
            if left in types and right in types:
                left_name = left.split("#")[-1]
                right_name = right.split("#")[-1]
                findings.append(
                    Finding(
                        severity="ERROR",
                        code="PROPERTY_TYPE_CONFLICT",
                        message=(
                            f"{_short(prop)} is declared both "
                            f"{left_name} and {right_name}"
                        ),
                        subjects=[_short(prop)],
                    )
                )

    return findings


# ---------------------------------------------------------------------------
# Check 6 — Missing domain/range (WARNING)
# ---------------------------------------------------------------------------


def check_missing_domain_range(g: Graph) -> list[Finding]:
    """WARNING: every owl:ObjectProperty / owl:DatatypeProperty should have
    both rdfs:domain and rdfs:range.

    Excludes symmetric chain-inferred properties (sharedFranchiseWith,
    sharesDeveloperWith, sharesPublisherWith) and inverse properties
    whose direct counterpart has domain/range (owlrl infers them).
    """
    findings: list[Finding] = []

    # Determine which properties are inverses of others (the "forward" ones)
    inverses: dict[URIRef, URIRef] = {}  # inverse → forward
    forward_props: set[URIRef] = set()
    for s, _, o in g.triples((None, OWL.inverseOf, None)):
        if isinstance(s, URIRef) and isinstance(o, URIRef):
            inverses[s] = o
            forward_props.add(o)

    _, props = _collect_declared_entities(g)
    for prop in sorted(props, key=str):
        # Skip symmetric chain properties
        if prop in SYMMETRIC_CHAIN_PROPERTIES:
            continue
        # Skip inverse properties: domain/range are inferred from forward
        if prop in inverses:
            continue

        has_domain = bool(list(g.objects(prop, RDFS.domain)))
        has_range = bool(list(g.objects(prop, RDFS.range)))

        if not has_domain:
            findings.append(
                Finding(
                    severity="WARNING",
                    code="MISSING_DOMAIN",
                    message=f"{_short(prop)} has no rdfs:domain",
                    subjects=[_short(prop)],
                )
            )
        if not has_range:
            findings.append(
                Finding(
                    severity="WARNING",
                    code="MISSING_RANGE",
                    message=f"{_short(prop)} has no rdfs:range",
                    subjects=[_short(prop)],
                )
            )

    return findings


# ---------------------------------------------------------------------------
# Check 7 — Missing labels (WARNING)
# ---------------------------------------------------------------------------


def check_missing_label(g: Graph) -> list[Finding]:
    """WARNING: every owl:Class, owl:ObjectProperty, owl:DatatypeProperty
    should have an rdfs:label."""
    findings: list[Finding] = []

    classes, props = _collect_declared_entities(g)

    for cls in sorted(classes, key=str):
        if not list(g.objects(cls, RDFS.label)):
            findings.append(
                Finding(
                    severity="WARNING",
                    code="MISSING_LABEL",
                    message=f"Class {_short(cls)} has no rdfs:label",
                    subjects=[_short(cls)],
                )
            )

    for prop in sorted(props, key=str):
        if not list(g.objects(prop, RDFS.label)):
            prop_type = "Property"
            findings.append(
                Finding(
                    severity="WARNING",
                    code="MISSING_LABEL",
                    message=f"Property {_short(prop)} has no rdfs:label",
                    subjects=[_short(prop)],
                )
            )

    return findings


# ---------------------------------------------------------------------------
# Check 8 — Unused classes (WARNING)
# ---------------------------------------------------------------------------


def check_unused_classes(g: Graph) -> list[Finding]:
    """WARNING: classes never referenced in any ontology construct.

    Excludes known top-level classes.
    """
    findings: list[Finding] = []

    classes, _ = _collect_declared_entities(g)

    # Collect all referenced URIs in constructs
    referenced: set[URIRef] = set()

    # Subclass relations
    for s, _, o in g.triples((None, RDFS.subClassOf, None)):
        if isinstance(s, URIRef):
            referenced.add(s)
        if isinstance(o, URIRef):
            referenced.add(o)

    # domain/range
    for p in (RDFS.domain, RDFS.range):
        for _, _, o in g.triples((None, p, None)):
            if isinstance(o, URIRef):
                referenced.add(o)

    # equivalentClass
    for _, _, o in g.triples((None, OWL.equivalentClass, None)):
        if isinstance(o, URIRef):
            referenced.add(o)

    # Restriction values
    for pred in RESTRICTION_VALUE_PREDICATES:
        for _, _, o in g.triples((None, pred, None)):
            if isinstance(o, URIRef):
                referenced.add(o)

    # disjointWith
    for s, _, o in g.triples((None, OWL.disjointWith, None)):
        if isinstance(s, URIRef):
            referenced.add(s)
        if isinstance(o, URIRef):
            referenced.add(o)

    # AllDisjointClass members
    for _, _, adc in g.triples((None, RDF.type, OWL.AllDisjointClasses)):
        member_node = g.value(adc, OWL.members)
        while member_node and member_node != RDF.nil:
            item = g.value(member_node, RDF.first)
            if isinstance(item, URIRef):
                referenced.add(item)
            member_node = g.value(member_node, RDF.rest)

    # hasKey
    for _, _, o in g.triples((None, OWL.hasKey, None)):
        if isinstance(o, URIRef):
            referenced.add(o)

    # onProperty
    for _, _, o in g.triples((None, OWL.onProperty, None)):
        if isinstance(o, URIRef):
            referenced.add(o)

    for cls in sorted(classes, key=str):
        if cls in KNOWN_TOP_LEVEL_CLASSES:
            continue
        if cls not in referenced:
            findings.append(
                Finding(
                    severity="WARNING",
                    code="UNUSED_CLASS",
                    message=(
                        f"Class {_short(cls)} is declared but never referenced "
                        f"in any construct"
                    ),
                    subjects=[_short(cls)],
                )
            )

    return findings


# ---------------------------------------------------------------------------
# Check 9 — Restriction completeness (ERROR/WARNING)
# ---------------------------------------------------------------------------


def check_restriction_completeness(g: Graph) -> list[Finding]:
    """Check that every owl:Restriction blank node has onProperty and at least
    one value/cardinality predicate.

    ERROR if missing onProperty; WARNING if missing value predicate.
    """
    findings: list[Finding] = []

    # Find all blank nodes used as restrictions (object of some construct or
    # directly typed as owl:Restriction)
    restriction_bnodes: set[BNode] = set()

    # Check explicit typing
    for bn, _, _ in g.triples((None, RDF.type, OWL.Restriction)):
        if isinstance(bn, BNode):
            restriction_bnodes.add(bn)

    # Also check blank nodes with onProperty (implicit restrictions)
    for bn, _, _ in g.triples((None, OWL.onProperty, None)):
        if isinstance(bn, BNode):
            restriction_bnodes.add(bn)

    for bn in sorted(restriction_bnodes, key=str):
        on_prop = list(g.objects(bn, OWL.onProperty))
        value_preds = [
            p
            for p in RESTRICTION_VALUE_PREDICATES
            if list(g.objects(bn, p))
        ]

        if not on_prop:
            # Try to find context (what contains this bnode)
            contexts = list(g.subjects(predicate=None, object=bn))
            ctx_strs = [_short(c) for c in contexts if isinstance(c, URIRef)]
            findings.append(
                Finding(
                    severity="ERROR",
                    code="RESTRICTION_MISSING_ONPROPERTY",
                    message=(
                        f"owl:Restriction blank node {bn} has no owl:onProperty"
                    ),
                    subjects=[f"_:{bn}", *ctx_strs],
                )
            )

        if on_prop and not value_preds:
            findings.append(
                Finding(
                    severity="WARNING",
                    code="RESTRICTION_MISSING_VALUE",
                    message=(
                        f"owl:Restriction blank node {bn} on {_short(on_prop[0])} "
                        f"has no someValuesFrom/allValuesFrom/hasValue/cardinality"
                    ),
                    subjects=[f"_:{bn}", _short(on_prop[0])],
                )
            )

    return findings


# ---------------------------------------------------------------------------
# Check 10 — Datatype restriction syntax (WARNING)
# ---------------------------------------------------------------------------


def check_datatype_restriction_syntax(g: Graph) -> list[Finding]:
    """WARNING: check syntax of datatype restrictions (owl:onDatatype +
    owl:withRestrictions RDF collection)."""
    findings: list[Finding] = []

    # Find blank nodes with owl:onProperty that point to datatype restrictions
    for bn, _, _ in g.triples((None, OWL.someValuesFrom, None)):
        # Check if the object is a blank node with owl:onDatatype or
        # owl:withRestrictions
        for _, svf_obj, _ in g.triples((bn, OWL.someValuesFrom, None)):
            if not isinstance(svf_obj, BNode):
                continue
            on_dt = list(g.objects(svf_obj, OWL.onDatatype))
            with_res = list(g.objects(svf_obj, OWL.withRestrictions))
            if on_dt or with_res:
                # This is a datatype restriction — verify syntax
                if not on_dt:
                    findings.append(
                        Finding(
                            severity="WARNING",
                            code="DATATYPE_REST_MISSING_ONDATATYPE",
                            message=(
                                f"Datatype restriction blank node "
                                f"{svf_obj} has owl:withRestrictions "
                                f"but no owl:onDatatype"
                            ),
                            subjects=[f"_:{svf_obj}", f"_:{bn}"],
                        )
                    )
                if not with_res:
                    findings.append(
                        Finding(
                            severity="WARNING",
                            code="DATATYPE_REST_MISSING_WITHRESTRICTIONS",
                            message=(
                                f"Datatype restriction blank node "
                                f"{svf_obj} has owl:onDatatype "
                                f"but no owl:withRestrictions"
                            ),
                            subjects=[f"_:{svf_obj}", f"_:{bn}"],
                        )
                    )
                # Also verify withRestrictions is an rdf:List
                if with_res:
                    rest_node = with_res[0]
                    if not isinstance(rest_node, BNode) and rest_node != RDF.nil:
                        findings.append(
                            Finding(
                                severity="WARNING",
                                code="DATATYPE_REST_BAD_LIST",
                                message=(
                                    f"owl:withRestrictions of {svf_obj} "
                                    f"is not an rdf:List"
                                ),
                                subjects=[f"_:{svf_obj}"],
                            )
                        )

    return findings


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def validate(g: Graph) -> list[Finding]:
    """Run all TBox checks on *g* and return a flat list of findings."""
    findings: list[Finding] = []

    checks: list[tuple[str, Callable[[Graph], list[Finding]]]] = [
        ("Dangling references", check_dangling_references),
        ("Unsatisfiable disjoint", check_unsatisfiable_disjoint),
        ("Circular subclass", check_circular_subclass),
        ("Inverse consistency", check_inverse_consistency),
        ("Property type conflict", check_property_type_conflict),
        ("Missing domain/range", check_missing_domain_range),
        ("Missing labels", check_missing_label),
        ("Unused classes", check_unused_classes),
        ("Restriction completeness", check_restriction_completeness),
        ("Datatype restriction syntax", check_datatype_restriction_syntax),
    ]

    for name, check_fn in checks:
        logger.info("Running check: %s", name)
        result = check_fn(g)
        findings.extend(result)
        logger.info("  → %d finding(s)", len(result))

    return findings


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------


def format_report(findings: list[Finding], file_path: str) -> str:
    """Format findings as a human-readable text report."""
    errors = [f for f in findings if f.severity == "ERROR"]
    warnings = [f for f in findings if f.severity == "WARNING"]
    infos = [f for f in findings if f.severity == "INFO"]

    lines: list[str] = []
    lines.append("=== TBox Validation Report ===")
    lines.append(f"File: {file_path}")
    lines.append(
        f"Total findings: {len(findings)} "
        f"(ERROR: {len(errors)}, WARNING: {len(warnings)}, INFO: {len(infos)})"
    )
    lines.append("")

    for f_finding in findings:
        lines.append(
            f"{f_finding.severity} [{f_finding.code}] {f_finding.message}"
        )
        if f_finding.subjects:
            lines.append(f"  subjects: {f_finding.subjects}")
        lines.append("")

    lines.append("=== Summary ===")
    lines.append(f"Errors: {len(errors)}")
    lines.append(f"Warnings: {len(warnings)}")
    result = "PASS" if len(errors) == 0 else "FAIL"
    lines.append(f"Result: {result}")

    return "\n".join(lines)


def to_json(findings: list[Finding], file_path: str) -> str:
    """Serialize findings as a JSON string."""
    errors = [f for f in findings if f.severity == "ERROR"]
    warnings = [f for f in findings if f.severity == "WARNING"]
    infos = [f for f in findings if f.severity == "INFO"]

    data = {
        "file": file_path,
        "findings": [asdict(f) for f in findings],
        "summary": {
            "errors": len(errors),
            "warnings": len(warnings),
            "info": len(infos),
        },
    }
    return json.dumps(data, indent=2)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate the TBox (schema) of a videogame OWL ontology."
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Path to the .owl file to validate",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Exit with code 2 if any WARNING is found "
            "(default: only ERROR exits non-zero)"
        ),
    )
    parser.add_argument(
        "--report",
        type=Path,
        metavar="PATH",
        help="Write JSON report to the given path",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose (debug-level) logging",
    )
    ns = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if ns.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s  %(message)s",
    )

    if not ns.input.exists():
        logger.error("File not found: %s", ns.input)
        sys.exit(1)

    g = load_graph(ns.input)
    findings = validate(g)

    # Print text report
    report_text = format_report(findings, str(ns.input))
    print(report_text)

    # Write JSON report if requested
    if ns.report:
        json_text = to_json(findings, str(ns.input))
        ns.report.write_text(json_text, encoding="utf-8")
        logger.info("JSON report written to %s", ns.report)

    # Exit codes
    errors = [f for f in findings if f.severity == "ERROR"]
    warnings = [f for f in findings if f.severity == "WARNING"]

    if errors:
        sys.exit(1)

    if ns.strict and warnings:
        sys.exit(2)

    sys.exit(0)


# ---------------------------------------------------------------------------
# Module-level logger
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    main()
