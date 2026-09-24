"""EVIDENCE & PROVENANCE AGENT.

Responsibilities: registration hashing (SHA-256), chain-of-custody provenance,
integrity verification, permissioned-ledger anchoring.

The original evidence object is never modified by this agent.
"""
from __future__ import annotations

from typing import Any, Optional

from ..audit import ledger
from ..database.object_storage import object_storage
from ..database.postgres import relational
from ..models.domain import now_iso
from ..security.crypto import sha256_bytes

AGENT_NAME = "EVIDENCE_PROVENANCE_AGENT"


def register_evidence(evidence: dict[str, Any], content: bytes, actor: str) -> dict[str, Any]:
    """Write-once intake: store blob, compute registration hash, anchor to ledger."""
    object_storage.put_bytes(evidence["object_key"], content)
    digest = sha256_bytes(content)
    evidence["sha256"] = digest
    evidence["integrity_status"] = "VERIFIED"
    evidence.setdefault("provenance", []).append({
        "step": "INTAKE",
        "actor": actor,
        "timestamp": now_iso(),
        "detail": f"Registered into evidence registry; SHA-256 computed over {len(content)} bytes.",
        "hash": digest,
    })
    relational.upsert("evidence", evidence["evidence_id"], evidence)
    block = ledger.append(
        "EVIDENCE_REGISTERED",
        {"evidence_id": evidence["evidence_id"], "case_id": evidence["case_id"],
         "sha256": digest, "source": evidence.get("source"), "actor": actor},
        evidence_id=evidence["evidence_id"], case_id=evidence["case_id"],
    )
    return {"evidence": evidence, "sha256": digest, "ledger_block": block.model_dump()}


def integrity_check(evidence_id: str, actor: str = "system") -> dict[str, Any]:
    """PHASE 4 - THREE-WAY integrity check.

    Three independently-stored values must agree:

      leg 1  OBJECT   SHA-256 recomputed from the bytes currently in object storage
      leg 2  REGISTRY SHA-256 recorded on the evidence row at intake
      leg 3  LEDGER   SHA-256 the permissioned ledger recorded in its
                      EVIDENCE_REGISTERED block, which lives in a separate durable
                      store (ledger.db) that the evidence tables never touch

    A single attacker who rewrites the stored object and the registry row together
    makes legs 1 and 2 agree - the old two-way check would have reported VERIFIED.
    Leg 3 still disagrees, so the rewrite is reported as INTEGRITY_MISMATCH. The
    ledger's own chain (and the independent witness copy of every block hash) is
    then re-verified and reported alongside.
    """
    ev = relational.get("evidence", evidence_id)
    if not ev:
        return {"agent": AGENT_NAME, "found": False, "status": "NOT_FOUND",
                "message": f"Evidence {evidence_id} is not present in the registry."}

    content = object_storage.get_bytes(ev["object_key"])
    if content is None:
        ev["integrity_status"] = "MISMATCH"
        relational.upsert("evidence", evidence_id, ev)
        return {
            "agent": AGENT_NAME, "found": True, "evidence_id": evidence_id,
            "status": "OBJECT_MISSING",
            "registered_hash": ev.get("sha256"), "current_hash": None,
            "message": "Evidence object is missing from object storage. Chain of custody broken.",
            "ledger": ledger.blocks_for_evidence(evidence_id),
        }

    current = sha256_bytes(content)
    registered = ev.get("sha256")
    ledger_digest = ledger.registered_digest(evidence_id)
    object_ok = current == registered
    ledger_ok = ledger_digest is None or ledger_digest == registered
    match = bool(object_ok and ledger_ok)
    ev["integrity_status"] = "VERIFIED" if match else "MISMATCH"
    ev.setdefault("provenance", []).append({
        "step": "INTEGRITY_CHECK",
        "actor": actor,
        "timestamp": now_iso(),
        "detail": "Three-way check: " +
                  ("object, registry and ledger digests all agree." if match else
                   "MISMATCH - " + "; ".join(
                       [t for t in ("" if object_ok else "object differs from the registry digest",
                                    "" if ledger_ok else
                                    "registry digest differs from the digest anchored in the ledger")
                        if t]) + "."),
        "hash": current,
    })
    relational.upsert("evidence", evidence_id, ev)

    block = ledger.append(
        "INTEGRITY_CHECK",
        {"evidence_id": evidence_id, "registered_hash": registered, "current_hash": current,
         "ledger_registered_hash": ledger_digest, "result": "MATCH" if match else "MISMATCH",
         "actor": actor},
        evidence_id=evidence_id, case_id=ev["case_id"],
        integrity_status="VERIFIED" if match else "INTEGRITY_MISMATCH",
    )

    return {
        "agent": AGENT_NAME,
        "found": True,
        "evidence_id": evidence_id,
        "case_id": ev["case_id"],
        "status": "VERIFIED" if match else "INTEGRITY_MISMATCH",
        "registered_hash": registered,
        "current_hash": current,
        "ledger_registered_hash": ledger_digest,
        "legs": {
            "object_storage": {"hash": current, "agrees": object_ok},
            "evidence_registry": {"hash": registered, "agrees": object_ok},
            "permissioned_ledger": {"hash": ledger_digest,
                                    "agrees": ledger_ok,
                                    "note": "digest anchored in the ledger's EVIDENCE_REGISTERED block"},
        },
        "ledger_chain": ledger.verify_chain(),
        "algorithm": "SHA-256",
        "checked_at": now_iso(),
        "message": ("Object, registry and ledger digests agree. Evidence integrity intact."
                    if match else
                    "INTEGRITY MISMATCH - the three copies of the digest do not agree "
                    "(object / registry / ledger). The original registered hash is preserved; the "
                    "object must be treated as suspect."),
        "ledger_block": block.model_dump(),
        "ledger": ledger.blocks_for_evidence(evidence_id),
        "provenance": ev.get("provenance", []),
    }


def add_provenance(evidence_id: str, step: str, actor: str, detail: str,
                   hash_value: Optional[str] = None) -> Optional[dict[str, Any]]:
    ev = relational.get("evidence", evidence_id)
    if not ev:
        return None
    ev.setdefault("provenance", []).append({
        "step": step, "actor": actor, "timestamp": now_iso(),
        "detail": detail, "hash": hash_value,
    })
    relational.upsert("evidence", evidence_id, ev)
    return ev


def registry_summary() -> dict[str, Any]:
    rows = [e for e in relational.all("evidence") if not e.get("demo_probe")]
    return {
        "total": len(rows),
        "verified": sum(1 for r in rows if r.get("integrity_status") == "VERIFIED"),
        "mismatch": sum(1 for r in rows if r.get("integrity_status") == "MISMATCH"),
        "unchecked": sum(1 for r in rows if r.get("integrity_status") == "UNCHECKED"),
        "human_verified": sum(1 for r in rows if r.get("verification_status") == "HUMAN_VERIFIED"),
    }
