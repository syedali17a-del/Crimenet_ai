"""SOURCE TRUST - how much weight does an uploaded document carry?

WHY THIS EXISTS
    Extracted entities and relationships enter the graph as LOW/UNVERIFIED candidates
    regardless of who uploaded them, and nothing is auto-merged. That part was already
    right. What was missing is the next question: when two documents appear to support the
    same candidate relationship, do they support it equally?

    They do not. A FIR registered through the officer console is a different kind of
    object from an anonymous bulk export or an external submission, and a system that
    treats them as interchangeable can be walked into a false HIGH-confidence finding by
    uploading the same claim twice from a low-trust path. This module makes that
    asymmetry explicit and machine-checked.

    Nothing here deletes or suppresses a document: a low-trust upload still enters the
    registry, still gets its SHA-256, still produces candidates - it just cannot, on its
    own, lift a candidate relationship into the confident band.

CATEGORIES
    OFFICER_UPLOAD      weight 1.00  An officer with case access registered it through the
                                     console: typed/pasted text, or a file attached to a
                                     specific case. The normal evidential path.
    BULK_IMPORT         weight 0.60  A machine-readable records export (CDR / bank CSV)
                                     registered by an officer. Real data, but produced by a
                                     system rather than a human, so format and completeness
                                     are not vouched for by a person.
    EXTERNAL_SUBMISSION weight 0.35  Declared as arriving from outside the force console
                                     (partner feed, public submission, third-party export).
                                     Never enough on its own to reach the confident band.

LADDER (used by the corroboration engine and by POST /api/analysis/evidence-support)
    HIGH    requires weighted support >= 2.00 AND >= 2 independent sources
    MEDIUM  requires weighted support >= 1.00
    LOW     everything else
    A single EXTERNAL_SUBMISSION (0.35) cannot reach HIGH, and neither can two of them
    (0.70). Two independent OFFICER_UPLOAD documents (2.00) can.
"""
from __future__ import annotations

from typing import Any, Optional

from ..database.postgres import relational

TRUST_OFFICER_UPLOAD = "OFFICER_UPLOAD"
TRUST_BULK_IMPORT = "BULK_IMPORT"
TRUST_EXTERNAL_SUBMISSION = "EXTERNAL_SUBMISSION"

SOURCE_TRUST_WEIGHTS: dict[str, float] = {
    TRUST_OFFICER_UPLOAD: 1.00,
    TRUST_BULK_IMPORT: 0.60,
    TRUST_EXTERNAL_SUBMISSION: 0.35,
}
SOURCE_TRUST_CATEGORIES = tuple(SOURCE_TRUST_WEIGHTS)

SOURCE_TRUST_EXPLANATION: dict[str, str] = {
    TRUST_OFFICER_UPLOAD: "Registered through the officer console by a user with upload "
                          "rights on the case (typed text or an attached file).",
    TRUST_BULK_IMPORT: "A structured records export (CDR / bank statement) registered by an "
                       "officer; machine-produced, so completeness is not vouched for by a "
                       "person.",
    TRUST_EXTERNAL_SUBMISSION: "Declared as arriving from outside the console (partner feed, "
                               "public or third-party submission).",
}

HIGH_MIN_WEIGHT = 2.0
MEDIUM_MIN_WEIGHT = 1.0
HIGH_MIN_SOURCES = 2

# Structured exports are detected from the file, not from the evidence_type alone, so a
# FIR PDF attached by an officer stays an officer upload.
_BULK_FORMATS = ("cdr", "bank", "csv")


def weight(source_trust: Optional[str]) -> float:
    return SOURCE_TRUST_WEIGHTS.get((source_trust or "").upper(), SOURCE_TRUST_WEIGHTS[TRUST_OFFICER_UPLOAD])


def derive_source_trust(explicit: Optional[str], *, evidence_type: str = "",
                        structured_kind: Optional[str] = None) -> str:
    """Pick the category for a new evidence record.

    An explicit declaration wins (it is what an integration or a console operator says the
    document is). Otherwise: a detected structured records export is BULK_IMPORT, and
    everything else registered through the console is OFFICER_UPLOAD.
    """
    if explicit:
        candidate = explicit.strip().upper()
        if candidate in SOURCE_TRUST_CATEGORIES:
            return candidate
    if structured_kind and str(structured_kind).lower() in _BULK_FORMATS:
        return TRUST_BULK_IMPORT
    if evidence_type.upper() in {"CSV"}:
        return TRUST_BULK_IMPORT
    return TRUST_OFFICER_UPLOAD


def trust_of(evidence_row: dict[str, Any] | None) -> str:
    """Trust category of a stored evidence record.

    Records written before this field existed (and the seeded synthetic documents, which
    are curator-provided case papers) are treated as OFFICER_UPLOAD - the default, stated
    here rather than left implicit.
    """
    if not evidence_row:
        return TRUST_OFFICER_UPLOAD
    return (evidence_row.get("source_trust") or TRUST_OFFICER_UPLOAD).upper()


def _rows(evidence_ids: list[str]) -> list[dict[str, Any]]:
    out = []
    for eid in evidence_ids:
        row = relational.get("evidence", eid)
        if row:
            out.append(row)
    return out


def support_assessment(evidence_ids: list[str]) -> dict[str, Any]:
    """Weighted support level reachable from this set of evidence.

    Independent sources are counted by registered `source` name (two rows from the same
    named source are one source), and the weight of each independent source is the highest
    weight among its rows.
    """
    rows = _rows(evidence_ids)
    by_source: dict[str, dict[str, Any]] = {}
    for row in rows:
        source = (row.get("source") or "unknown").strip()
        entry = by_source.setdefault(source, {
            "source": source, "weight": 0.0, "evidence_ids": [],
            "source_trust": trust_of(row),
        })
        entry["evidence_ids"].append(row["evidence_id"])
        entry["weight"] = max(entry["weight"], weight(trust_of(row)))
        if weight(trust_of(row)) == entry["weight"]:
            entry["source_trust"] = trust_of(row)

    total = round(sum(e["weight"] for e in by_source.values()), 4)
    independent_sources = len(by_source)

    if total >= HIGH_MIN_WEIGHT and independent_sources >= HIGH_MIN_SOURCES:
        level, why = "HIGH", (f"weighted support {total:.2f} from {independent_sources} independent "
                              f"sources reaches the confident band")
    elif total >= MEDIUM_MIN_WEIGHT:
        level, why = "MEDIUM", (f"weighted support {total:.2f} clears the reviewable-candidate "
                                f"band but not the confident band"
                                if total < HIGH_MIN_WEIGHT else
                                f"weighted support {total:.2f} but only {independent_sources} "
                                f"independent source - independence is required for HIGH")
    else:
        level, why = "LOW", (f"weighted support {total:.2f} from {independent_sources} source(s) "
                             f"stays below the reviewable-candidate band")

    weakest = min((e["source_trust"] for e in by_source.values()), key=lambda t: weight(t),
                  default=None)
    return {
        "evidence_ids": [r["evidence_id"] for r in rows],
        "missing_evidence_ids": [e for e in evidence_ids if e not in
                                 {r["evidence_id"] for r in rows}],
        "sources": sorted(by_source.values(), key=lambda e: -e["weight"]),
        "independent_sources": independent_sources,
        "weighted_support": total,
        "support_level_reachable": level,
        "explanation": why,
        "lowest_trust_source": weakest,
        "ladder": {
            "HIGH": f"weighted support >= {HIGH_MIN_WEIGHT:.2f} and >= {HIGH_MIN_SOURCES} "
                    f"independent sources",
            "MEDIUM": f"weighted support >= {MEDIUM_MIN_WEIGHT:.2f}",
            "LOW": "anything below that",
        },
        "weights": SOURCE_TRUST_WEIGHTS,
        "policy_note": "Low-trust evidence is never discarded or hidden; it simply cannot lift "
                       "a candidate into the confident band on its own.",
    }


def cap_level(level: str, assessment: dict[str, Any]) -> str:
    """Cap an existing support level by what the evidence actually supports."""
    order = {"INSUFFICIENT": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
    reachable = assessment["support_level_reachable"]
    return level if order.get(level, 0) <= order.get(reachable, 0) else reachable
