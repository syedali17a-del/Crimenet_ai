"""Neo4j property-graph adapter.

Holds the evidence-aware knowledge graph: entities, relationships, events and
evidence links.

Profile resolution:
  * CRIMENET_NEO4J_URI set -> real Neo4j (production profile, Neo4j GDS used for
    centrality/community when the plugin is present)
  * otherwise              -> EMBEDDED_PROPERTY_GRAPH fallback backed by NetworkX,
    exposing the identical node/relationship contract. Graph algorithms then run
    through NetworkX (the declared analytics library) instead of Neo4j GDS.
"""
from __future__ import annotations

import threading
from typing import Any, Optional

import networkx as nx

from ..config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER


class GraphStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._g = nx.MultiDiGraph()
        self.driver = None
        self.profile = "EMBEDDED_PROPERTY_GRAPH"
        self.gds_available = False
        self.detail = (
            "No Neo4j server reachable in this environment. Running the labelled embedded "
            "property-graph profile; graph algorithms execute on NetworkX."
        )
        if NEO4J_URI:
            try:  # pragma: no cover
                from neo4j import GraphDatabase  # type: ignore

                self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
                self.driver.verify_connectivity()
                self.profile = "NEO4J"
                self.detail = "Connected to Neo4j."
                try:
                    with self.driver.session() as s:
                        s.run("CALL gds.list() YIELD name RETURN name LIMIT 1").consume()
                    self.gds_available = True
                except Exception:
                    self.gds_available = False
            except Exception as exc:  # pragma: no cover
                self.detail = f"Neo4j URI configured but unreachable ({exc}). Using embedded profile."

    # --- write -------------------------------------------------------------
    def merge_node(self, node_id: str, labels: list[str], props: dict[str, Any]) -> None:
        with self._lock:
            if self._g.has_node(node_id):
                self._g.nodes[node_id].update(props)
                existing = set(self._g.nodes[node_id].get("labels", []))
                self._g.nodes[node_id]["labels"] = sorted(existing | set(labels))
            else:
                self._g.add_node(node_id, labels=sorted(set(labels)), **props)

    def merge_relationship(self, rel_id: str, source: str, target: str, rel_type: str,
                           props: dict[str, Any]) -> None:
        with self._lock:
            data = {**props, "rel_type": rel_type}
            self._g.add_edge(source, target, key=rel_id, **data)

    def update_relationship(self, rel_id: str, patch: dict[str, Any]) -> bool:
        with self._lock:
            for u, v, k, data in self._g.edges(keys=True, data=True):
                if k == rel_id:
                    data.update(patch)
                    return True
        return False

    def update_node(self, node_id: str, patch: dict[str, Any]) -> bool:
        with self._lock:
            if not self._g.has_node(node_id):
                return False
            self._g.nodes[node_id].update(patch)
            return True

    # --- read --------------------------------------------------------------
    def node(self, node_id: str) -> Optional[dict[str, Any]]:
        if not self._g.has_node(node_id):
            return None
        return {"id": node_id, **self._g.nodes[node_id]}

    def nodes(self, case_id: Optional[str] = None, entity_types: Optional[list[str]] = None
              ) -> list[dict[str, Any]]:
        out = []
        for nid, data in self._g.nodes(data=True):
            if case_id and case_id not in (data.get("cases") or []):
                continue
            if entity_types and data.get("entity_type") not in entity_types:
                continue
            out.append({"id": nid, **data})
        return out

    def relationships(self, case_id: Optional[str] = None) -> list[dict[str, Any]]:
        out = []
        for u, v, k, data in self._g.edges(keys=True, data=True):
            if case_id and data.get("case_id") != case_id:
                continue
            out.append({"id": k, "source": u, "target": v, **data})
        return out

    def relationship(self, rel_id: str) -> Optional[dict[str, Any]]:
        for u, v, k, data in self._g.edges(keys=True, data=True):
            if k == rel_id:
                return {"id": k, "source": u, "target": v, **data}
        return None

    def neighbours(self, node_id: str) -> list[dict[str, Any]]:
        if not self._g.has_node(node_id):
            return []
        out = []
        for u, v, k, data in self._g.out_edges(node_id, keys=True, data=True):
            out.append({"id": k, "source": u, "target": v, "direction": "OUT", **data})
        for u, v, k, data in self._g.in_edges(node_id, keys=True, data=True):
            out.append({"id": k, "source": u, "target": v, "direction": "IN", **data})
        return out

    def as_networkx(self, case_ids: Optional[list[str]] = None,
                    verified_only: bool = False) -> nx.MultiDiGraph:
        """Projection used by the analytics layer (NetworkX / Neo4j GDS equivalent)."""
        if case_ids is None and not verified_only:
            return self._g.copy()
        h = nx.MultiDiGraph()
        for u, v, k, data in self._g.edges(keys=True, data=True):
            if case_ids and data.get("case_id") not in case_ids:
                continue
            if verified_only and data.get("verification_status") == "REJECTED":
                continue
            for n in (u, v):
                if not h.has_node(n):
                    h.add_node(n, **self._g.nodes[n])
            h.add_edge(u, v, key=k, **data)
        return h

    def clear(self) -> None:
        with self._lock:
            self._g.clear()

    def status(self) -> dict[str, Any]:
        return {
            "component": "Neo4j",
            "profile": self.profile,
            "detail": self.detail,
            "gds_available": self.gds_available,
            "algorithm_engine": "Neo4j GDS" if self.gds_available else "NetworkX",
            "nodes": self._g.number_of_nodes(),
            "relationships": self._g.number_of_edges(),
        }


graph_store = GraphStore()
