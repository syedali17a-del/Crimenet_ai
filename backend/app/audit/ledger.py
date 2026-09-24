"""Permissioned ledger (tamper-evident chain-of-custody).

IMPORTANT LABELLING: no production blockchain network is running in this
environment, and this module deliberately uses no blockchain library and no
network dependency. It implements a clearly-labelled *permissioned-ledger
abstraction*: an append-only, SHA-256 hash-chained block sequence with a
notary-style authority set, persisted to SQLite so the chain survives process
restart, and mirrored block-by-block into an INDEPENDENT witness store
(`app/audit/ledger_store.py`) that the ledger never reads back from.

The interface (append / verify_chain / blocks) matches what a Hyperledger-style
permissioned deployment would expose, so a real network can be swapped in without
changing callers.

Only integrity metadata is written to the chain - never evidence content:
  evidence_id, case_id, SHA-256 hash, timestamp, critical event, integrity status.
"""
from __future__ import annotations

import json
import threading
from typing import Any, Optional

from ..models.domain import LedgerBlock, now_iso
from ..security.crypto import sha256_text
from . import ledger_store

LEDGER_PROFILE = "PERMISSIONED_LEDGER_ABSTRACTION (development notary profile - not a production blockchain network)"
AUTHORITY_SET = ["crimenet-evidence-notary-01", "crimenet-audit-notary-02"]

_lock = threading.RLock()


def _block_from_row(row: dict[str, Any]) -> LedgerBlock:
    return LedgerBlock(
        index=int(row["idx"]), timestamp=row["timestamp"], event_type=row["event_type"],
        payload_hash=row["payload_hash"], previous_hash=row["previous_hash"],
        block_hash=row["block_hash"], recorded_by=row["recorded_by"],
        evidence_id=row["evidence_id"], case_id=row["case_id"],
        integrity_status=row["integrity_status"],
    )


def ensure_genesis() -> None:
    """Recreate the genesis block if the durable chain is empty (first run or reset)."""
    with _lock:
        if ledger_store.ledger_store.count() == 0:
            payload_hash = sha256_text("CRIMENET-AI-GENESIS")
            block_hash = sha256_text("0" * 64 + payload_hash)
            ts = now_iso()
            row = dict(idx=0, timestamp=ts, event_type="GENESIS", evidence_id=None,
                       case_id=None, payload_hash=payload_hash, payload="{}",
                       previous_hash="0" * 64,
                       block_hash=block_hash, integrity_status="SEALED",
                       recorded_by="crimenet-evidence-notary-01")
            ledger_store.ledger_store.execute(
                "INSERT INTO blocks (idx, timestamp, event_type, evidence_id, case_id, "
                "payload_hash, payload, previous_hash, block_hash, integrity_status, recorded_by) "
                "VALUES (:idx, :timestamp, :event_type, :evidence_id, :case_id, :payload_hash, "
                ":payload, :previous_hash, :block_hash, :integrity_status, :recorded_by)", row)
            ledger_store.publish_to_witness(0, block_hash, ts)


def append(event_type: str, payload: dict[str, Any], evidence_id: Optional[str] = None,
           case_id: Optional[str] = None, recorded_by: str = "crimenet-evidence-notary-01",
           integrity_status: str = "SEALED") -> LedgerBlock:
    ensure_genesis()
    with _lock:
        rows = ledger_store.ledger_store.query("SELECT * FROM blocks ORDER BY idx DESC LIMIT 1")
        prev = _block_from_row(rows[0])
        payload_hash = sha256_text(json.dumps(payload, sort_keys=True, default=str))
        index = prev.index + 1
        ts = now_iso()
        block_hash = sha256_text(f"{index}|{ts}|{event_type}|{payload_hash}|{prev.block_hash}")
        payload_json = json.dumps(payload, sort_keys=True, default=str)
        values = dict(idx=index, timestamp=ts, event_type=event_type, evidence_id=evidence_id,
                      case_id=case_id, payload_hash=payload_hash, payload=payload_json,
                      previous_hash=prev.block_hash, block_hash=block_hash,
                      integrity_status=integrity_status, recorded_by=recorded_by)
        ledger_store.ledger_store.execute(
            "INSERT INTO blocks (idx, timestamp, event_type, evidence_id, case_id, payload_hash, "
            "payload, previous_hash, block_hash, integrity_status, recorded_by) VALUES "
            "(:idx, :timestamp, :event_type, :evidence_id, :case_id, :payload_hash, :payload, "
            ":previous_hash, :block_hash, :integrity_status, :recorded_by)", values)
        # The witness receives the hash through a different code path and a
        # different database; a later rewrite of ledger.db alone cannot update it.
        ledger_store.publish_to_witness(index, block_hash, ts)
        return _block_from_row(values)


def _all() -> list[LedgerBlock]:
    ensure_genesis()
    return [_block_from_row(r) for r in
            ledger_store.ledger_store.query("SELECT * FROM blocks ORDER BY idx ASC")]


def blocks(limit: int = 200, case_id: Optional[str] = None) -> list[dict[str, Any]]:
    items = [b.model_dump() for b in _all()]
    if case_id:
        items = [b for b in items if b.get("case_id") in (case_id, None)]
    return list(reversed(items))[:limit]


def blocks_for_evidence(evidence_id: str) -> list[dict[str, Any]]:
    return [b.model_dump() for b in _all() if b.evidence_id == evidence_id]


def registered_digest(evidence_id: str) -> Optional[str]:
    """The SHA-256 the ledger recorded when this evidence was registered.

    This is the third, independently-held leg of the integrity check: the ledger
    keeps its own copy of the digest taken at intake, so rewriting the object and
    the registry row together is not enough to hide a change.
    """
    payload = ledger_store.ledger_store.payload_for(evidence_id, "EVIDENCE_REGISTERED")
    if payload is None:
        return None
    return payload.get("sha256")


def verify_chain(with_witness: bool = True) -> dict[str, Any]:
    chain = _all()
    broken: list[int] = []
    for i, block in enumerate(chain):
        if i == 0:
            continue
        prev = chain[i - 1]
        recomputed = sha256_text(
            f"{block.index}|{block.timestamp}|{block.event_type}|{block.payload_hash}|{prev.block_hash}"
        )
        if block.previous_hash != prev.block_hash or recomputed != block.block_hash:
            broken.append(block.index)
        # a gap in the index sequence means a block was deleted
    expected = list(range(len(chain)))
    if [b.index for b in chain] != expected:
        missing = sorted(set(expected) - {b.index for b in chain})
        broken.extend(missing)

    result: dict[str, Any] = {
        "profile": LEDGER_PROFILE,
        "authority_set": AUTHORITY_SET,
        "persistence": ledger_store.status()["engine"],
        "ledger_path": ledger_store.LEDGER_PATH,
        "blocks": len(chain),
        "chain_intact": not broken,
        "broken_blocks": sorted(set(broken)),
        "head_hash": chain[-1].block_hash if chain else None,
        "verified_at": now_iso(),
    }
    if with_witness:
        witness = ledger_store.compare_with_witness([b.model_dump() for b in chain])
        result["witness"] = witness
        result["chain_intact"] = bool(result["chain_intact"] and witness["witness_agrees"])
    return result


def reset() -> None:
    with _lock:
        ledger_store.reset()
    ensure_genesis()
