"""
Caches for the application:
  - "label:" node labels by URI — in-memory only (derived from the in-memory RDF store)
  - "type:"  node types by URI  — in-memory only

Public API:
    from backend.services.image_cache import get_label, set_label   # sync
    from backend.services.image_cache import get_type, set_type     # sync
"""

_local_label: dict[str, str] = {}
_local_type: dict[str, str] = {}


# ── Label cache (sync, in-memory only) ───────────────────────────────────────
# Labels are derived from the in-memory RDF graph on first access and cached locally.
# Not persisted: the data is already available in-memory and labels are static.


def get_label(uri: str) -> str | None:
    return _local_label.get(uri)


def set_label(uri: str, label: str) -> None:
    _local_label[uri] = label


# ── Type cache (sync, in-memory only) ────────────────────────────────────────


def get_type(uri: str) -> str | None:
    return _local_type.get(uri)


def set_type(uri: str, node_type: str) -> None:
    _local_type[uri] = node_type
