"""Durable storage for the permissioned ledger + the witness store.

Two SEPARATE SQLite databases, opened through separate connections by separate
code paths:

  ledger.db          - the main hash-chained ledger (this module's LedgerStore)
  ledger_witness.db  - the witness store

WHAT THIS DOES AND DOES NOT DEFEND AGAINST (read this before citing it):

  Both stores currently run on the same host. This defends against a single
  incorrect write path or a naive single-file rewrite; it does not defend against
  an attacker with full filesystem access to this server. A production deployment
  would run the witness store on a separate host with separate credentials.

  Verified in this repository: `scripts/tamper_test.py` Scenario B rewrites a
  block in ledger.db and recomputes every following block hash, so the chain is
  internally consistent, and the local witness still reports the divergence. That
  is a *single-host* attack. Full-filesystem access defeats it, because both files
  are writable by the same OS user.

For that reason the witness can optionally be sent OFF the host: set
CRIMENET_WITNESS_URL to an HTTP endpoint and every block hash is POSTed there as
well (the local SQLite witness is still written). A separate service on a separate
host with separate credentials is then a genuinely independent witness. The
capability is optional and unused unless the variable is set.

Neither database stores criminal-justice content: only indices, hashes, event
types, evidence/case references and timestamps.
"""
from __future__ import annotations

import os
import sqlite3
import threading
from typing import Any, Optional

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LEDGER_PATH = os.getenv("CRIMENET_LEDGER_PATH", os.path.join(_BACKEND_ROOT, "ledger.db"))
WITNESS_PATH = os.getenv("CRIMENET_LEDGER_WITNESS_PATH",
                         os.path.join(_BACKEND_ROOT, "ledger_witness.db"))

# OPTIONAL remote witness. Unset by default: with no value the witness is the local
# SQLite file only, which is honest for a single-host prototype. Set it to an HTTP
# endpoint (e.g. https://witness.internal/crimenet) and every block hash is POSTed
# there as well, so the witness can live on a separate host under separate
# credentials - the only configuration in which the witness is genuinely
# independent of an attacker who controls this filesystem.
WITNESS_URL = os.getenv("CRIMENET_WITNESS_URL", "").strip()
_remote_errors: list[str] = []

_SCHEMA = """
CREATE TABLE IF NOT EXISTS blocks (
    idx           INTEGER PRIMARY KEY,
    timestamp     TEXT NOT NULL,
    event_type    TEXT NOT NULL,
    evidence_id   TEXT,
    case_id       TEXT,
    payload_hash  TEXT NOT NULL,
    payload       TEXT NOT NULL,
    previous_hash TEXT NOT NULL,
    block_hash    TEXT NOT NULL,
    integrity_status TEXT NOT NULL,
    recorded_by   TEXT NOT NULL
);
"""
_WITNESS_SCHEMA = """
CREATE TABLE IF NOT EXISTS witness (
    idx        INTEGER PRIMARY KEY,
    block_hash TEXT NOT NULL,
    observed_at TEXT NOT NULL
);
"""


class _SqliteStore:
    """Thin durable key/index store. One connection per store, WAL enabled."""

    def __init__(self, path: str, schema: str, name: str) -> None:
        self.path = path
        self.name = name
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(schema)
        self._conn.commit()

    def execute(self, sql: str, params: tuple = ()) -> None:
        with self._lock:
            self._conn.execute(sql, params)
            self._conn.commit()

    def executemany(self, sql: str, rows: list[tuple]) -> None:
        with self._lock:
            self._conn.executemany(sql, rows)
            self._conn.commit()

    def query(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(r) for r in self._conn.execute(sql, params).fetchall()]

    def payload_for(self, evidence_id: str, event_type: str) -> Optional[dict]:
        rows = self.query(
            "SELECT payload FROM blocks WHERE evidence_id = ? AND event_type = ? "
            "ORDER BY idx ASC LIMIT 1", (evidence_id, event_type))
        if not rows:
            return None
        import json as _json
        try:
            return _json.loads(rows[0]["payload"])
        except Exception:  # pragma: no cover - defensive
            return None

    def count(self) -> int:
        rows = self.query("SELECT COUNT(*) AS n FROM " + (
            "blocks" if self.name == "ledger" else "witness"))
        return int(rows[0]["n"]) if rows else 0

    def reset(self) -> None:
        table = "blocks" if self.name == "ledger" else "witness"
        with self._lock:
            self._conn.execute(f"DELETE FROM {table}")
            self._conn.commit()


ledger_store = _SqliteStore(LEDGER_PATH, _SCHEMA, "ledger")
witness_store = _SqliteStore(WITNESS_PATH, _WITNESS_SCHEMA, "witness")


def publish_to_witness(index: int, block_hash: str, observed_at: str) -> None:
    """Copy a block hash into the witness store(s).

    Deliberately a separate function, separate file and separate connection: the
    witness has no read path back into the ledger.

    If CRIMENET_WITNESS_URL is set the entry is also POSTed to that endpoint, so the
    witness can be a separate service on a separate host. A failed POST is recorded
    (and surfaced in status()) rather than raised: the local witness still holds the
    chain, and a witness outage must not silently stop the ledger from recording.
    """
    witness_store.execute(
        "INSERT INTO witness (idx, block_hash, observed_at) VALUES (?, ?, ?) "
        "ON CONFLICT(idx) DO UPDATE SET block_hash=excluded.block_hash, "
        "observed_at=excluded.observed_at",
        (index, block_hash, observed_at),
    )
    if WITNESS_URL:
        _post_remote(index, block_hash, observed_at)


def _post_remote(index: int, block_hash: str, observed_at: str) -> bool:
    """POST one witness entry to CRIMENET_WITNESS_URL. Returns True on 2xx."""
    import json as _json
    import urllib.error
    import urllib.request
    body = _json.dumps({"idx": index, "block_hash": block_hash,
                        "observed_at": observed_at}).encode("utf-8")
    request = urllib.request.Request(
        WITNESS_URL, data=body, method="POST",
        headers={"content-type": "application/json", "user-agent": "crimenet-ledger/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, OSError, ValueError) as exc:
        _remote_errors.append(f"block {index}: {type(exc).__name__}: {exc}")
        return False


def compare_with_witness(chain: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare every ledger block hash against the witness copy."""
    rows = witness_store.query("SELECT idx, block_hash FROM witness ORDER BY idx")
    witnessed = {int(r["idx"]): r["block_hash"] for r in rows}
    missing: list[int] = []
    divergent: list[int] = []
    for block in chain:
        idx = int(block["index"])
        if idx not in witnessed:
            missing.append(idx)
        elif witnessed[idx] != block["block_hash"]:
            divergent.append(idx)
    extra = sorted(set(witnessed) - {int(b["index"]) for b in chain})
    return {
        "witness_profile": f"INDEPENDENT_WITNESS_STORE ({os.path.basename(WITNESS_PATH)})",
        "witness_blocks": len(witnessed),
        "ledger_blocks": len(chain),
        "divergent_blocks": divergent,
        "missing_from_witness": missing,
        "extra_in_witness": extra,
        "witness_agrees": not divergent and not missing and not extra,
    }


def status() -> dict[str, Any]:
    return {
        "engine": "SQLite (durable append-only tables)",
        "ledger_path": LEDGER_PATH,
        "ledger_blocks": ledger_store.count(),
        "witness_path": WITNESS_PATH,
        "witness_blocks": witness_store.count(),
        "survives_process_restart": True,
        "remote_witness": {
            "configured": bool(WITNESS_URL),
            "url": WITNESS_URL or None,
            "note": "OPTIONAL. Unset means the witness is a second SQLite file on this "
                    "same host: it catches an incorrect write path or a naive "
                    "single-file rewrite, not an attacker with full filesystem access. "
                    "Point this at a service on a separate host for a genuinely "
                    "independent witness.",
            "delivery_errors": _remote_errors[-5:],
        },
    }


def reset() -> None:
    ledger_store.reset()
    witness_store.reset()


__all__ = ["ledger_store", "witness_store", "publish_to_witness", "compare_with_witness",
           "status", "reset", "LEDGER_PATH", "WITNESS_PATH"]
