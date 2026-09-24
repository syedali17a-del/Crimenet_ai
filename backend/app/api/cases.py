"""Case management API."""
from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..agents import reasoning_agent
from ..audit import audit_log, ledger
from ..config import DATA_CLASSIFICATION
from ..database.neo4j_graph import graph_store
from ..database.postgres import relational
from ..database.redis_cache import cache
from ..schemas.api import CaseCreate, CaseOut, CaseUpdate
from ..security.deps import Principal, authorize_case, authorized_case_ids, get_principal, require_permission
from ..security.pii import mask_node

router = APIRouter(prefix="/api/cases", tags=["cases"])


def _enrich(case: dict[str, Any]) -> CaseOut:
    cid = case["case_id"]
    evidence = [e for e in relational.all("evidence") if e["case_id"] == cid]
    entities = [n for n in graph_store.nodes() if cid in (n.get("cases") or [])
                and n.get("entity_type") != "CASE"]
    rels = [r for r in graph_store.relationships(cid) if not r.get("hidden")]
    return CaseOut(
        case_id=cid, title=case["title"], case_type=case["case_type"], priority=case["priority"],
        description=case.get("description", ""), investigator=case.get("investigator", ""),
        created_date=case.get("created_date", ""), status=case.get("status", "OPEN"),
        classification=case.get("classification", DATA_CLASSIFICATION),
        evidence_count=len(evidence), entity_count=len(entities), relationship_count=len(rels),
    )


@router.get("", response_model=list[CaseOut])
def list_cases(principal: Principal = Depends(require_permission("case:read"))) -> list[CaseOut]:
    allowed = set(authorized_case_ids(principal))
    return [_enrich(c) for c in relational.all("cases") if c["case_id"] in allowed]


@router.post("", response_model=CaseOut, status_code=201)
def create_case(payload: CaseCreate,
                principal: Principal = Depends(require_permission("case:create"))) -> CaseOut:
    case_id = payload.case_id
    if not case_id:
        existing = [int(c["case_id"].split("-")[1]) for c in relational.all("cases")
                    if c["case_id"].split("-")[1].isdigit()]
        case_id = f"CASE-{max(existing or [100]) + 7}"
    if relational.get("cases", case_id):
        raise HTTPException(status_code=409, detail=f"Case {case_id} already exists.")

    record = {
        "case_id": case_id, "title": payload.title.strip(), "case_type": payload.case_type.strip(),
        "priority": payload.priority, "description": payload.description.strip(),
        "investigator": payload.investigator or principal.user_id,
        "created_date": date.today().isoformat(), "status": payload.status,
        "jurisdiction": "Synthetic Jurisdiction", "classification": DATA_CLASSIFICATION,
    }
    relational.insert("cases", case_id, record)
    graph_store.merge_node(case_id, ["CASE"], {
        "entity_id": case_id, "entity_type": "CASE", "label": case_id, "normalized": case_id,
        "cases": [case_id], "attributes": {"title": record["title"]}, "evidence_ids": [],
        "verification_status": "UNVERIFIED", "support_level": "HIGH",
        "classification": DATA_CLASSIFICATION,
    })
    # creator keeps access; supervisors/admins already hold "*"
    user = relational.get("users", principal.user_id)
    if user and "*" not in user.get("case_access", []):
        user["case_access"] = sorted(set(user.get("case_access", []) + [case_id]))
        relational.upsert("users", principal.user_id, user)
        principal.case_access = user["case_access"]

    audit_log.record(principal.user_id, principal.role, "CASE_CREATED", case_id=case_id,
                     object_id=case_id, detail=f"{record['title']} ({record['case_type']}, "
                                               f"priority {record['priority']}).")
    ledger.append("CASE_CREATED", {"case_id": case_id, "title": record["title"],
                                   "created_by": principal.user_id}, case_id=case_id)
    cache.invalidate("analysis:")
    return _enrich(record)


@router.get("/{case_id}", response_model=CaseOut)
def get_case(case_id: str, principal: Principal = Depends(require_permission("case:read"))) -> CaseOut:
    authorize_case(principal, case_id)
    case = relational.get("cases", case_id)
    audit_log.record(principal.user_id, principal.role, "CASE_OPENED", case_id=case_id,
                     object_id=case_id, detail=f"Case {case_id} opened.")
    return _enrich(case)


@router.patch("/{case_id}", response_model=CaseOut)
def update_case(case_id: str, payload: CaseUpdate,
                principal: Principal = Depends(require_permission("case:assign"))) -> CaseOut:
    authorize_case(principal, case_id)
    case = relational.get("cases", case_id)
    patch = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not patch:
        raise HTTPException(status_code=400, detail="No fields supplied to update.")
    case.update(patch)
    relational.upsert("cases", case_id, case)
    audit_log.record(principal.user_id, principal.role, "CASE_UPDATED", case_id=case_id,
                     object_id=case_id, detail=", ".join(f"{k}={v}" for k, v in patch.items()))
    return _enrich(case)


@router.get("/{case_id}/entities")
def case_entities(case_id: str,
                  principal: Principal = Depends(require_permission("case:read"))) -> dict[str, Any]:
    authorize_case(principal, case_id)
    nodes = [n for n in graph_store.nodes(case_id=case_id) if n.get("entity_type") != "CASE"]
    return {
        "case_id": case_id,
        "count": len(nodes),
        "entities": nodes,
        "sufficient": bool(nodes),
        "message": "" if nodes else
                   "INSUFFICIENT EVIDENCE: no entities have been extracted for this case yet.",
        "classification": DATA_CLASSIFICATION,
    }


@router.get("/{case_id}/network")
def case_network(case_id: str,
                 principal: Principal = Depends(require_permission("case:read"))) -> dict[str, Any]:
    authorize_case(principal, case_id)
    return _graph_payload([case_id])


@router.get("/{case_id}/timeline")
def case_timeline(case_id: str,
                  principal: Principal = Depends(require_permission("case:read"))) -> dict[str, Any]:
    authorize_case(principal, case_id)
    events = sorted([e for e in relational.all("events") if e["case_id"] == case_id],
                    key=lambda e: e["timestamp"])
    return {"case_id": case_id, "events": events, "count": len(events),
            "sufficient": bool(events),
            "message": "" if events else "INSUFFICIENT EVIDENCE: no timestamped events recorded."}


@router.get("/{case_id}/hypotheses")
def case_hypotheses(case_id: str,
                    principal: Principal = Depends(require_permission("analysis:run"))) -> dict[str, Any]:
    authorize_case(principal, case_id)
    return reasoning_agent.hypotheses([case_id])


@router.get("/{case_id}/information-gaps")
def case_gaps(case_id: str,
              principal: Principal = Depends(require_permission("analysis:run"))) -> dict[str, Any]:
    authorize_case(principal, case_id)
    return reasoning_agent.information_gaps([case_id])


@router.get("/{case_id}/next-best-action")
def case_nba(case_id: str,
             principal: Principal = Depends(require_permission("analysis:run"))) -> dict[str, Any]:
    authorize_case(principal, case_id)
    return reasoning_agent.next_best_action([case_id])


def _graph_payload(case_ids: list[str] | None) -> dict[str, Any]:
    """Cytoscape-ready evidence-aware graph payload."""
    if case_ids:
        nodes: dict[str, dict[str, Any]] = {}
        for cid in case_ids:
            for n in graph_store.nodes(case_id=cid):
                nodes[n["id"]] = n
        rels = []
        for cid in case_ids:
            rels.extend([r for r in graph_store.relationships(cid) if not r.get("hidden")])
    else:
        nodes = {n["id"]: n for n in graph_store.nodes()}
        rels = [r for r in graph_store.relationships() if not r.get("hidden")]

    degree: dict[str, int] = {}
    for r in rels:
        degree[r["source"]] = degree.get(r["source"], 0) + 1
        degree[r["target"]] = degree.get(r["target"], 0) + 1

    shown = {nid: mask_node(n) for nid, n in nodes.items()}
    return {
        "case_ids": case_ids or "ALL_AUTHORIZED",
        "pii_policy": "PHONE / ACCOUNT / DEVICE labels are masked; GET "
                      "/api/entities/{entity_id}/reveal returns the full value and is audited.",
        "nodes": [
            {
                "data": {
                    "id": nid, "label": node.get("label"), "entity_type": node.get("entity_type"),
                    "identifier_masked": node.get("identifier_masked", False),
                    "reveal_endpoint": node.get("reveal_endpoint"),
                    "cases": node.get("cases", []), "support_level": node.get("support_level"),
                    "verification_status": node.get("verification_status"),
                    "evidence_ids": node.get("evidence_ids", []), "degree": degree.get(nid, 0),
                    "lat": node.get("lat"), "lon": node.get("lon"),
                }
            } for nid, node in shown.items()
        ],
        "edges": [
            {
                "data": {
                    "id": r["id"], "source": r["source"], "target": r["target"],
                    "relationship_type": r.get("rel_type"), "timestamp": r.get("timestamp"),
                    "evidence_id": r.get("evidence_id"), "case_id": r.get("case_id"),
                    "support_level": r.get("support_level"),
                    "verification_status": r.get("verification_status"),
                    "source_document": r.get("source_document"),
                }
            } for r in rels
        ],
        "counts": {"nodes": len(nodes), "edges": len(rels)},
        "sufficient": bool(rels),
        "message": "" if rels else
                   "INSUFFICIENT EVIDENCE: no evidence-backed relationships exist for this scope. "
                   "The graph cannot be reconstructed until corroborating evidence is added.",
        "classification": DATA_CLASSIFICATION,
    }
