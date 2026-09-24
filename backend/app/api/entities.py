"""Entity / relationship API including the human-in-the-loop decisions."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException

from ..agents import network_agent
from ..audit import audit_log, ledger
from ..config import DATA_CLASSIFICATION
from ..database.neo4j_graph import graph_store
from ..database.postgres import relational
from ..models.domain import now_iso
from ..schemas.api import AnnotationRequest, VerificationRequest
from ..security.deps import Principal, authorized_case_ids, require_permission
from ..security import pii
from ..security.pii import mask_node, mask_nodes, reveal

router = APIRouter(prefix="/api", tags=["entities"])


def _authorized_node(entity_id: str, principal: Principal) -> dict[str, Any]:
    node = graph_store.node(entity_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Entity {entity_id} not found.")
    allowed = set(authorized_case_ids(principal))
    if node.get("cases") and not (set(node["cases"]) & allowed):
        raise HTTPException(status_code=403,
                            detail="Case-level authorization denied for this entity.")
    return node


@router.get("/entities")
def list_entities(entity_type: Optional[str] = None, case_id: Optional[str] = None, q: Optional[str] = None,
                  principal: Principal = Depends(require_permission("case:read"))) -> dict[str, Any]:
    allowed = set(authorized_case_ids(principal))
    nodes = [n for n in graph_store.nodes()
             if not n.get("cases") or set(n["cases"]) & allowed]
    if entity_type:
        nodes = [n for n in nodes if n.get("entity_type") == entity_type.upper()]
    if case_id:
        nodes = [n for n in nodes if case_id in (n.get("cases") or [])]
    if q:
        ql = q.lower()
        nodes = [n for n in nodes if ql in (n.get("label", "") or "").lower()
                 or ql in (n.get("entity_id", "") or "").lower()]
    return {"count": len(nodes), "entities": mask_nodes(nodes),
            "pii_policy": "PHONE / ACCOUNT / DEVICE identifiers are masked in API responses; "
                          "the full value is available only through GET "
                          "/api/entities/{entity_id}/reveal, which is audited.",
            "classification": DATA_CLASSIFICATION}


@router.get("/entities/{entity_id}")
def entity_profile(entity_id: str,
                   principal: Principal = Depends(require_permission("case:read"))) -> dict[str, Any]:
    node = _authorized_node(entity_id, principal)
    rels = [r for r in graph_store.neighbours(entity_id) if not r.get("hidden")]
    evidence_ids = sorted({r.get("evidence_id") for r in rels if r.get("evidence_id")}
                          | set(node.get("evidence_ids") or []))
    evidence = [relational.get("evidence", e) for e in evidence_ids]
    evidence = [{"evidence_id": e["evidence_id"], "type": e["evidence_type"], "source": e["source"],
                 "timestamp": e["timestamp"], "integrity_status": e["integrity_status"],
                 "verification_status": e["verification_status"], "case_id": e["case_id"]}
                for e in evidence if e]
    timeline = sorted([e for e in relational.all("events") if entity_id in (e.get("entity_ids") or [])],
                      key=lambda e: e["timestamp"])
    annotations = [a for a in relational.all("annotations") if a["object_id"] == entity_id]
    ego = network_agent.ego_summary(entity_id)
    return pii.mask_payload({
        "entity": mask_node(node),
        "relationships": [{
            "relationship_id": r["id"], "direction": r.get("direction"),
            "source": r["source"], "target": r["target"],
            "source_label": mask_node(graph_store.node(r["source"]) or {}).get("label"),
            "target_label": mask_node(graph_store.node(r["target"]) or {}).get("label"),
            "relationship_type": r.get("rel_type"), "timestamp": r.get("timestamp"),
            "evidence_id": r.get("evidence_id"), "case_id": r.get("case_id"),
            "support_level": r.get("support_level"),
            "verification_status": r.get("verification_status"),
            "source_document": r.get("source_document"),
        } for r in rels],
        "evidence": evidence,
        "timeline": timeline,
        "annotations": sorted(annotations, key=lambda a: a["timestamp"], reverse=True),
        "degree": ego.get("degree", 0),
        "cases": node.get("cases", []),
        "classification": DATA_CLASSIFICATION,
        "safety_note": "Entity profiles describe evidence-backed observations only. No inference of "
                       "criminal responsibility is made by this system.",
    })


@router.get("/relationships/{relationship_id}")
def relationship_detail(relationship_id: str,
                        principal: Principal = Depends(require_permission("case:read"))) -> dict[str, Any]:
    rel = graph_store.relationship(relationship_id)
    if not rel:
        raise HTTPException(status_code=404, detail=f"Relationship {relationship_id} not found.")
    allowed = set(authorized_case_ids(principal))
    if rel.get("case_id") and rel["case_id"] not in allowed:
        raise HTTPException(status_code=403, detail="Case-level authorization denied.")
    ev = relational.get("evidence", rel.get("evidence_id") or "")
    return pii.mask_payload({
        "relationship": {
            "relationship_id": rel["id"], "source": rel["source"], "target": rel["target"],
            "source_entity": mask_node(graph_store.node(rel["source"])),
            "target_entity": mask_node(graph_store.node(rel["target"])),
            "relationship_type": rel.get("rel_type"), "timestamp": rel.get("timestamp"),
            "evidence_id": rel.get("evidence_id"), "case_id": rel.get("case_id"),
            "support_level": rel.get("support_level"),
            "verification_status": rel.get("verification_status"),
            "source_document": rel.get("source_document"), "notes": rel.get("notes", ""),
        },
        "evidence": ev and {
            "evidence_id": ev["evidence_id"], "type": ev["evidence_type"], "source": ev["source"],
            "timestamp": ev["timestamp"], "integrity_status": ev["integrity_status"],
            "verification_status": ev["verification_status"], "sha256": ev["sha256"],
        },
        "annotations": [a for a in relational.all("annotations") if a["object_id"] == relationship_id],
        "classification": DATA_CLASSIFICATION,
    })

@router.get("/entities/{entity_id}/reveal")
def reveal_identifier(entity_id: str,
                      principal: Principal = Depends(require_permission("evidence:read"))
                      ) -> dict[str, Any]:
    """AUDITED reveal of a masked identifier (phone / account / device).

    Every call writes an IDENTIFIER_REVEALED audit record naming the officer, the role,
    the case and the identifier, so the mask can be lifted without the lift being
    invisible. A non-identifier entity returns `masked: false` and no value.
    """
    node = _authorized_node(entity_id, principal)
    payload = reveal(node)
    if not payload:
        return {"entity_id": entity_id, "masked": False,
                "message": "This entity type is not a masked identifier; nothing to reveal.",
                "label": mask_node(node).get("label")}
    audit_log.record(principal.user_id, principal.role, "IDENTIFIER_REVEALED",
                     case_id=(node.get("cases") or [None])[0], object_id=entity_id,
                     detail=f"Unmasked {payload['entity_type']} identifier "
                            f"{payload['label']} (masked form {payload['masked_form']}).")
    ledger.append("IDENTIFIER_REVEALED",
                  {"object_id": entity_id, "object_type": payload["entity_type"],
                   "revealed_by": principal.user_id, "timestamp": now_iso()},
                  case_id=(node.get("cases") or [None])[0])
    return {
        "entity_id": payload["entity_id"],
        "entity_type": payload["entity_type"],
        "masked": True,
        "value": payload["label"],
        "normalized": payload["normalized"],
        "masked_form": payload["masked_form"],
        "at_rest": payload["at_rest"],
        "audited": True,
        "audit_action": "IDENTIFIER_REVEALED",
        "revealed_by": principal.user_id,
        "revealed_at": now_iso(),
        "policy_note": "Identifiers are masked by default. This reveal is recorded in the "
                       "append-only audit trail and the hash-chained ledger.",
    }


# --- human-in-the-loop -----------------------------------------------------
def _record_decision(object_id: str, object_type: str, case_id: Optional[str], decision: str,
                     principal: Principal, payload: VerificationRequest) -> dict[str, Any]:
    record = {
        "record_id": f"VER-{relational.count('verifications') + 1:04d}",
        "object_id": object_id, "object_type": object_type, "case_id": case_id,
        "decision": decision, "verified_by": principal.user_id, "role": principal.role,
        "timestamp": now_iso(), "rationale": payload.rationale,
        "evidence_ids": payload.evidence_ids,
    }
    relational.insert("verifications", object_id, record)
    audit_log.record(principal.user_id, principal.role, f"{object_type}_{decision}",
                     case_id=case_id, object_id=object_id, detail=payload.rationale)
    ledger.append(f"{object_type}_{decision}",
                  {k: record[k] for k in ("object_id", "object_type", "decision", "verified_by",
                                          "timestamp", "case_id")},
                  case_id=case_id)
    return record


@router.post("/entities/{entity_id}/verify")
def verify_entity(entity_id: str, payload: VerificationRequest,
                  principal: Principal = Depends(require_permission("verification:decide"))
                  ) -> dict[str, Any]:
    node = _authorized_node(entity_id, principal)
    graph_store.update_node(entity_id, {"verification_status": "HUMAN_VERIFIED"})
    record = _record_decision(entity_id, "ENTITY", (node.get("cases") or [None])[0],
                              "HUMAN_VERIFIED", principal, payload)
    return {"entity": graph_store.node(entity_id), "verification": record,
            "note": "Original analytical finding retained; verification status updated."}


@router.post("/entities/{entity_id}/reject")
def reject_entity(entity_id: str, payload: VerificationRequest,
                  principal: Principal = Depends(require_permission("verification:decide"))
                  ) -> dict[str, Any]:
    node = _authorized_node(entity_id, principal)
    graph_store.update_node(entity_id, {"verification_status": "REJECTED"})
    record = _record_decision(entity_id, "ENTITY", (node.get("cases") or [None])[0],
                              "REJECTED", principal, payload)
    return {"entity": graph_store.node(entity_id), "verification": record,
            "note": "Rejection recorded. The underlying analytical finding is preserved, not deleted."}


@router.post("/entities/{entity_id}/annotate")
def annotate_entity(entity_id: str, payload: AnnotationRequest,
                    principal: Principal = Depends(require_permission("entity:annotate"))
                    ) -> dict[str, Any]:
    node = _authorized_node(entity_id, principal)
    ann = {
        "annotation_id": f"ANN-{relational.count('annotations') + 1:04d}", "object_id": entity_id,
        "object_type": "ENTITY", "case_id": (node.get("cases") or [None])[0],
        "author": principal.user_id, "timestamp": now_iso(), "text": payload.text.strip(),
    }
    relational.insert("annotations", ann["annotation_id"], ann)
    audit_log.record(principal.user_id, principal.role, "ENTITY_ANNOTATED",
                     case_id=ann["case_id"], object_id=entity_id, detail=payload.text[:180])
    return {"annotation": ann}


@router.post("/relationships/{relationship_id}/verify")
def verify_relationship(relationship_id: str, payload: VerificationRequest,
                        principal: Principal = Depends(require_permission("verification:decide"))
                        ) -> dict[str, Any]:
    rel = graph_store.relationship(relationship_id)
    if not rel:
        raise HTTPException(status_code=404, detail="Relationship not found.")
    graph_store.update_relationship(relationship_id, {"verification_status": "HUMAN_VERIFIED"})
    record = _record_decision(relationship_id, "RELATIONSHIP", rel.get("case_id"),
                              "HUMAN_VERIFIED", principal, payload)
    return {"relationship": graph_store.relationship(relationship_id), "verification": record}


@router.post("/relationships/{relationship_id}/reject")
def reject_relationship(relationship_id: str, payload: VerificationRequest,
                        principal: Principal = Depends(require_permission("verification:decide"))
                        ) -> dict[str, Any]:
    rel = graph_store.relationship(relationship_id)
    if not rel:
        raise HTTPException(status_code=404, detail="Relationship not found.")
    graph_store.update_relationship(relationship_id, {"verification_status": "REJECTED"})
    record = _record_decision(relationship_id, "RELATIONSHIP", rel.get("case_id"),
                              "REJECTED", principal, payload)
    return {"relationship": graph_store.relationship(relationship_id), "verification": record,
            "note": "Finding preserved; marked rejected by human reviewer."}


@router.post("/findings/{finding_id}/verify")
def verify_finding(finding_id: str, payload: VerificationRequest,
                   principal: Principal = Depends(require_permission("verification:decide"))
                   ) -> dict[str, Any]:
    """Generic decision endpoint for cross-case links, identity matches, convergence events
    and hypotheses (objects that are computed rather than stored)."""
    record = _record_decision(finding_id, payload.object_type, payload.case_id,
                              "HUMAN_VERIFIED", principal, payload)
    return {"finding_id": finding_id, "verification": record}


@router.post("/findings/{finding_id}/reject")
def reject_finding(finding_id: str, payload: VerificationRequest,
                   principal: Principal = Depends(require_permission("verification:decide"))
                   ) -> dict[str, Any]:
    record = _record_decision(finding_id, payload.object_type, payload.case_id,
                              "REJECTED", principal, payload)
    return {"finding_id": finding_id, "verification": record,
            "note": "Rejection recorded; analytical finding retained for audit."}


@router.post("/findings/{finding_id}/annotate")
def annotate_finding(finding_id: str, payload: AnnotationRequest,
                     principal: Principal = Depends(require_permission("entity:annotate"))
                     ) -> dict[str, Any]:
    ann = {
        "annotation_id": f"ANN-{relational.count('annotations') + 1:04d}", "object_id": finding_id,
        "object_type": payload.object_type, "case_id": payload.case_id,
        "author": principal.user_id, "timestamp": now_iso(), "text": payload.text.strip(),
    }
    relational.insert("annotations", ann["annotation_id"], ann)
    audit_log.record(principal.user_id, principal.role, "FINDING_ANNOTATED",
                     case_id=payload.case_id, object_id=finding_id, detail=payload.text[:180])
    return {"annotation": ann}


@router.get("/verifications")
def verifications(principal: Principal = Depends(require_permission("case:read"))) -> dict[str, Any]:
    rows = relational.all("verifications")
    allowed = set(authorized_case_ids(principal))
    rows = [r for r in rows if not r.get("case_id") or r["case_id"] in allowed]
    rows.sort(key=lambda r: r["timestamp"], reverse=True)
    return {"count": len(rows), "verifications": rows}
