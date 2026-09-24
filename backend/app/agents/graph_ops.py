"""Shared knowledge-graph write helpers.

Single implementation of "find-or-create an entity node" and "add an
evidence-backed candidate relationship", used by BOTH the free-text extraction
path (`api/evidence.py::_materialise`) and the structured-data parsers
(`agents/parsers.py`). Guarantees that a phone discovered in a CDR CSV and the
same phone discovered in an intelligence note land on the same node.
"""
from __future__ import annotations

from typing import Any, Optional

from ..config import DATA_CLASSIFICATION
from ..database.neo4j_graph import graph_store

TYPE_PREFIX = {
    "PERSON": "PER", "ALIAS": "PER", "VEHICLE": "VEH", "PHONE": "PHN",
    "ACCOUNT": "ACC", "LOCATION": "LOC", "ORGANIZATION": "ORG", "DEVICE": "DEV",
}

_PERSON_LIKE = {"PERSON", "ALIAS"}


def _type_set(entity_type: str) -> set[str]:
    return _PERSON_LIKE if entity_type in _PERSON_LIKE else {entity_type}


_IDENTIFIER_TYPES = {"PHONE", "ACCOUNT", "VEHICLE"}


def match_key(entity_type: str, value: str) -> str:
    """Type-aware identity key for node matching.

    Identifiers must compare on their canonical content, not their formatting:
    the seeded graph labels accounts "A/C 33901122" while a parsed bank statement
    yields "33901122". Comparing raw strings created a duplicate ACC node for an
    account that already existed, which would silently split transaction history.
    """
    value = (value or "").strip()
    if entity_type == "PHONE":
        digits = "".join(ch for ch in value if ch.isdigit())
        return digits[-10:] if digits else ""
    if entity_type == "ACCOUNT":
        digits = "".join(ch for ch in value if ch.isdigit())
        return digits
    if entity_type == "VEHICLE":
        return "".join(ch for ch in value.upper() if ch.isalnum())
    return value.upper()


def find_entity_node(entity_type: str, normalized: str) -> Optional[dict[str, Any]]:
    """Locate an existing node by entity type + canonical identity key, checking
    both the normalized value and the display label."""
    target = match_key(entity_type, normalized)
    if not target:
        return None
    for node in graph_store.nodes():
        if node.get("entity_type") not in _type_set(entity_type):
            continue
        candidates = {match_key(entity_type, node.get("normalized") or ""),
                      match_key(entity_type, node.get("label") or "")}
        if target in candidates - {""}:
            return node
    return None


def ensure_entity_node(entity_type: str, surface: str, normalized: str, case_id: str,
                       evidence_id: str, attributes: Optional[dict[str, Any]] = None,
                       lat: Optional[float] = None, lon: Optional[float] = None,
                       label_override: Optional[str] = None) -> tuple[str, bool]:
    """Return (node_id, created). Extends an existing node's case/evidence sets
    rather than duplicating it."""
    match = find_entity_node(entity_type, normalized)
    if match:
        node_id = match["id"]
        graph_store.update_node(node_id, {
            "cases": sorted(set((match.get("cases") or []) + [case_id])),
            "evidence_ids": sorted(set((match.get("evidence_ids") or []) + [evidence_id])),
        })
        if lat is not None and match.get("lat") is None:
            graph_store.update_node(node_id, {"lat": lat, "lon": lon})
        return node_id, False

    prefix = TYPE_PREFIX[entity_type]
    seq = sum(1 for n in graph_store.nodes() if n.get("entity_type") == entity_type) + 1
    node_id = f"{prefix}-X{seq:03d}"
    while graph_store.node(node_id):
        seq += 1
        node_id = f"{prefix}-X{seq:03d}"
    graph_store.merge_node(node_id, [entity_type], {
        "entity_id": node_id, "entity_type": entity_type,
        "label": label_override or surface, "normalized": (normalized or "").upper(),
        "cases": [case_id], "attributes": attributes or {},
        "evidence_ids": [evidence_id], "verification_status": "UNVERIFIED",
        "support_level": "LOW", "lat": lat, "lon": lon,
        "classification": DATA_CLASSIFICATION,
    })
    return node_id, True


def link(src: str, tgt: str, rel_type: str, ts: str, evidence_id: str, case_id: str,
         support_level: str = "LOW", notes: str = "",
         relation_id: Optional[str] = None) -> Optional[str]:
    """Add an evidence-backed candidate relationship. Returns the relationship id,
    or None if it already existed. Every relationship carries its evidence id."""
    if not src or not tgt or src == tgt:
        return None
    rel_id = relation_id or f"REL-X-{evidence_id}-{src}-{tgt}-{rel_type}"
    if graph_store.relationship(rel_id):
        return None
    graph_store.merge_relationship(rel_id, src, tgt, rel_type, {
        "relationship_id": rel_id, "rel_type": rel_type, "timestamp": ts,
        "evidence_id": evidence_id, "case_id": case_id, "support_level": support_level,
        "verification_status": "UNVERIFIED", "source_document": "Structured data parser",
        "notes": notes or "Candidate relationship derived from structured evidence.",
        "classification": DATA_CLASSIFICATION,
    })
    return rel_id
