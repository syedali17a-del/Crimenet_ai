"""PHASE 4 acceptance - evidence integrity under two realistic tamper scenarios.

Scenario A - INSIDER REWRITE OF THE EVIDENCE OBJECT.
  The attacker replaces the stored object and also overwrites the SHA-256 recorded
  on the evidence row, so object hash == registry hash. A two-way check reports
  VERIFIED. The three-way check compares both against the digest the permissioned
  ledger anchored at registration (separate durable store, separate connection)
  and reports INTEGRITY MISMATCH.

Scenario B - REWRITE OF THE LEDGER ITSELF BY A SKILLED ATTACKER.
  The attacker edits a block in ledger.db and recomputes that block hash and every
  following block hash, so the chain is internally consistent and `verify_chain()`
  alone would accept it. The independent witness store still holds the original
  hashes, so verification reports a divergence.

ISOLATION: the attack runs in a CHILD process against COPIES of ledger.db and
ledger_witness.db in a temporary directory (CRIMENET_LEDGER_PATH /
CRIMENET_LEDGER_WITNESS_PATH point there). The live files are never modified, so
this is safe to run while the API server is up - an earlier version rewrote the
live files in place and could corrupt them under a running server's open
connection (a stale main file restored on top of a newer WAL).

Run:  cd backend && python3 scripts/tamper_test.py
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents import evidence_agent  # noqa: E402
from app.audit import ledger, ledger_store  # noqa: E402
from app.database.object_storage import object_storage  # noqa: E402
from app.database.postgres import relational  # noqa: E402
from app.security.crypto import sha256_bytes, sha256_text  # noqa: E402

PROBE = "EV-9501"
KEY = "tamper_test/probe.txt"
RULE = "=" * 96


def scenario_a() -> bool:
    print(RULE)
    print("SCENARIO A - insider rewrites the object AND the registry hash together")
    print(RULE)
    relational.upsert("evidence", PROBE, {
        "evidence_id": PROBE, "case_id": "CASE-101", "evidence_type": "TEXT", "object_key": KEY,
        "source": "tamper test probe", "verification_status": "UNVERIFIED",
        "processing_status": "UPLOADED", "uploaded_by": "SUP-1100", "sha256": "",
        "integrity_status": "UNCHECKED", "notes": "probe",
    })
    evidence_agent.register_evidence(relational.get("evidence", PROBE),
                                     b"original probe content", "SUP-1100")
    first = evidence_agent.integrity_check(PROBE)
    print(f"1. probe registered, three-way check          : {first['status']}")
    print(f"     object      = {first['legs']['object_storage']['hash'][:32]}...")
    print(f"     registry    = {first['legs']['evidence_registry']['hash'][:32]}...")
    print(f"     ledger      = {str(first['legs']['permissioned_ledger']['hash'])[:32]}...")

    altered = b"probe content REPLACED by an attacker who also had database access"
    object_storage.put_bytes(KEY, altered)
    rec = relational.get("evidence", PROBE)
    rec["sha256"] = sha256_bytes(altered)
    relational.upsert("evidence", PROBE, rec)
    print("\n2. attacker rewrites the object and the registry hash to match it")
    print(f"     two-way check (object == registry) would report : VERIFIED "
          f"({sha256_bytes(altered)[:16]}... == {sha256_bytes(altered)[:16]}...)")

    second = evidence_agent.integrity_check(PROBE)
    print(f"\n3. three-way check                            : {second['status']}")
    print(f"     object agrees with registry : {second['legs']['object_storage']['agrees']}")
    print(f"     registry agrees with ledger : {second['legs']['permissioned_ledger']['agrees']}")
    print(f"     ledger-registered digest    : {str(second['ledger_registered_hash'])[:32]}...")
    print(f"     ledger chain intact         : {second['ledger_chain']['chain_intact']}")
    print(f"     witness agrees              : {second['ledger_chain']['witness']['witness_agrees']}")
    detected = second["status"] != "VERIFIED"
    print(f"\n   RESULT: {'DETECTED' if detected else 'NOT DETECTED'}")
    return detected


def scenario_b() -> bool:
    print()
    print(RULE)
    print("SCENARIO B - skilled attacker rewrites ledger.db and recomputes the chain")
    print(RULE)
    backups = {}
    for path in (ledger_store.LEDGER_PATH, ledger_store.WITNESS_PATH,
                 ledger_store.LEDGER_PATH + "-wal", ledger_store.WITNESS_PATH + "-wal"):
        if os.path.exists(path):
            backups[path] = path + ".tamperbak"
            shutil.copy2(path, backups[path])

    try:
        before = ledger.verify_chain()
        print(f"1. ledger before attack : {before['blocks']} blocks, intact={before['chain_intact']}, "
              f"witness_agrees={before['witness']['witness_agrees']}")

        # --- the attack: edit one historical block's payload and re-link the chain ---
        conn = ledger_store.ledger_store._conn  # noqa: SLF001 - deliberate low-level rewrite
        rows = [dict(r) for r in conn.execute("SELECT * FROM blocks ORDER BY idx ASC").fetchall()]
        target = next((r for r in rows if r["idx"] == 1), rows[-1])
        payload = json.loads(target["payload"])
        payload["sha256"] = hashlib.sha256(b"attacker-controlled digest").hexdigest()
        payload["actor"] = "unknown"
        conn.execute("UPDATE blocks SET payload = ?, payload_hash = ? WHERE idx = ?",
                     (json.dumps(payload, sort_keys=True), sha256_text(json.dumps(payload, sort_keys=True)),
                      target["idx"]))
        # recompute every hash from the edited block forward so the chain is consistent
        prev_hash = rows[0]["block_hash"]
        for row in rows[1:]:
            current = dict(row)
            if current["idx"] >= target["idx"]:
                res = conn.execute("SELECT payload, payload_hash FROM blocks WHERE idx = ?",
                                   (current["idx"],)).fetchone()
                payload_hash = res["payload_hash"]
            else:
                payload_hash = current["payload_hash"]
            block_hash = sha256_text(
                f"{current['idx']}|{current['timestamp']}|{current['event_type']}|"
                f"{payload_hash}|{prev_hash}")
            conn.execute("UPDATE blocks SET previous_hash = ?, block_hash = ? WHERE idx = ?",
                         (prev_hash, block_hash, current["idx"]))
            prev_hash = block_hash
        conn.commit()
        print("2. attacker edited block "
              f"{target['idx']} and recomputed all following block hashes")

        after = ledger.verify_chain()
        witness = after["witness"]
        print(f"3. chain recomputation alone                  : intact={after['chain_intact'] and not witness['divergent_blocks']}")
        print(f"   index-sequence / hash-link check           : broken_blocks={after['broken_blocks']}")
        print(f"   WITNESS comparison                         : agrees={witness['witness_agrees']}, "
              f"divergent_blocks={witness['divergent_blocks']}")
        print(f"   reported chain_intact                      : {after['chain_intact']}")
        detected = not after["chain_intact"] and bool(witness["divergent_blocks"])
        print(f"\n   RESULT: {'DETECTED' if detected else 'NOT DETECTED'}")
        return detected
    finally:
        # the restore only affects the TEMPORARY COPY (run_in_isolation guarantee)
        for path, backup in backups.items():
            shutil.copy2(backup, path)
            os.remove(backup)
        ledger_store.ledger_store._conn.close()  # noqa: SLF001
        ledger_store.ledger_store.__init__(ledger_store.LEDGER_PATH,  # re-open clean
                                           ledger_store._SCHEMA, "ledger")


def run_in_isolation() -> int:
    """Copy the durable stores to a temp dir and run both scenarios there."""
    tmp = tempfile.mkdtemp(prefix="crimenet-tamper-")
    pairs = ((ledger_store.LEDGER_PATH, os.path.join(tmp, "ledger.db")),
             (ledger_store.WITNESS_PATH, os.path.join(tmp, "witness.db")))
    for src, dst in pairs:
        for suffix in ("", "-wal", "-shm"):
            if os.path.exists(src + suffix):
                shutil.copy2(src + suffix, dst + suffix)
    print("ISOLATION: running against copies of the durable stores, the live files")
    print(f"           are untouched (temp dir: {tmp})\n", flush=True)
    env = dict(os.environ, CRIMENET_LEDGER_PATH=pairs[0][1],
               CRIMENET_LEDGER_WITNESS_PATH=pairs[1][1], CRIMENET_TAMPER_CHILD="1")
    result = subprocess.run([sys.executable, os.path.abspath(__file__), "--child"],
                            env=env, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    shutil.rmtree(tmp, ignore_errors=True)
    return result.returncode


def main() -> int:
    if os.environ.get("CRIMENET_TAMPER_CHILD") != "1":
        return run_in_isolation()
    a = scenario_a()
    b = scenario_b()
    print()
    print(RULE)
    print(f"PHASE 4 ACCEPTANCE: object+DB rewrite detected = {a} | ledger rewrite detected = {b}")
    print(RULE)
    return 0 if (a and b) else 1


if __name__ == "__main__":
    raise SystemExit(main())
