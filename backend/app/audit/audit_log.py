"""Append-only audit trail (PostgreSQL 'audit' table) with per-record SHA-256.

PHASE 4: records are now HASH-CHAINED. Each record stores
  hash       = SHA-256 of its own canonical body (per-record integrity)
  prev_hash  = the `hash` of the preceding audit record
  chain_hash = SHA-256("{prev_hash}|{body}")
so deleting or editing any single record breaks the recomputation of every later
record, and the break is reported by `verify_chain()` rather than being invisible."""
from __future__ import annotations

import itertools
import json
from typing import Any, Optional

from ..database.postgres import relational
from ..models.domain import AuditRecord, now_iso
from ..security.crypto import sha256_text

_counter = itertools.count(1)
GENESIS_HASH = "0" * 64


def _chain_head() -> str:
    """Hash of the newest audit record, or the genesis constant for an empty log."""
    rows = relational.all("audit")
    if not rows:
        return GENESIS_HASH
    latest = max(rows, key=lambda r: r["audit_id"])
    return latest.get("chain_hash") or latest.get("hash") or GENESIS_HASH


def record(user_id: str, role: str, action: str, case_id: Optional[str] = None,
           object_id: Optional[str] = None, status: str = "SUCCESS",
           detail: str = "") -> AuditRecord:
    audit_id = f"AUD-{next(_counter):05d}"
    ts = now_iso()
    body = json.dumps({
        "audit_id": audit_id, "timestamp": ts, "user_id": user_id, "role": role,
        "action": action, "case_id": case_id, "object_id": object_id,
        "status": status, "detail": detail,
    }, sort_keys=True)
    prev_hash = _chain_head()
    rec = AuditRecord(
        audit_id=audit_id, timestamp=ts, user_id=user_id, role=role, action=action,
        case_id=case_id, object_id=object_id, status=status, detail=detail,
        hash=sha256_text(body),
        prev_hash=prev_hash,
        chain_hash=sha256_text(f"{prev_hash}|{body}"),
    )
    relational.insert("audit", audit_id, rec.model_dump())
    return rec


def query(case_id: Optional[str] = None, user_id: Optional[str] = None,
          action: Optional[str] = None, limit: int = 250) -> list[dict[str, Any]]:
    rows = relational.all("audit")
    if case_id:
        rows = [r for r in rows if r.get("case_id") == case_id]
    if user_id:
        rows = [r for r in rows if r.get("user_id") == user_id]
    if action:
        rows = [r for r in rows if action.lower() in r.get("action", "").lower()]
    rows.sort(key=lambda r: r["audit_id"], reverse=True)
    return rows[:limit]


def count() -> int:
    return relational.count("audit")


def verify_chain() -> dict[str, Any]:
    """Recompute the audit hash-chain over every stored record."""
    rows = sorted(relational.all("audit"), key=lambda r: r["audit_id"])
    broken: list[str] = []
    prev_hash = GENESIS_HASH
    for row in rows:
        body = json.dumps({
            "audit_id": row["audit_id"], "timestamp": row["timestamp"], "user_id": row["user_id"],
            "role": row["role"], "action": row["action"], "case_id": row.get("case_id"),
            "object_id": row.get("object_id"), "status": row.get("status"),
            "detail": row.get("detail", ""),
        }, sort_keys=True)
        if row.get("prev_hash") not in (None, prev_hash):
            broken.append(row["audit_id"])
        elif row.get("hash") != sha256_text(body):
            broken.append(row["audit_id"])
        elif row.get("chain_hash") != sha256_text(f"{row.get('prev_hash')}|{body}"):
            broken.append(row["audit_id"])
        prev_hash = row.get("chain_hash") or prev_hash
    return {
        "records": len(rows),
        "chained": True,
        "algorithm": "SHA-256 over prev_hash + canonical record body",
        "chain_intact": not broken,
        "broken_records": broken,
        "head_hash": rows[-1]["chain_hash"] if rows else GENESIS_HASH,
        "genesis_hash": GENESIS_HASH,
    }
