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
}

NODE_SIZES = {
    "VideoGame": 12,
    "Developer": 8,
    "Publisher": 8,
    "Genre": 6,
    "Platform": 6,
    "Character": 5,
    "Franchise": 10,
    "Award": 7,
    "GameEngine": 7,
    "Unknown": 5,
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

    return {
        "nodes": list(nodes_map.values()),
        "links": links,
    }


def build_graph_from_node(uri: str, ontology_service: Any) -> dict:
    """
    Build a focused graph centered on a single node.
    Includes all directly connected nodes.
    """
    details = ontology_service.get_node_details(uri)
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

    return {
        "nodes": list(nodes_map.values()),
        "links": links,
    }


def _find_relationship(uri_a: str, uri_b: str, ontology_service: Any) -> str | None:
    """Check if there's a direct relationship between two URIs in the graph."""
    from rdflib import URIRef

    g = ontology_service.get_graph()
    node_a = URIRef(uri_a)
    node_b = URIRef(uri_b)

    # Check A -> B
    for s, p, o in g.triples((node_a, None, node_b)):
        local = str(p).split("#")[-1] if "#" in str(p) else str(p).split("/")[-1]
        if local != "type":
            return local

    # Check B -> A
    for s, p, o in g.triples((node_b, None, node_a)):
        local = str(p).split("#")[-1] if "#" in str(p) else str(p).split("/")[-1]
        if local != "type":
            return local

    return None
