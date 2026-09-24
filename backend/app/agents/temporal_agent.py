"""TEMPORAL ANALYSIS AGENT (pandas).

Time windows, repeated activity, activity spikes, temporal overlap, network
evolution and temporal-spatial convergence.

Safety rule: spatio-temporal overlap is reported as a POTENTIAL CONVERGENCE EVENT
requiring investigator review - never as a confirmed meeting.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional

import pandas as pd

from ..config import CONVERGENCE_WINDOW_MINUTES
from ..database.postgres import relational

AGENT_NAME = "NETWORK_TEMPORAL_AGENT"


def _parse(ts: str) -> Optional[datetime]:
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(ts, fmt)
        except Exception:
            continue
    return None


def _events(case_ids: Optional[list[str]] = None, entity_id: Optional[str] = None,
            start: Optional[str] = None, end: Optional[str] = None) -> list[dict[str, Any]]:
    rows = relational.all("events")
    if case_ids:
        rows = [r for r in rows if r.get("case_id") in case_ids]
    if entity_id:
        rows = [r for r in rows if entity_id in (r.get("entity_ids") or [])]
    s = _parse(start) if start else None
    e = _parse(end) if end else None
    out = []
    for r in rows:
        ts = _parse(r.get("timestamp", ""))
        if ts is None:
            continue
        if s and ts < s:
            continue
        if e and ts > e:
            continue
        out.append(r)
    out.sort(key=lambda r: r["timestamp"])
    return out


def analyze(case_ids: Optional[list[str]] = None, entity_id: Optional[str] = None,
            start: Optional[str] = None, end: Optional[str] = None) -> dict[str, Any]:
    events = _events(case_ids, entity_id, start, end)
    if not events:
        return {
            "agent": AGENT_NAME, "sufficient": False, "events": [], "daily_activity": [],
            "message": "INSUFFICIENT EVIDENCE: no timestamped events available for this scope.",
            "repeated_activity": [], "spikes": [], "overlaps": [], "convergence": [],
            "network_evolution": [],
        }

    df = pd.DataFrame(events)
    df["ts"] = pd.to_datetime(df["timestamp"], format="mixed", utc=False, errors="coerce")
    df = df.dropna(subset=["ts"]).sort_values("ts")
    df["date"] = df["ts"].dt.date.astype(str)

    daily = df.groupby("date").size().reset_index(name="events")
    mean, std = daily["events"].mean(), daily["events"].std(ddof=0)
    threshold = mean + max(std, 0.8)
    spikes = [
        {"date": row["date"], "events": int(row["events"]), "baseline": round(float(mean), 2),
         "interpretation": "Activity above the observed baseline for this scope - "
                           "an analytical signal, not a finding."}
        for _, row in daily.iterrows() if row["events"] > threshold
    ]

    # repeated activity: entity + location pairs seen more than once
    repeated: list[dict[str, Any]] = []
    pair_counts: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for ev in events:
        loc = ev.get("location_id") or "UNKNOWN"
        for ent in ev.get("entity_ids") or []:
            pair_counts.setdefault((ent, loc), []).append(ev)
    for (ent, loc), evs in pair_counts.items():
        if len(evs) >= 2 and loc != "UNKNOWN":
            repeated.append({
                "entity_id": ent, "location_id": loc, "occurrences": len(evs),
                "timestamps": [e["timestamp"] for e in evs],
                "evidence_ids": sorted({e.get("evidence_id") for e in evs if e.get("evidence_id")}),
                "interpretation": "Repeated presence at the same location across the evidence set.",
            })
    repeated.sort(key=lambda r: r["occurrences"], reverse=True)

    # temporal overlap between entities (same day)
    overlaps: list[dict[str, Any]] = []
    by_day: dict[str, set[str]] = {}
    for ev in events:
        day = ev["timestamp"][:10]
        by_day.setdefault(day, set()).update(ev.get("entity_ids") or [])
    for day, ents in sorted(by_day.items()):
        persons = sorted(ents)
        if len(persons) >= 2:
            overlaps.append({"date": day, "entities": persons, "count": len(persons)})

    # network evolution: cumulative distinct entities/relationship-bearing events over time
    evolution = []
    seen: set[str] = set()
    for _, row in df.iterrows():
        seen.update(row.get("entity_ids") or [])
        evolution.append({"timestamp": row["timestamp"], "distinct_entities": len(seen)})

    return {
        "agent": AGENT_NAME,
        "sufficient": True,
        "case_scope": case_ids or "ALL_AUTHORIZED",
        "window": {"start": events[0]["timestamp"], "end": events[-1]["timestamp"]},
        "event_count": len(events),
        "events": events,
        "daily_activity": daily.to_dict("records"),
        "baseline_events_per_day": round(float(mean), 2),
        "spikes": spikes,
        "repeated_activity": repeated[:12],
        "overlaps": overlaps,
        "network_evolution": evolution,
        "convergence": convergence(case_ids)["convergence_events"],
        "safety_note": "Temporal co-occurrence is an analytical signal. It does not establish "
                       "contact, coordination or intent.",
    }


def convergence(case_ids: Optional[list[str]] = None,
                window_minutes: int = CONVERGENCE_WINDOW_MINUTES) -> dict[str, Any]:
    """TEMPORAL-SPATIAL CONVERGENCE: entities at the same location inside a time window."""
    events = _events(case_ids)
    buckets: dict[str, list[dict[str, Any]]] = {}
    for ev in events:
        loc = ev.get("location_id")
        if not loc:
            continue
        buckets.setdefault(loc, []).append(ev)

    results: list[dict[str, Any]] = []
    for loc, evs in buckets.items():
        evs = sorted(evs, key=lambda e: e["timestamp"])
        for i, base in enumerate(evs):
            base_ts = _parse(base["timestamp"])
            if base_ts is None:
                continue
            group = [base]
            for other in evs[i + 1:]:
                ots = _parse(other["timestamp"])
                if ots and abs((ots - base_ts).total_seconds()) <= window_minutes * 60:
                    group.append(other)
            entities = sorted({e for g in group for e in (g.get("entity_ids") or [])})
            if len(group) >= 2 and len(entities) >= 2:
                signals = [
                    {"signal": "Temporal overlap",
                     "present": True,
                     "detail": f"{len(group)} events inside a {window_minutes}-minute window"},
                    {"signal": "Location overlap", "present": True, "detail": f"All events at {loc}"},
                    {"signal": "Repeated occurrence",
                     "present": len(group) >= 3,
                     "detail": f"{len(group)} separate records at this location/window"},
                ]
                key = (loc, group[0]["timestamp"])
                if not any(r["key"] == list(key) for r in results):
                    results.append({
                        "key": list(key),
                        "location_id": loc,
                        "window_start": group[0]["timestamp"],
                        "window_end": group[-1]["timestamp"],
                        "entities": entities,
                        "events": [{"event_id": g["event_id"], "timestamp": g["timestamp"],
                                    "title": g.get("title"), "evidence_id": g.get("evidence_id"),
                                    "entity_ids": g.get("entity_ids", [])} for g in group],
                        "evidence_ids": sorted({g.get("evidence_id") for g in group if g.get("evidence_id")}),
                        "signals": signals,
                        "status": "POTENTIAL CONVERGENCE EVENT",
                        "requires_review": True,
                        "disclaimer": "Co-location in time does not establish that these individuals met. "
                                      "Investigator review required.",
                    })
    results.sort(key=lambda r: (len(r["entities"]), r["window_start"]), reverse=True)
    return {
        "agent": AGENT_NAME,
        "window_minutes": window_minutes,
        "convergence_events": results,
        "sufficient": bool(results),
        "message": "" if results else
                   "INSUFFICIENT EVIDENCE: no spatio-temporal overlap detected in this scope.",
    }
