"""NETWORK ANALYSIS AGENT (NetworkX / Neo4j GDS).

Degree centrality, betweenness centrality, community detection, shortest paths.

Terminology rule: structural prominence is reported as "structurally important node"
or "highly connected entity". The agent never labels a person a leader or a criminal.
"""
from __future__ import annotations

from typing import Any, Optional

import networkx as nx

from ..database.neo4j_graph import graph_store
from ..security.pii import mask_identifier, mask_node

AGENT_NAME = "NETWORK_TEMPORAL_AGENT"


def _projection(case_ids: Optional[list[str]] = None) -> nx.Graph:
    mg = graph_store.as_networkx(case_ids=case_ids)
    g = nx.Graph()
    for n, data in mg.nodes(data=True):
        if data.get("entity_type") == "CASE":
            continue
        g.add_node(n, **data)
    for u, v, k, data in mg.edges(keys=True, data=True):
        if data.get("hidden"):
            continue
        if u not in g or v not in g:
            continue
        if g.has_edge(u, v):
            g[u][v]["weight"] += 1
            g[u][v]["evidence_ids"].append(data.get("evidence_id"))
            g[u][v]["rel_types"].append(data.get("rel_type"))
        else:
            g.add_edge(u, v, weight=1,
                       evidence_ids=[data.get("evidence_id")],
                       rel_types=[data.get("rel_type")])
    return g


def _label(g: nx.Graph, node: str) -> str:
    """Node label as shown to a human - identifiers are masked per the PII policy
    (app/security/pii.py). The full value is available only through the audited
    reveal action, and matching keys keep the unmasked digits internally."""
    data = g.nodes.get(node, {})
    return mask_identifier(data.get("entity_type"), data.get("label", node))


# Human-readable nouns for the entity types that can appear in the graph, with the
# plural used when a node connects more than one of them.
_TYPE_NOUNS: dict[str, tuple[str, str]] = {
    "PERSON": ("person", "people"),
    "ALIAS": ("name variant", "name variants"),
    "ORGANIZATION": ("organisation", "organisations"),
    "LOCATION": ("location", "locations"),
    "VEHICLE": ("vehicle", "vehicles"),
    "PHONE": ("phone number", "phone numbers"),
    "ACCOUNT": ("bank account", "bank accounts"),
    "DEVICE": ("device", "devices"),
    "EVENT": ("event", "events"),
    "DATE": ("date", "dates"),
    "IDENTIFIER": ("identifier", "identifiers"),
    "CASE": ("case", "cases"),
}


def _noun(entity_type: str, count: int) -> str:
    singular, plural = _TYPE_NOUNS.get(entity_type, (entity_type.lower(), entity_type.lower() + "s"))
    return f"{count} {singular if count == 1 else plural}"


def _case_phrase(node_data: dict[str, Any], scope_cases: Optional[list[str]]) -> tuple[str, int]:
    """'3 cases (CASE-101, CASE-202, CASE-305)' from the node's own case membership."""
    cases = [c for c in (node_data.get("cases") or []) if c]
    if scope_cases is not None:
        cases = [c for c in cases if c in scope_cases]
    cases = sorted(set(cases))
    if not cases:
        return "", 0
    shown = ", ".join(cases[:3]) + (f", +{len(cases) - 3} more" if len(cases) > 3 else "")
    word = "case" if len(cases) == 1 else "cases"
    return f"{len(cases)} {word} ({shown})", len(cases)


def _type_phrase(type_counts: dict[str, int], limit: int = 3) -> str:
    """'2 vehicles and 1 phone number' - the entity types this node actually links to."""
    ordered = sorted(type_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:limit]
    parts = [_noun(t, c) for t, c in ordered if c]
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def neighbour_communities(g: nx.Graph, node: str, community_map: dict[str, int]) -> set[int]:
    return {community_map[nb] for nb in g.neighbors(node) if nb in community_map}


def bridge_nodes(g: nx.Graph, community_map: dict[str, int]) -> list[str]:
    """Nodes whose evidence-backed links reach more than one community.

    A node that appears in several communities' member lists is not a bridge by itself -
    it is a node that is *placed* in one of them. What makes it structural is that its own
    neighbours fall into different communities.
    """
    return [n for n in g.nodes if len(neighbour_communities(g, n, community_map)) >= 2]


def _type_label(node_type: str) -> str:
    """Singular noun for a node's type, e.g. 'PHONE' -> 'phone number'."""
    return _TYPE_NOUNS.get(node_type, (node_type.lower(), ""))[0]


def explain_node(g: nx.Graph, node: str, community_map: dict[str, int],
                 betweenness_score: float, bridges: list[str],
                 scope_cases: Optional[list[str]] = None) -> str:
    """Build a per-node explanation out of this node's own graph facts.

    Every clause is read off the projected graph: case membership, the entity types the
    node is actually linked to, and whether its own neighbours span several communities.
    Two nodes get identical wording only when they genuinely share the same structure; a
    rank band alone never produces a sentence.
    """
    data = g.nodes.get(node, {})
    neighbours = list(g.neighbors(node))
    if not neighbours:
        return ("Isolated node in this projection: it carries no evidence-backed "
                "relationship, so no structural role can be described.")

    type_counts: dict[str, int] = {}
    for nb in neighbours:
        t = g.nodes[nb].get("entity_type", "UNKNOWN")
        type_counts[t] = type_counts.get(t, 0) + 1

    case_phrase, case_count = _case_phrase(data, scope_cases)
    link_phrase = _type_phrase(type_counts)
    degree = len(neighbours)
    relation_count = sum(len([e for e in (g[node][nb].get("evidence_ids") or []) if e])
                         for nb in neighbours)
    communities = neighbour_communities(g, node, community_map)

    clauses: list[str] = []
    if case_phrase:
        clauses.append(f"appears in {case_phrase}")
    clauses.append(f"is connected to {degree} distinct "
                   f"{'entity' if degree == 1 else 'entities'}"
                   + (f" ({link_phrase})" if link_phrase else ""))

    if len(communities) >= 2:
        others = [b for b in bridges if b != node]
        if not others:
            clauses.append(f"and is the ONLY shared link between the {len(communities)} "
                           f"otherwise separate communities its neighbours belong to")
        else:
            clauses.append(f"and links {len(communities)} communities that otherwise have no "
                           f"shared entity (one of {len(others) + 1} bridging entities in this "
                           f"projection)")
    elif betweenness_score > 0:
        clauses.append("sits inside one community but on the shortest evidence paths between "
                       "the entities in it")
    else:
        clauses.append("sits entirely inside one community and on no bridging path here")

    first = f"This {_type_label(data.get('entity_type', 'ENTITY'))} " + ", ".join(clauses) + "."
    second = (f"{relation_count} evidence-linked "
              f"{'relationship' if relation_count == 1 else 'relationships'} back it."
              if relation_count else
              "None of those relationships carries a registered evidence identifier.")

    parts = [first, second]
    if case_count > 1:
        parts.append("Cross-case overlap such as this is a lead for an investigator to check, "
                     "not a finding.")
    locations = sorted({str(v).title() for v in (data.get("attributes") or {}).get("locations", [])})
    if locations:
        parts.append(f"Locations recorded on this entity: {', '.join(locations[:3])}"
                     f"{' +more' if len(locations) > 3 else ''}.")
    return " ".join(parts)


def analyze(case_ids: Optional[list[str]] = None, top_k: int = 10) -> dict[str, Any]:
    g = _projection(case_ids)
    n, m = g.number_of_nodes(), g.number_of_edges()
    engine = "Neo4j GDS" if graph_store.gds_available else "NetworkX"

    if n == 0 or m == 0:
        return {
            "agent": AGENT_NAME, "engine": engine, "nodes": n, "edges": m,
            "sufficient": False,
            "message": "INSUFFICIENT EVIDENCE: no evidence-backed relationships exist in this scope, "
                       "so no network structure can be computed.",
            "degree_centrality": [], "betweenness_centrality": [], "communities": [],
            "density": 0.0, "components": 0,
        }

    degree = nx.degree_centrality(g)
    betweenness = nx.betweenness_centrality(g, weight=None, normalized=True)

    try:
        communities = list(nx.community.louvain_communities(g, seed=42))
        community_algo = "Louvain modularity (NetworkX)"
    except Exception:
        communities = list(nx.community.greedy_modularity_communities(g))
        community_algo = "Greedy modularity (NetworkX)"

    community_map: dict[str, int] = {}
    community_out: list[dict[str, Any]] = []
    for idx, members in enumerate(communities):
        members = sorted(members)
        for mnode in members:
            community_map[mnode] = idx
        types: dict[str, int] = {}
        for mnode in members:
            t = g.nodes[mnode].get("entity_type", "UNKNOWN")
            types[t] = types.get(t, 0) + 1
        community_out.append({
            "community_id": idx,
            "size": len(members),
            "members": [{"id": mm, "label": _label(g, mm),
                         "entity_type": g.nodes[mm].get("entity_type")} for mm in members],
            "composition": types,
            "interpretation": "Structural cluster of entities that share evidence-backed relationships. "
                              "Cluster membership is not an allegation.",
        })

    # Nodes whose own neighbours span more than one community - computed once, so a node
    # can be described as "the only bridge" only when it really is the only one.
    bridges = bridge_nodes(g, community_map)

    def rank(metric: dict[str, float], label: str) -> list[dict[str, Any]]:
        items = sorted(metric.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
        out = []
        for i, (node, score) in enumerate(items):
            data = g.nodes[node]
            cases, _case_count = _case_phrase(data, case_ids)
            out.append({
                "entity_id": node,
                "label": _label(g, node),
                "entity_type": data.get("entity_type"),
                "score": round(score, 4),
                "rank": i + 1,
                "community_id": community_map.get(node),
                "degree": g.degree(node),
                "cases": [c for c in (data.get("cases") or []) if c],
                "communities_touched": sorted(neighbour_communities(g, node, community_map)),
                "connected_type_counts": {
                    t: sum(1 for nb in g.neighbors(node)
                           if g.nodes[nb].get("entity_type") == t)
                    for t in sorted({g.nodes[nb].get("entity_type", "UNKNOWN")
                                     for nb in g.neighbors(node)})},
                "interpretation": explain_node(g, node, community_map, score, bridges,
                                               case_ids),
                "interpretation_basis": (
                    f"{g.degree(node)} evidence-linked relationships, "
                    f"{len([c for c in (data.get('cases') or []) if c])} cases, "
                    f"{len(neighbour_communities(g, node, community_map))} communities touched"
                    + (f", present in {cases}" if cases else "")),
                "metric_note": ("Degree centrality is the share of the network reachable through "
                                "this entity's direct evidence-backed relationships."
                                if label == "degree" else
                                "Betweenness centrality is the share of shortest evidence paths "
                                "that pass through this entity."),
            })
        return out

    try:
        modularity = round(nx.community.modularity(g, communities), 4)
    except Exception:
        modularity = None

    return {
        "agent": AGENT_NAME,
        "engine": engine,
        "case_scope": case_ids or "ALL_AUTHORIZED",
        "nodes": n,
        "edges": m,
        "density": round(nx.density(g), 4),
        "components": nx.number_connected_components(g),
        "degree_centrality": rank(degree, "degree"),
        "betweenness_centrality": rank(betweenness, "betweenness"),
        "communities": community_out,
        "community_algorithm": community_algo,
        "modularity": modularity,
        "sufficient": True,
        "safety_note": "Centrality measures structural position in the evidence graph only. "
                       "It is not evidence of leadership, control or criminality.",
    }


def shortest_path(source: str, target: str, case_ids: Optional[list[str]] = None) -> dict[str, Any]:
    g = _projection(case_ids)
    if source not in g or target not in g:
        missing = [x for x in (source, target) if x not in g]
        return {
            "agent": AGENT_NAME, "found": False, "status": "ENTITY_NOT_IN_SCOPE",
            "missing": missing,
            "message": f"Entity not present in the authorized graph scope: {', '.join(missing)}.",
        }
    try:
        nodes = nx.shortest_path(g, source, target)
    except nx.NetworkXNoPath:
        return {
            "agent": AGENT_NAME, "found": False, "status": "NO_PATH",
            "message": "INSUFFICIENT EVIDENCE: no evidence-backed path connects these entities "
                       "in the authorized scope.",
        }

    hops = []
    for a, b in zip(nodes, nodes[1:]):
        data = g[a][b]
        hops.append({
            "from": a, "from_label": _label(g, a),
            "to": b, "to_label": _label(g, b),
            "relationship_types": [t for t in data.get("rel_types", []) if t],
            "evidence_ids": [e for e in data.get("evidence_ids", []) if e],
            "weight": data.get("weight", 1),
        })
    return {
        "agent": AGENT_NAME,
        "found": True,
        "length": len(nodes) - 1,
        "nodes": [{"id": x, "label": _label(g, x),
                   "entity_type": g.nodes[x].get("entity_type")} for x in nodes],
        "path_ids": nodes,
        "hops": hops,
        "interpretation": "Shows how two entities are connected through evidence-backed "
                          "relationships. A connection path is not proof of an association "
                          "between the endpoints.",
    }


def ego_summary(entity_id: str) -> dict[str, Any]:
    g = _projection(None)
    if entity_id not in g:
        return {"found": False, "entity_id": entity_id}
    deg = g.degree(entity_id)
    neighbours = [{"id": nb, "label": _label(g, nb),
                   "entity_type": g.nodes[nb].get("entity_type"),
                   "evidence_ids": [e for e in g[entity_id][nb].get("evidence_ids", []) if e]}
                  for nb in g.neighbors(entity_id)]
    return {"found": True, "entity_id": entity_id, "degree": deg, "neighbours": neighbours}
