"""
Builds graph data (nodes + links) from SPARQL query results for the frontend
knowledge graph visualization.
"""

from typing import Any

# Color palette for node types
NODE_COLORS = {
    "VideoGame": "#6366f1",  # Indigo
    "Developer": "#f59e0b",  # Amber
    "Publisher": "#10b981",  # Emerald
    "Genre": "#ef4444",  # Red
    "Platform": "#3b82f6",  # Blue
    "Character": "#ec4899",  # Pink
    "Franchise": "#8b5cf6",  # Violet
    "Award": "#f97316",  # Orange
    "GameEngine": "#14b8a6",  # Teal
    "Unknown": "#6b7280",  # Gray
    # Defined subclasses — same colour as VideoGame
    "AwardWinningGame": "#6366f1",
    "FranchiseGame": "#6366f1",
}

NODE_SIZES = {
    "VideoGame": 9,
    "Developer": 8,
    "Publisher": 8,
    "Genre": 6,
    "Platform": 6,
    "Character": 5,
    "Franchise": 10,
    "Award": 7,
    "GameEngine": 7,
    "Unknown": 5,
    # Defined subclasses — same size as VideoGame
    "AwardWinningGame": 9,
    "FranchiseGame": 9,
}


def build_graph_from_results(
    results: list[dict],
    ontology_service: Any,
) -> dict:
    """
    Build a graph structure from SPARQL results.

    Analyzes the result rows to identify entities (URIs) and their relationships,
    then constructs nodes and links for force-graph visualization.

    Returns:
        {
            "nodes": [{"id": uri, "label": name, "type": class, "color": hex, "size": int, "properties": {}}],
            "links": [{"source": uri, "target": uri, "label": predicate}]
        }
    """
    nodes_map: dict[str, dict] = {}
    links: list[dict] = []

    for row in results:
        uris_in_row = []

        for key, value in row.items():
            if value and value.startswith("http://www.videogame-ontology.org/"):
                uri = value
                if uri not in nodes_map:
                    node_type = ontology_service._get_node_type(uri)
                    node_label = ontology_service._get_node_label(uri)
                    node_data = {
                        "id": uri,
                        "label": node_label,
                        "type": node_type,
                        "color": NODE_COLORS.get(node_type, NODE_COLORS["Unknown"]),
                        "size": NODE_SIZES.get(node_type, NODE_SIZES["Unknown"]),
                    }
                    nodes_map[uri] = node_data
                uris_in_row.append((key, uri))

        # Create links between entities found in the same result row
        # by checking actual ontology relationships
        for i, (key_a, uri_a) in enumerate(uris_in_row):
            for key_b, uri_b in uris_in_row[i + 1 :]:
                if uri_a == uri_b:
                    continue
                # Check if there's an actual relationship
                rel = _find_relationship(uri_a, uri_b, ontology_service)
                if rel:
                    # Avoid duplicate links
                    if not any(
                        link["source"] == uri_a
                        and link["target"] == uri_b
                        and link["label"] == rel
                        for link in links
                    ):
                        links.append(
                            {
                                "source": uri_a,
                                "target": uri_b,
                                "label": rel,
                            }
                        )

    # Cross-link pass: find relationships between nodes that appeared in
    # different rows (e.g. two games sharing a franchise node each returned
    # in separate rows — they still have sharedFranchiseWith between them).
    existing_link_keys: set[tuple] = {
        (lnk["source"], lnk["target"], lnk["label"]) for lnk in links
    }
    all_uris = list(nodes_map.keys())
    if len(all_uris) > 1:
        cross = find_cross_links(
            existing_uris=[],
            new_uris=all_uris,
            ontology_service=ontology_service,
        )
        for lnk in cross:
            key = (lnk["source"], lnk["target"], lnk["label"])
            rev = (lnk["target"], lnk["source"], lnk["label"])
            if key not in existing_link_keys and rev not in existing_link_keys:
                existing_link_keys.add(key)
                links.append(lnk)

    return {
        "nodes": list(nodes_map.values()),
        "links": links,
    }


def build_graph_from_node(
    uri: str, ontology_service: Any, max_relations: int = 50
) -> dict:
    """
    Build a focused graph centered on a single node.
    Includes directly connected nodes (limited to prevent memory issues).
    """
    details = ontology_service.get_node_details(uri, max_relations=max_relations)
    nodes_map: dict[str, dict] = {}
    links: list[dict] = []

    # Add center node
    center_type = details["type"]
    nodes_map[uri] = {
        "id": uri,
        "label": details["label"],
        "type": center_type,
        "color": NODE_COLORS.get(center_type, NODE_COLORS["Unknown"]),
        "size": NODE_SIZES.get(center_type, NODE_SIZES["Unknown"])
        + 4,  # larger for center
    }

    # Add outgoing relations
    for rel in details["outgoing_relations"]:
        target_uri = rel["target_uri"]
        target_type = rel["target_type"]
        if target_uri not in nodes_map:
            nodes_map[target_uri] = {
                "id": target_uri,
                "label": rel["target_label"],
                "type": target_type,
                "color": NODE_COLORS.get(target_type, NODE_COLORS["Unknown"]),
                "size": NODE_SIZES.get(target_type, NODE_SIZES["Unknown"]),
            }
        links.append(
            {
                "source": uri,
                "target": target_uri,
                "label": rel["predicate"],
            }
        )

    # Add incoming relations
    for rel in details["incoming_relations"]:
        source_uri = rel["source_uri"]
        source_type = rel["source_type"]
        if source_uri not in nodes_map:
            nodes_map[source_uri] = {
                "id": source_uri,
                "label": rel["source_label"],
                "type": source_type,
                "color": NODE_COLORS.get(source_type, NODE_COLORS["Unknown"]),
                "size": NODE_SIZES.get(source_type, NODE_SIZES["Unknown"]),
            }
        links.append(
            {
                "source": source_uri,
                "target": uri,
                "label": rel["predicate"],
            }
        )

    # Discover cross-links between neighbor nodes (e.g. sharedFranchiseWith,
    # sharesDeveloperWith between two games already in the graph).
    neighbor_uris = [u for u in nodes_map if u != uri]
    if neighbor_uris:
        cross = find_cross_links(
            existing_uris=[uri],
            new_uris=neighbor_uris,
            ontology_service=ontology_service,
        )
        for lnk in cross:
            # Skip center→neighbor / neighbor→center links already added above
            is_center_link = lnk["source"] == uri or lnk["target"] == uri
            if not is_center_link:
                dup = any(
                    ll["source"] == lnk["source"]
                    and ll["target"] == lnk["target"]
                    and ll["label"] == lnk["label"]
                    for ll in links
                )
                if not dup:
                    links.append(lnk)

    return {
        "nodes": list(nodes_map.values()),
        "links": links,
    }


def _find_relationship(uri_a: str, uri_b: str, ontology_service: Any) -> str | None:
    """Check if there's a direct relationship between two URIs in the graph."""
    import pyoxigraph as ox

    store = ontology_service.get_store()
    node_a = ox.NamedNode(uri_a)
    node_b = ox.NamedNode(uri_b)

    # Check A -> B
    for quad in store.quads_for_pattern(node_a, None, node_b):
        local = (
            quad.predicate.value.split("#")[-1]
            if "#" in quad.predicate.value
            else quad.predicate.value.split("/")[-1]
        )
        if local != "type":
            return local

    # Check B -> A
    for quad in store.quads_for_pattern(node_b, None, node_a):
        local = (
            quad.predicate.value.split("#")[-1]
            if "#" in quad.predicate.value
            else quad.predicate.value.split("/")[-1]
        )
        if local != "type":
            return local

    return None


def find_cross_links(
    existing_uris: list[str],
    new_uris: list[str],
    ontology_service: Any,
) -> list[dict]:
    """
    Find all direct relationships between new_uris and (existing_uris ∪ new_uris).

    Efficient: for each new URI, iterates only its actual triples in the store and
    checks if the connected node belongs to the known URI sets. O(new × avg_degree).
    """
    import pyoxigraph as ox

    store = ontology_service.get_store()
    existing_set = set(existing_uris)
    new_set = set(new_uris)
    all_set = existing_set | new_set

    _SKIP_PREDS = {"type", "label", "subClassOf", "sameAs", "equivalentClass"}

    links: list[dict] = []
    seen: set[tuple] = set()

    def _local(pred_value: str) -> str:
        return (
            pred_value.split("#")[-1]
            if "#" in pred_value
            else pred_value.split("/")[-1]
        )

    for uri in new_uris:
        node = ox.NamedNode(uri)

        # Outgoing: uri → target
        for quad in store.quads_for_pattern(node, None, None):
            if not isinstance(quad.object, ox.NamedNode):
                continue
            target = quad.object.value
            if target not in all_set or target == uri:
                continue
            pred = _local(quad.predicate.value)
            if pred in _SKIP_PREDS:
                continue
            key = (uri, target, pred)
            rev = (target, uri, pred)
            if key not in seen and rev not in seen:
                seen.add(key)
                links.append({"source": uri, "target": target, "label": pred})

        # Incoming: source → uri
        for quad in store.quads_for_pattern(None, None, node):
            if not isinstance(quad.subject, ox.NamedNode):
                continue
            source = quad.subject.value
            if source not in all_set or source == uri:
                continue
            pred = _local(quad.predicate.value)
            if pred in _SKIP_PREDS:
                continue
            key = (source, uri, pred)
            rev = (uri, source, pred)
            if key not in seen and rev not in seen:
                seen.add(key)
                links.append({"source": source, "target": uri, "label": pred})

    return links
