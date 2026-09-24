"""Read the live synthetic dataset straight out of the application seed file.

We parse ``backend/app/database/seed.py`` with :mod:`ast` instead of importing it,
because importing pulls in FastAPI/spaCy. Parsing guarantees the exported dataset
files are byte-for-byte consistent with what the running application serves.
"""
from __future__ import annotations

import ast
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "backend" / "app" / "database" / "seed.py"

WANTED = [
    "CLASSIFICATION", "USERS", "CASES", "LOCATIONS", "PERSONS", "VEHICLES",
    "PHONES", "ACCOUNTS", "ORGS", "DEVICES", "EVIDENCE_DOCS", "RELATIONSHIPS",
    "EVENTS", "CONTRADICTIONS",
]


def _load() -> dict[str, Any]:
    tree = ast.parse(SEED.read_text(encoding="utf-8"))
    out: dict[str, Any] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                name = getattr(tgt, "id", None)
                if name in WANTED:
                    out[name] = ast.literal_eval(node.value)
        elif isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) in WANTED:
            out[node.target.id] = ast.literal_eval(node.value)
    missing = [w for w in WANTED if w not in out]
    if missing:
        raise RuntimeError(f"could not extract from seed.py: {missing}")
    return out


_D = _load()

CLASSIFICATION: str = _D["CLASSIFICATION"]
USERS: list[dict] = _D["USERS"]
CASES: list[dict] = _D["CASES"]
LOCATIONS: list[tuple] = _D["LOCATIONS"]
PERSONS: list[tuple] = _D["PERSONS"]
VEHICLES: list[tuple] = _D["VEHICLES"]
PHONES: list[tuple] = _D["PHONES"]
ACCOUNTS: list[tuple] = _D["ACCOUNTS"]
ORGS: list[tuple] = _D["ORGS"]
DEVICES: list[tuple] = _D["DEVICES"]
EVIDENCE_DOCS: list[dict] = _D["EVIDENCE_DOCS"]
RELATIONSHIPS: list[tuple] = _D["RELATIONSHIPS"]
EVENTS: list[tuple] = _D["EVENTS"]
CONTRADICTIONS: list[dict] = _D["CONTRADICTIONS"]

# Convenience lookups -------------------------------------------------------
CASE_BY_ID = {c["case_id"]: c for c in CASES}
USER_BY_ID = {u["user_id"]: u for u in USERS}
PERSON_BY_ID = {p[0]: p for p in PERSONS}
LOC_BY_ID = {l[0]: l for l in LOCATIONS}
LOC_BY_NAME = {l[1].upper(): l for l in LOCATIONS}
EVIDENCE_BY_ID = {e["evidence_id"]: e for e in EVIDENCE_DOCS}
PERSON_BY_NAME = {p[1]: p for p in PERSONS}


def person_of_phone(number: str) -> tuple | None:
    for p in PERSONS:
        if number in (p[3].get("phones") or []):
            return p
    return None


def person_of_account(number: str) -> tuple | None:
    for p in PERSONS:
        if number in (p[3].get("accounts") or []):
            return p
    return None


def person_of_vehicle(plate: str) -> list[tuple]:
    return [p for p in PERSONS if plate in (p[3].get("vehicles") or [])]


def transactions() -> list[dict[str, Any]]:
    """Byte-identical replica of ``seed._transactions`` (same RNG seed 42)."""
    rng = random.Random(42)
    rows: list[dict[str, Any]] = []
    counter = 1
    base = datetime(2025, 8, 18)
    for day in range(4):
        for _ in range(2):
            ts = base + timedelta(days=day, hours=rng.randint(9, 17), minutes=rng.randint(0, 59))
            rows.append({
                "txn_id": f"TXN-{counter:04d}", "account_id": "ACC-001", "case_id": "CASE-305",
                "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "amount": round(rng.uniform(1500, 9000), 2), "counterparty": "ACC-002",
                "evidence_id": "EV-3070", "classification": CLASSIFICATION,
            })
            counter += 1
    burst = datetime(2025, 8, 22, 14, 0)
    for i in range(50):
        ts = burst + timedelta(seconds=i * 70)
        rows.append({
            "txn_id": f"TXN-{counter:04d}", "account_id": "ACC-001", "case_id": "CASE-305",
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "amount": round(rng.uniform(4000, 48000), 2),
            "counterparty": "ACC-002" if i % 3 else "ACC-003",
            "evidence_id": "EV-3070", "classification": CLASSIFICATION,
        })
        counter += 1
    for day in range(5):
        ts = datetime(2025, 8, 20) + timedelta(days=day, hours=11)
        rows.append({
            "txn_id": f"TXN-{counter:04d}", "account_id": "ACC-002", "case_id": "CASE-305",
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "amount": round(rng.uniform(2000, 12000), 2), "counterparty": "ACC-001",
            "evidence_id": "EV-3070", "classification": CLASSIFICATION,
        })
        counter += 1
    return rows


if __name__ == "__main__":
    print("cases", len(CASES), "| persons", len(PERSONS), "| vehicles", len(VEHICLES),
          "| locations", len(LOCATIONS), "| phones", len(PHONES), "| accounts", len(ACCOUNTS),
          "| orgs", len(ORGS), "| devices", len(DEVICES), "| evidence", len(EVIDENCE_DOCS),
          "| rels", len(RELATIONSHIPS), "| events", len(EVENTS),
          "| txns", len(transactions()))
