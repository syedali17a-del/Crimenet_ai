"""Command-centre aggregation API: dashboard, global graph, map, timeline, search."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query

from ..agents import network_agent, reasoning_agent, temporal_agent
from ..analytics import anomaly, cross_case
from ..api.cases import _graph_payload
from ..audit import audit_log, ledger
from ..config import APP_DESCRIPTION, APP_NAME, APP_TAGLINE, DATA_CLASSIFICATION
from ..database.neo4j_graph import graph_store
from ..database.postgres import relational
from ..security.deps import Principal, authorize_case, authorized_case_ids, require_permission
from ..security import pii
from ..security.pii import mask_node

router = APIRouter(prefix="/api", tags=["intelligence"])

PRINCIPLE = ("AI finds patterns. Evidence supports them. Specialized agents corroborate them. "
             "Security protects them. Humans decide what they mean.")


@router.get("/dashboard")
def dashboard(case_id: Optional[str] = None,
              principal: Principal = Depends(require_permission("case:read"))) -> dict[str, Any]:
    allowed = authorized_case_ids(principal)
    scope = [case_id] if case_id else allowed
    if case_id:
        authorize_case(principal, case_id)

    cases = [c for c in relational.all("cases") if c["case_id"] in allowed]
    evidence = [e for e in relational.all("evidence") if e["case_id"] in scope]
    rels = [r for r in graph_store.relationships() if r.get("case_id") in scope and not r.get("hidden")]
    candidate_rels = [r for r in rels if r.get("verification_status") == "UNVERIFIED"]
    xcase = cross_case.correlate(scope)
    gaps = reasoning_agent.information_gaps(scope)
    corr = reasoning_agent.corroborate(scope)
    nba = reasoning_agent.next_best_action(scope)
    temporal = temporal_agent.analyze(scope)
    anomalies = anomaly.analyze(scope)
    pending = [r for r in rels if r.get("verification_status") == "UNVERIFIED"
               and r.get("support_level") in {"HIGH", "MEDIUM"}]
    chain = ledger.verify_chain()
    integrity_issues = [e for e in evidence if e.get("integrity_status") == "MISMATCH"]

    return {
        "product": {"name": APP_NAME, "tagline": APP_TAGLINE, "description": APP_DESCRIPTION,
                    "principle": PRINCIPLE, "classification": DATA_CLASSIFICATION},
        "scope": scope,
        "kpis": {
            "active_cases": sum(1 for c in cases if c["status"] in {"ACTIVE", "OPEN", "UNDER_REVIEW"}),
            "total_cases": len(cases),
            "evidence_items": len(evidence),
            "candidate_relationships": len(candidate_rels),
            "cross_case_links": len(xcase["associations"]),
            "information_gaps": len(gaps["gaps"]),
            "pending_verifications": len(pending),
            "analytical_anomalies": len(anomalies.get("anomalies", [])),
        },
        "pipeline": [
            {"stage": "EVIDENCE", "value": len(evidence),
             "detail": f"{sum(1 for e in evidence if e.get('processing_status') in {'EXTRACTED', 'ENTITIES_FOUND', 'RELATIONSHIPS_CANDIDATE'})} processed"},
            {"stage": "NETWORK", "value": len(rels),
             "detail": f"{len({n['id'] for n in graph_store.nodes() if set(n.get('cases', [])) & set(scope)})} entities"},
            {"stage": "INTELLIGENCE", "value": len(corr["leads"]),
             "detail": f"{corr['summary']['corroborated']} corroborated, "
                       f"{corr['summary']['insufficient']} insufficient"},
        ],
        "network_preview": _graph_payload(scope if case_id else None),
        "timeline_preview": temporal.get("events", [])[:12],
        "recent_evidence": sorted(evidence, key=lambda e: e["timestamp"], reverse=True)[:6],
        "findings": corr["leads"][:5],
        "pending_validation": [{
            "relationship_id": r["id"], "source": r["source"], "target": r["target"],
            "source_label": mask_node(graph_store.node(r["source"]) or {}).get("label"),
            "target_label": mask_node(graph_store.node(r["target"]) or {}).get("label"),
            "relationship_type": r.get("rel_type"), "case_id": r.get("case_id"),
            "support_level": r.get("support_level"), "evidence_id": r.get("evidence_id"),
        } for r in pending[:8]],
        "information_gaps": gaps["gaps"][:4],
        "next_best_action": nba.get("recommended"),
        "next_best_actions": nba.get("actions", [])[:4],
        "integrity": {
            "ledger_intact": chain["chain_intact"],
            "ledger_blocks": chain["blocks"],
            "head_hash": chain["head_hash"],
            "mismatches": [e["evidence_id"] for e in integrity_issues],
            "verified": sum(1 for e in evidence if e.get("integrity_status") == "VERIFIED"),
            "total": len(evidence),
        },
        "recent_audit": audit_log.query(limit=6),
    }


@router.get("/graph")
def global_graph(case_id: Optional[str] = None,
                 principal: Principal = Depends(require_permission("case:read"))) -> dict[str, Any]:
    allowed = authorized_case_ids(principal)
    if case_id:
        authorize_case(principal, case_id)
        return _graph_payload([case_id])
    return _graph_payload(allowed)


@router.get("/timeline")
def global_timeline(case_ids: Optional[str] = Query(default=None,
                                                    description="Comma separated case ids"),
                    entity_id: Optional[str] = None, start: Optional[str] = None,
                    end: Optional[str] = None,
                    principal: Principal = Depends(require_permission("case:read"))) -> dict[str, Any]:
    allowed = authorized_case_ids(principal)
    scope = [c for c in (case_ids.split(",") if case_ids else allowed) if c in allowed]
    result = temporal_agent.analyze(scope, entity_id, start, end)
    enriched = []
    for e in result.get("events", []):
        loc = graph_store.node(e.get("location_id") or "") or {}
        enriched.append({
            **e,
            "location_label": loc.get("label"),
            "entity_labels": [mask_node(graph_store.node(x) or {}).get("label", x)
                              for x in (e.get("entity_ids") or [])],
        })
    result["events"] = enriched
    return pii.mask_payload(result)


@router.get("/map")
def map_intelligence(case_ids: Optional[str] = Query(default=None),
                     principal: Principal = Depends(require_permission("case:read"))) -> dict[str, Any]:
    allowed = authorized_case_ids(principal)
    scope = [c for c in (case_ids.split(",") if case_ids else allowed) if c in allowed]
    locations = [n for n in graph_store.nodes() if n.get("entity_type") == "LOCATION"
                 and (not n.get("cases") or set(n["cases"]) & set(scope))]
    events = [e for e in relational.all("events") if e.get("case_id") in scope and e.get("location_id")]
    conv = temporal_agent.convergence(scope)["convergence_events"]

    points = []
    for loc in locations:
        loc_events = [e for e in events if e["location_id"] == loc["id"]]
        entity_ids = sorted({x for e in loc_events for x in (e.get("entity_ids") or [])})
        points.append({
            "location_id": loc["id"], "label": loc.get("label"),
            "lat": loc.get("lat"), "lon": loc.get("lon"),
            "cases": loc.get("cases", []),
            "event_count": len(loc_events),
            "entities": [{"id": x, "label": mask_node(graph_store.node(x) or {}).get("label", x),
                          "entity_type": (graph_store.node(x) or {}).get("entity_type")}
                         for x in entity_ids],
            "events": sorted(loc_events, key=lambda e: e["timestamp"]),
            "evidence_ids": sorted({e.get("evidence_id") for e in loc_events if e.get("evidence_id")}),
            "convergence": [c for c in conv if c["location_id"] == loc["id"]],
        })
    points = [p for p in points if p["lat"] is not None]
    return pii.mask_payload({
        "points": points,
        "convergence_events": conv,
        "count": len(points),
        "sufficient": bool(points),
        "message": "" if points else
                   "INSUFFICIENT EVIDENCE: no geolocated observations available for this scope.",
        "classification": DATA_CLASSIFICATION,
    })


def _masked_search(payload: dict[str, Any]) -> dict[str, Any]:
    """Policy (a): identifiers are masked in every response, the search echo included."""
    return pii.mask_payload(payload)


@router.get("/search")
def global_search(q: str = Query(min_length=1, max_length=80),
                  principal: Principal = Depends(require_permission("case:read"))) -> dict[str, Any]:
    allowed = set(authorized_case_ids(principal))
    ql = q.lower().strip()

    cases = [c for c in relational.all("cases")
             if c["case_id"] in allowed and (ql in c["case_id"].lower() or ql in c["title"].lower())]
    entities = [n for n in graph_store.nodes()
                if (not n.get("cases") or set(n["cases"]) & allowed)
                and (ql in (n.get("label") or "").lower() or ql in n["id"].lower())]
    evidence = [e for e in relational.all("evidence")
                if e["case_id"] in allowed and (ql in e["evidence_id"].lower()
                                                or ql in e["evidence_type"].lower()
                                                or ql in e["source"].lower())]
    result = {
        "query": q,
        "cases": cases[:10],
        "entities": [{"id": n["id"], "label": mask_node(n).get("label"),
                      "entity_type": n.get("entity_type"),
                      "cases": n.get("cases", [])} for n in entities[:15]],
        "evidence": [{"evidence_id": e["evidence_id"], "case_id": e["case_id"],
                      "type": e["evidence_type"], "source": e["source"]} for e in evidence[:10]],
        "total": len(cases) + len(entities) + len(evidence),
    }
    return _masked_search(result)


@router.get("/insights")
def insights(case_ids: Optional[str] = Query(default=None),
             principal: Principal = Depends(require_permission("analysis:run"))) -> dict[str, Any]:
    allowed = authorized_case_ids(principal)
    scope = [c for c in (case_ids.split(",") if case_ids else allowed) if c in allowed]
    corr = reasoning_agent.corroborate(scope)
    return {
        "leads": corr["leads"],
        "summary": corr["summary"],
        "network": network_agent.analyze(scope),
        "principle": PRINCIPLE,
    }


@router.get("/contradictions")
def contradictions(principal: Principal = Depends(require_permission("case:read"))) -> dict[str, Any]:
    allowed = set(authorized_case_ids(principal))
    rows = [c for c in relational.all("contradictions") if c.get("case_id") in allowed]
    return {"count": len(rows), "contradictions": rows,
            "policy": "Contradictory evidence is displayed, never suppressed."}
