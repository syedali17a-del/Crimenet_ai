"""Audit trail, permissioned ledger and evidence-integrity overview API."""
from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import APIRouter, Depends

from ..agents import evidence_agent
from ..audit import audit_log, ledger, ledger_store
from ..database.postgres import relational
from ..security.deps import Principal, authorized_case_ids, require_permission

router = APIRouter(prefix="/api", tags=["audit"])


@router.get("/audit")
def get_audit(case_id: Optional[str] = None, action: Optional[str] = None, limit: int = 250,
              principal: Principal = Depends(require_permission("audit:read"))) -> dict[str, Any]:
    allowed = set(authorized_case_ids(principal))
    rows = audit_log.query(case_id=case_id, action=action, limit=limit)
    if principal.role not in {"ADMIN", "SUPERVISOR"}:
        rows = [r for r in rows if not r.get("case_id") or r["case_id"] in allowed]
    return {
        "count": len(rows),
        "records": rows,
        "total_records": audit_log.count(),
        "append_only": True,
        "chain": audit_log.verify_chain(),
        "note": "Audit records are append-only, individually SHA-256 hashed AND hash-chained "
                "(each record stores the hash of its predecessor). No user or agent can modify "
                "audit history without breaking the chain, which /api/audit/chain reports.",
    }


@router.get("/ledger")
def get_ledger(case_id: Optional[str] = None, limit: int = 200,
               principal: Principal = Depends(require_permission("ledger:read"))) -> dict[str, Any]:
    return {
        "profile": ledger.LEDGER_PROFILE,
        "authority_set": ledger.AUTHORITY_SET,
        "persistence": ledger_store.status(),
        "witness": {
            "profile": f"INDEPENDENT_WITNESS_STORE ({os.path.basename(ledger_store.WITNESS_PATH)})",
            "detail": "Every block hash is copied to a separate SQLite database through a separate "
                      "connection. Verification compares the two; a rewrite of the main ledger "
                      "cannot update the witness, so it is reported as a divergence.",
        },
        "blocks": ledger.blocks(limit=limit, case_id=case_id),
        "verification": ledger.verify_chain(),
        "stored_fields": ["evidence_id", "case_id", "sha256 payload hash", "timestamp",
                          "critical event type", "integrity status"],
        "never_stored": ["evidence content", "personal data", "case narrative"],
    }


@router.post("/ledger/verify")
def verify_ledger(principal: Principal = Depends(require_permission("ledger:read"))) -> dict[str, Any]:
    result = ledger.verify_chain()
    audit_log.record(principal.user_id, principal.role, "LEDGER_VERIFIED",
                     status="SUCCESS" if result["chain_intact"] else "FAILED",
                     detail=f"{result['blocks']} blocks verified; intact={result['chain_intact']}.")
    return result


@router.get("/integrity/overview")
def integrity_overview(principal: Principal = Depends(require_permission("evidence:read"))
                       ) -> dict[str, Any]:
    allowed = set(authorized_case_ids(principal))
    rows = [e for e in relational.all("evidence")
            if e["case_id"] in allowed and not e.get("demo_probe")]
    return {
        "summary": evidence_agent.registry_summary(),
        "items": [{
            "evidence_id": e["evidence_id"], "case_id": e["case_id"], "type": e["evidence_type"],
            "sha256": e.get("sha256", ""), "integrity_status": e.get("integrity_status"),
            "verification_status": e.get("verification_status"),
            "last_checked": next((p["timestamp"] for p in reversed(e.get("provenance", []))
                                  if p["step"] == "INTEGRITY_CHECK"), None),
            "notes": e.get("notes", ""),
        } for e in rows],
        "algorithm": "SHA-256",
        "policy": "Original evidence objects are never modified by the application. "
                  "A mismatch preserves the registered hash and flags the object as suspect.",
    }


@router.post("/integrity/run-all")
def run_all_integrity(principal: Principal = Depends(require_permission("evidence:integrity"))
                      ) -> dict[str, Any]:
    allowed = set(authorized_case_ids(principal))
    results = [evidence_agent.integrity_check(e["evidence_id"], actor=principal.user_id)
               for e in relational.all("evidence")
               if e["case_id"] in allowed and not e.get("demo_probe")]
    mismatches = [r for r in results if r.get("status") != "VERIFIED"]
    audit_log.record(principal.user_id, principal.role, "INTEGRITY_SWEEP",
                     status="MISMATCH" if mismatches else "SUCCESS",
                     detail=f"{len(results)} objects checked, {len(mismatches)} mismatch(es).")
    return {"checked": len(results), "mismatches": len(mismatches), "results": results}


@router.get("/audit/chain")
def audit_chain(principal: Principal = Depends(require_permission("audit:read"))) -> dict[str, Any]:
    """Verify the audit hash-chain and the ledger chain (with witness) together."""
    audit_result = audit_log.verify_chain()
    ledger_result = ledger.verify_chain()
    return {
        "audit_chain": audit_result,
        "ledger_chain": ledger_result,
        "both_intact": bool(audit_result["chain_intact"] and ledger_result["chain_intact"]),
    }
