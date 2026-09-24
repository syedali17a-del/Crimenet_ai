"""CROSS-CASE CORRELATION.

Detects candidate associations between cases from shared identifiers, name
similarity (RapidFuzz), shared locations and temporal relationships.

Output is always labelled CANDIDATE CROSS-CASE ASSOCIATION - never "confirmed".
"""
from __future__ import annotations

from datetime import datetime
from itertools import combinations
from typing import Any, Optional

from ..agents.resolution_agent import compare_pair, normalize_name
from ..database.neo4j_graph import graph_store
from ..database.postgres import relational
from ..security.pii import mask_node


def _parse(ts: str) -> Optional[datetime]:
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(ts, fmt)
        except Exception:
            continue
    return None


def _entities_by_case() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for node in graph_store.nodes():
        for case_id in node.get("cases", []) or []:
            out.setdefault(case_id, []).append(node)
    return out


def correlate(case_ids: Optional[list[str]] = None) -> dict[str, Any]:
    by_case = _entities_by_case()
    scope = [c for c in (case_ids or list(by_case.keys())) if c in by_case]
    associations: list[dict[str, Any]] = []

    for case_a, case_b in combinations(sorted(scope), 2):
        ents_a, ents_b = by_case[case_a], by_case[case_b]
        signals: list[dict[str, Any]] = []
        evidence_ids: set[str] = set()
        entity_pairs: list[dict[str, Any]] = []
        strength = 0.0

        # --- shared hard identifiers (vehicle / phone / account / device) ---
        hard_types = {"VEHICLE", "PHONE", "ACCOUNT", "DEVICE"}
        idx_a = {e["normalized"]: e for e in ents_a if e.get("entity_type") in hard_types}
        idx_b = {e["normalized"]: e for e in ents_b if e.get("entity_type") in hard_types}
        shared_ids = sorted(set(idx_a) & set(idx_b))
        for sid in shared_ids:
            ea, eb = idx_a[sid], idx_b[sid]
            evidence_ids.update(ea.get("evidence_ids", []) or [])
            evidence_ids.update(eb.get("evidence_ids", []) or [])
            signals.append({
                "signal": f"Shared {ea['entity_type'].lower()}",
                "value": sid,
                "supports": True,
                "detail": f"Identifier {sid} appears in evidence for both {case_a} and {case_b}.",
            })
            strength += 34.0
            entity_pairs.append({"left": ea["id"], "right": eb["id"], "type": ea["entity_type"],
                                 "basis": "exact identifier match"})

        # --- name similarity between persons/aliases -----------------------
        people_a = [e for e in ents_a if e.get("entity_type") in {"PERSON", "ALIAS"}]
        people_b = [e for e in ents_b if e.get("entity_type") in {"PERSON", "ALIAS"}]
        best_name = None
        for pa in people_a:
            for pb in people_b:
                if pa["id"] == pb["id"]:
                    continue
                cmp = compare_pair({**pa, "entity_id": pa["id"]}, {**pb, "entity_id": pb["id"]})
                if cmp["support_level"] in {"HIGH", "MEDIUM"} and (
                        best_name is None or cmp["score"] > best_name["score"]):
                    best_name = cmp
        if best_name:
            signals.append({
                "signal": "Name similarity",
                "value": f"{best_name['left']['label']} ↔ {best_name['right']['label']} "
                         f"({best_name['name_similarity']}%)",
                "supports": True,
                "detail": "RapidFuzz multi-attribute candidate match (not a confirmed identity merge).",
            })
            strength += 22.0 if best_name["support_level"] == "HIGH" else 14.0
            entity_pairs.append({"left": best_name["left"]["entity_id"],
                                 "right": best_name["right"]["entity_id"],
                                 "type": "PERSON", "basis": "fuzzy name + attribute match"})

        # --- shared locations ----------------------------------------------
        loc_a = {e["normalized"] for e in ents_a if e.get("entity_type") == "LOCATION"}
        loc_b = {e["normalized"] for e in ents_b if e.get("entity_type") == "LOCATION"}
        shared_loc = sorted(loc_a & loc_b)
        if shared_loc:
            signals.append({
                "signal": "Location consistency",
                "value": ", ".join(shared_loc[:4]),
                "supports": True,
                "detail": "Both cases contain observations at the same location(s).",
            })
            strength += 12.0

        # --- temporal relationship ------------------------------------------
        ev_a = [e for e in relational.all("events") if e.get("case_id") == case_a]
        ev_b = [e for e in relational.all("events") if e.get("case_id") == case_b]
        gap_days = None
        if ev_a and ev_b:
            ta = [t for t in (_parse(e["timestamp"]) for e in ev_a) if t]
            tb = [t for t in (_parse(e["timestamp"]) for e in ev_b) if t]
            if ta and tb:
                gap_days = min(abs((x - y).days) for x in ta for y in tb)
                signals.append({
                    "signal": "Temporal relationship",
                    "value": f"{gap_days} day(s) between nearest events",
                    "supports": gap_days <= 45,
                    "detail": "Activity in the two cases falls inside a comparable window."
                              if gap_days <= 45 else "Events are temporally distant.",
                })
                if gap_days <= 45:
                    strength += 10.0

        supporting = [s for s in signals if s["supports"]]
        substantive = [s for s in supporting if s["signal"] != "Temporal relationship"]
        if not substantive:
            # temporal proximity alone is not an association signal
            continue

        strength = round(min(strength, 97.0), 1)
        if strength >= 70 and len(supporting) >= 3:
            support_level = "HIGH"
        elif strength >= 45 and len(supporting) >= 2:
            support_level = "MEDIUM"
        else:
            support_level = "LOW"

        for e in list(ents_a) + list(ents_b):
            for evid in (e.get("evidence_ids") or []):
                if e.get("normalized") in shared_ids or e.get("entity_type") in {"PERSON", "ALIAS"}:
                    evidence_ids.add(evid)

        link_id = f"XC-{case_a.split('-')[-1]}-{case_b.split('-')[-1]}"
        stored = relational.get("verifications", link_id)
        associations.append({
            "link_id": link_id,
            "case_a": case_a,
            "case_a_title": (relational.get("cases", case_a) or {}).get("title", case_a),
            "case_b": case_b,
            "case_b_title": (relational.get("cases", case_b) or {}).get("title", case_b),
            "status": "CANDIDATE CROSS-CASE ASSOCIATION",
            "support_level": support_level,
            "strength": strength,
            "signals": signals,
            "why_connected": [s["signal"] + ": " + str(s["value"]) for s in supporting],
            "evidence_ids": sorted(e for e in evidence_ids if e),
            "entity_pairs": entity_pairs,
            "verification_status": (stored or {}).get("decision", "UNVERIFIED"),
            "verified_by": (stored or {}).get("verified_by"),
            "disclaimer": "Candidate association only. Requires investigator verification before "
                          "any investigative reliance.",
        })

    associations.sort(key=lambda a: a["strength"], reverse=True)
    return {
        "algorithm": "shared-identifier join + RapidFuzz name matching + location overlap + temporal proximity",
        "case_scope": scope,
        "associations": associations,
        "sufficient": bool(associations),
        "message": "" if associations else
                   "INSUFFICIENT EVIDENCE: no shared identifiers, similar identities or overlapping "
                   "locations were found across the authorized cases in scope.",
    }


def entity_case_overlap() -> list[dict[str, Any]]:
    """Entities appearing in more than one case (drives the cross-case table)."""
    out = []
    for node in graph_store.nodes():
        cases = node.get("cases") or []
        if len(cases) > 1:
            out.append({
                "entity_id": node["id"],
                "label": mask_node(node).get("label"),
                "entity_type": node.get("entity_type"),
                "cases": cases,
                "evidence_ids": node.get("evidence_ids", []),
                "verification_status": node.get("verification_status", "UNVERIFIED"),
            })
    out.sort(key=lambda x: (-len(x["cases"]), x["label"] or ""))
    return out
