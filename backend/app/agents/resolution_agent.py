"""ENTITY RESOLUTION AGENT.

NORMALIZATION -> TOKEN COMPARISON -> FUZZY SIMILARITY (RapidFuzz)
   -> MULTI-ATTRIBUTE MATCHING -> CANDIDATE MATCH -> HUMAN VERIFICATION

Hard rule: identities are NEVER merged automatically. The agent only produces
candidate matches with an explicit support level and the signals behind it.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import datetime
from typing import Any, Iterable, Optional

from rapidfuzz import fuzz

from ..config import RESOLUTION_HIGH, RESOLUTION_MEDIUM

AGENT_NAME = "ENTITY_RESOLUTION_AGENT"

_SUFFIX = {"jr", "sr", "mr", "mrs", "ms", "dr", "thiru"}


def _is_name_char(ch: str) -> bool:
    """Letters (L*) and combining marks (M* - this is what Devanagari/Tamil vowel
    signs and viramas are) plus '.' and space. Digits, punctuation and symbols are
    dropped. `\\w` is NOT usable here: matras are not alphanumeric, so a `\\w`-based
    filter silently deleted every vowel sign in an Indic name."""
    if ch in ". ":
        return True
    return unicodedata.category(ch)[0] in ("L", "M")


def normalize_name(name: str) -> str:
    """Unicode-aware name normalisation.

    The previous implementation, `re.sub(r"[^A-Za-z. ]", " ", name)`, stripped ALL
    non-Latin characters: "रवि कुमार" normalised to the empty string and could never
    be compared or resolved against anything.
    """
    n = unicodedata.normalize("NFKC", name or "")
    n = "".join(ch if _is_name_char(ch) else " " for ch in n)
    n = re.sub(r"\s+", " ", n).strip().lower()
    tokens = [t for t in n.split() if t.strip(".") not in _SUFFIX]
    return " ".join(tokens)


def tokenize(name: str) -> list[str]:
    return [t.strip(".") for t in normalize_name(name).split() if t.strip(".")]


def script_of(name: str) -> str:
    """Dominant script of a name, so a cross-script pair can be romanised before
    comparison instead of scoring 0 against a Latin record."""
    from . import indic

    return indic.dominant_script(name or "")


def token_comparison(a: str, b: str) -> dict[str, Any]:
    # Strip the trailing period from initials so "R. Kumar" and "R Kumar" and
    # "Ravi Kumar" are all recognised as sharing a compatible given name.
    ta = [t.strip(".") for t in _comparable(a).split() if t.strip(".")]
    tb = [t.strip(".") for t in _comparable(b).split() if t.strip(".")]
    shared = sorted(set(ta) & set(tb))
    initial_hits = 0
    for x in ta:
        for y in tb:
            if len(x) == 1 and y.startswith(x):
                initial_hits += 1
            elif len(y) == 1 and x.startswith(y):
                initial_hits += 1
    surname_match = bool(ta and tb and ta[-1] == tb[-1])
    return {
        "tokens_a": ta, "tokens_b": tb, "shared_tokens": shared,
        "initial_compatible": initial_hits > 0, "surname_match": surname_match,
    }


def _comparable(name: str) -> str:
    """Normalise for comparison; romanise Indic script so a Hindi/Tamil record can
    be compared with a Latin-script record from another case."""
    from . import indic

    norm = normalize_name(name)
    if norm and indic.is_indic(norm):
        return indic.fold_vowels(indic.romanise(norm, drop_final_schwa=True))
    return norm


def fuzzy_similarity(a: str, b: str) -> dict[str, float]:
    na, nb = _comparable(a), _comparable(b)
    return {
        "ratio": round(fuzz.ratio(na, nb), 2),
        "partial_ratio": round(fuzz.partial_ratio(na, nb), 2),
        "token_sort_ratio": round(fuzz.token_sort_ratio(na, nb), 2),
        "token_set_ratio": round(fuzz.token_set_ratio(na, nb), 2),
        "wratio": round(fuzz.WRatio(na, nb), 2),
    }


def _parse(ts: str) -> Optional[datetime]:
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(ts, fmt)
        except Exception:
            continue
    return None


def _attr_set(entity: dict[str, Any], key: str) -> set[str]:
    attrs = entity.get("attributes") or {}
    values = attrs.get(key) or []
    if isinstance(values, str):
        values = [values]
    return {str(v).upper() for v in values}


def _record_summary(entity: dict[str, Any], label: str) -> dict[str, Any]:
    """Comparable projection of an identity record for the review UI."""
    attrs = entity.get("attributes") or {}

    def _vals(key: str) -> list[str]:
        values = attrs.get(key) or []
        if isinstance(values, str):
            values = [values]
        return [str(v) for v in values]

    return {
        "entity_id": entity.get("entity_id") or entity.get("id"),
        "label": label,
        "entity_type": entity.get("entity_type", "PERSON"),
        "cases": entity.get("cases", []),
        "aliases": _vals("aliases"),
        "role_in_case": attrs.get("role_in_case", ""),
        "activity_dates": _vals("activity_dates"),
        "vehicles": _vals("vehicles"),
        "phones": _vals("phones"),
        "accounts": _vals("accounts"),
        "locations": _vals("locations"),
        "evidence_ids": entity.get("evidence_ids", []) or _vals("evidence_ids"),
        "first_seen": entity.get("first_seen"),
        "last_seen": entity.get("last_seen"),
    }


def compare_pair(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Multi-attribute comparison producing an explainable candidate match."""
    name_a, name_b = a.get("label", ""), b.get("label", "")
    tokens = token_comparison(name_a, name_b)
    fuzzy = fuzzy_similarity(name_a, name_b)
    name_score = max(fuzzy["token_set_ratio"], fuzzy["token_sort_ratio"], fuzzy["wratio"] * 0.95)
    if tokens["initial_compatible"] and tokens["surname_match"]:
        name_score = max(name_score, 86.0)
    elif tokens["initial_compatible"] and tokens["shared_tokens"]:
        # e.g. "Ravi Kumar" vs "Ravi K." - full given name plus compatible initial
        name_score = max(name_score, 78.0)

    vehicles = _attr_set(a, "vehicles") & _attr_set(b, "vehicles")
    phones = _attr_set(a, "phones") & _attr_set(b, "phones")
    locations = _attr_set(a, "locations") & _attr_set(b, "locations")
    accounts = _attr_set(a, "accounts") & _attr_set(b, "accounts")

    dates_a = [d for d in (_parse(x) for x in (a.get("attributes", {}).get("activity_dates") or [])) if d]
    dates_b = [d for d in (_parse(x) for x in (b.get("attributes", {}).get("activity_dates") or [])) if d]
    temporal_gap_days: Optional[int] = None
    temporal_conflict = False
    if dates_a and dates_b:
        temporal_gap_days = min(abs((x - y).days) for x in dates_a for y in dates_b)
        # A conflict is an identical timestamp in two different locations.
        for x in dates_a:
            for y in dates_b:
                if abs((x - y).total_seconds()) < 3600:
                    la = _attr_set(a, "locations")
                    lb = _attr_set(b, "locations")
                    if la and lb and not (la & lb):
                        temporal_conflict = True

    signals: list[dict[str, Any]] = [{
        "signal": "Name similarity",
        "value": f"{round(name_score, 1)}%",
        "supports": name_score >= 70,
        "detail": f"RapidFuzz token_set={fuzzy['token_set_ratio']}, token_sort={fuzzy['token_sort_ratio']}"
                  + (", initials compatible" if tokens["initial_compatible"] else "")
                  + (", surname match" if tokens["surname_match"] else ""),
    }, {
        "signal": "Vehicle consistency",
        "value": ", ".join(sorted(vehicles)) or "no shared vehicle",
        "supports": bool(vehicles),
        "detail": "Shared vehicle registration observed across records" if vehicles
                  else "No shared vehicle in available evidence",
    }, {
        "signal": "Location consistency",
        "value": ", ".join(sorted(locations)) or "no shared location",
        "supports": bool(locations),
        "detail": "Overlapping observed locations" if locations else "No overlapping locations",
    }, {
        "signal": "Phone / account consistency",
        "value": ", ".join(sorted(phones | accounts)) or "none shared",
        "supports": bool(phones or accounts),
        "detail": "Shared communication or financial identifier" if (phones or accounts)
                  else "No shared identifier in available evidence",
    }, {
        "signal": "Temporal consistency",
        "value": (f"{temporal_gap_days} day(s) between nearest observations"
                  if temporal_gap_days is not None else "no comparable timestamps"),
        "supports": temporal_gap_days is not None and temporal_gap_days <= 30 and not temporal_conflict,
        "detail": ("Same-hour observations at different locations - possible contradiction"
                   if temporal_conflict else "Observations fall inside a comparable window"
                   if temporal_gap_days is not None else "Insufficient temporal data"),
    }]

    score = (
        0.50 * min(name_score, 100.0)
        + 22.0 * (1 if vehicles else 0)
        + 10.0 * (1 if locations else 0)
        + 12.0 * (1 if (phones or accounts) else 0)
        + 8.0 * (1 if (temporal_gap_days is not None and temporal_gap_days <= 30) else 0)
    )
    if temporal_conflict:
        score -= 15.0
    score = round(max(0.0, min(score, 99.0)), 1)

    supporting = sum(1 for s in signals if s["supports"])
    if score >= 85 and supporting >= 3:
        support = "HIGH"
    elif score >= 65 and supporting >= 2:
        support = "MEDIUM"
    elif score >= 50:
        support = "LOW"
    else:
        support = "INSUFFICIENT"

    contradictions = []
    if temporal_conflict:
        contradictions.append(
            "Records place the two identities at different locations within the same hour.")
    if not vehicles and not phones and not accounts and name_score < RESOLUTION_HIGH:
        contradictions.append("No corroborating identifier beyond name similarity.")

    return {
        "left": _record_summary(a, name_a),
        "right": _record_summary(b, name_b),
        "score": score,
        "support_level": support,
        "name_similarity": round(name_score, 1),
        "fuzzy": fuzzy,
        "tokens": tokens,
        "signals": signals,
        "shared": {
            "vehicles": sorted(vehicles), "phones": sorted(phones),
            "locations": sorted(locations), "accounts": sorted(accounts),
        },
        "contradictions": contradictions,
        "temporal_gap_days": temporal_gap_days,
        "decision": "CANDIDATE_MATCH - REQUIRES HUMAN VERIFICATION" if support != "INSUFFICIENT"
                    else "INSUFFICIENT EVIDENCE FOR CANDIDATE MATCH",
        "auto_merged": False,
    }


def resolve(entities: Iterable[dict[str, Any]], min_support: str = "LOW",
            case_ids: Optional[list[str]] = None) -> dict[str, Any]:
    people = [e for e in entities if e.get("entity_type") in {"PERSON", "ALIAS"}]
    order = {"INSUFFICIENT": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
    threshold = order.get(min_support, 1)

    candidates: list[dict[str, Any]] = []
    for i in range(len(people)):
        for j in range(i + 1, len(people)):
            a, b = people[i], people[j]
            if (a.get("entity_id") or a.get("id")) == (b.get("entity_id") or b.get("id")):
                continue
            result = compare_pair(a, b)
            if order[result["support_level"]] >= threshold:
                candidates.append(result)

    candidates.sort(key=lambda c: c["score"], reverse=True)
    return {
        "agent": AGENT_NAME,
        "algorithm": "normalization -> token comparison -> RapidFuzz fuzzy similarity -> multi-attribute matching",
        "compared_records": len(people),
        "candidate_matches": candidates,
        "auto_merge_policy": "DISABLED - identity consolidation requires human verification",
        "case_scope": case_ids or "ALL_AUTHORIZED",
        "sufficient": bool(candidates),
        "note": "" if candidates else
                "INSUFFICIENT EVIDENCE: no identity pair reached the minimum multi-attribute support level.",
    }
