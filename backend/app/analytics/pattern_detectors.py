"""SUSPICIOUS-PATTERN DETECTORS (rule-based).

Requirement #5 asks for detection of "suspicious patterns and unusual activities".
`anomaly.py` covers the second half with a statistical model (Isolation Forest over
per-account transaction behaviour). This module covers patterns that a statistical
model is the wrong tool for: they are defined by an explicit rule, and the rule is the
explanation.

DETECTOR 1 - shared_identifier_cross_case
    An identifier (phone, vehicle, account, device) that appears in the evidence of two
    or more cases which have NO other link between them.

    Why this is worth surfacing: every other signal the correlation engine looks at is
    an *association* (a name that looks similar, a common location). A single identifier
    with nothing else around it is a different shape - one record, replicated across
    otherwise unrelated investigations. It is also a known data-poisoning shape: a file
    uploaded with one borrowed identifier can join two cases on that identifier alone.

    This is deliberately NOT `analytics/cross_case.py`. That engine PROPOSES a candidate
    association and tries to weigh many signals; this detector fires on the opposite
    condition - the identifier is the only thing present, and says so in plain language.

    What counts as "another link", using this product's own stated rules:
      * a candidate PERSON/ALIAS match between the two cases  -> a link
      * a second shared identifier                             -> a link
      * a shared LOCATION                                      -> NOT a link
        (the product states that co-location is not proof of a meeting)
      * events a few days apart                                -> NOT a link
        (cross_case.py: "temporal proximity alone is not an association signal")
    The weak signals are still reported on each finding, so a reviewer can see exactly
    what else the two cases have in common and disagree with the rule if they want to.

Both detectors report ANALYTICAL LEADS. A shared identifier is not proof that two cases
are related, that a person is involved, or that any offence occurred.
"""
from __future__ import annotations

from typing import Any, Optional

from ..database.neo4j_graph import graph_store

AGENT_NAME = "PATTERN_DETECTOR"

DETECTOR_NAME = "shared_identifier_cross_case"
# Identifier types only. A shared LOCATION (co-location) or a shared ORGANISATION is
# common and is not, on its own, a distinguishing pattern; those stay with the
# correlation engine where they are weighed as one signal among several.
IDENTIFIER_TYPES = ("PHONE", "VEHICLE", "ACCOUNT", "DEVICE")
MIN_CASES = 2


def _identifier_case_index() -> dict[tuple[str, str], dict[str, Any]]:
    """(type, normalized) -> the cases and evidence that carry that identifier."""
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for node in graph_store.nodes():
        if node.get("entity_type") not in IDENTIFIER_TYPES:
            continue
        cases = sorted({c for c in (node.get("cases") or []) if c})
        if not cases:
            continue
        key = (node["entity_type"], node.get("normalized") or node.get("label") or node["id"])
        entry = index.setdefault(key, {
            "entity_id": node["id"],
            "entity_type": node["entity_type"],
            "label": node.get("label"),
            "normalized": node.get("normalized"),
            "cases": set(),
            "evidence_ids": set(),
            "verification_status": node.get("verification_status", "UNVERIFIED"),
        })
        entry["cases"].update(cases)
        entry["evidence_ids"].update(e for e in (node.get("evidence_ids") or []) if e)
    return index


# Signals that are not treated as a link between two cases by this product's own rules.
WEAK_SIGNALS = ("location consistency", "temporal relationship")


def _case_pair_signals() -> dict[tuple[str, str], dict[str, list[str]]]:
    """Case-pair -> {"strong": [...], "weak": [...]} as the correlation engine sees it.

    Read from the correlation engine rather than recomputed, so the detector cannot drift
    away from what the rest of the product reports about the same pair.
    """
    from . import cross_case

    out: dict[tuple[str, str], dict[str, list[str]]] = {}
    try:
        result = cross_case.correlate(None)
    except Exception:  # pragma: no cover - correlation failure must not break the detector
        return out
    for assoc in result.get("associations", []):
        pair = (assoc["case_a"], assoc["case_b"])
        entry: dict[str, list[str]] = {"strong": [], "weak": []}
        for signal in assoc.get("signals", []):
            if not signal.get("supports"):
                continue
            name = str(signal.get("signal", ""))
            label = f'{name}: {signal.get("value")}'
            if name.lower().startswith("shared ") or name.lower() not in WEAK_SIGNALS:
                entry["strong"].append(label)
            else:
                entry["weak"].append(label)
        out[pair] = entry
    return out


def shared_identifier_cross_case(case_ids: Optional[list[str]] = None) -> dict[str, Any]:
    """Rule: identifier present in 2+ cases that share nothing else."""
    scope = set(case_ids) if case_ids else None
    pair_signals = _case_pair_signals()
    findings: list[dict[str, Any]] = []

    for (entity_type, key), entry in sorted(_identifier_case_index().items()):
        cases = sorted(c for c in entry["cases"] if (scope is None or c in scope))
        if len(cases) < MIN_CASES:
            continue
        for i, case_a in enumerate(cases):
            for case_b in cases[i + 1:]:
                signals = pair_signals.get((case_a, case_b)) or \
                    pair_signals.get((case_b, case_a)) or {"strong": [], "weak": []}
                # A signal that merely repeats this same identifier is not an
                # independent link; a name match or a second identifier is.
                strong = [s for s in signals["strong"]
                          if not s.lower().startswith("shared ")
                          or (entry["label"] or "").lower() not in s.lower()]
                if strong:
                    continue  # the two cases are connected by something else as well
                weak = signals["weak"]
                noun = {"PHONE": "phone number", "VEHICLE": "vehicle registration",
                        "ACCOUNT": "bank account", "DEVICE": "device"}[entity_type]
                findings.append({
                    "detector": DETECTOR_NAME,
                    "detector_kind": "rule_based",
                    "detector_method": "rule-based (no model, no threshold learned from data)",
                    "pattern": "SHARED_IDENTIFIER_WITHOUT_OTHER_LINK",
                    "identifier_type": entity_type,
                    "identifier": entry["label"],
                    "identifier_normalized": entry["normalized"],
                    "entity_id": entry["entity_id"],
                    "cases": [case_a, case_b],
                    "reason": (f"{noun} {entry['label']} appears in the evidence for {case_a} and "
                               f"{case_b} with no other link between these cases: no shared "
                               f"person or alias, and no second identifier."
                               + (f" The only other things these cases have in common are "
                                  f"{'; '.join(weak)}, neither of which this product treats as "
                                  f"a connection (co-location is not proof of a meeting, and "
                                  f"temporal proximity alone is not an association signal)."
                                  if weak else "")),
                    "weak_signals_not_counted_as_a_link": weak,
                    "why_suspicious": ("A single identifier replicated across otherwise unrelated "
                                       "cases is either a genuine common thread worth an "
                                       "investigator's attention, or a data-quality problem in "
                                       "one of the uploads."),
                    "evidence_ids": sorted(entry["evidence_ids"]),
                    "verification_status": entry["verification_status"],
                    "rule": ("identifier.type in {PHONE, VEHICLE, ACCOUNT, DEVICE} AND "
                             "len(distinct cases) >= 2 AND the correlation engine reports no "
                             "person/alias match and no second identifier for the case pair "
                             "(shared location and event proximity are not counted as a link)"),
                    "label": "Analytical pattern / investigative lead",
                    "interpretation": ("A shared identifier is a lead to check, not proof that the "
                                       "cases are related or that any person is involved in an "
                                       "offence. Co-occurrence of an identifier across cases may "
                                       "also be a data-entry or data-quality artefact."),
                    "requires_review": True,
                })

    return {
        "detector": DETECTOR_NAME,
        "detector_kind": "rule_based",
        "detector_description": ("Flags an identifier (phone, vehicle, account, device) that "
                                 "appears in the evidence of 2+ cases that have no other declared "
                                 "connection."),
        "case_scope": sorted(scope) if scope else "ALL_AUTHORIZED",
        "findings": findings,
        "finding_count": len(findings),
        "sufficient": bool(findings),
        "message": "" if findings else
                   ("No identifier was found in the evidence of two cases that share nothing "
                    "else in the authorized scope."),
        "safety_note": ("A shared identifier is an analytical lead requiring corroboration and "
                        "investigator review. It is not evidence that the cases are related, "
                        "that a person is involved, or that any offence occurred."),
    }


def run_all(case_ids: Optional[list[str]] = None) -> dict[str, Any]:
    """Every rule-based detector, each labelled with its own name."""
    results = [shared_identifier_cross_case(case_ids)]
    return {
        "agent": AGENT_NAME,
        "detectors_run": [r["detector"] for r in results],
        "detector_count": len(results),
        "results": results,
        "total_findings": sum(r["finding_count"] for r in results),
    }
