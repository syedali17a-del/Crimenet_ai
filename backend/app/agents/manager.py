"""MANAGER AGENT - controlled task orchestration.

The Manager understands an investigation objective, builds a dependency-ordered
task plan, delegates each task to an AUTHORIZED analytical service, collects the
structured results and hands them back with an audit trail.

Constraints enforced here:
  * The Manager has no direct database access - it may only call the registered
    analytical services below.
  * Every task is checked against the invoking principal's RBAC permissions and
    case-level authorization before it runs.
  * The Manager can never verify findings, change permissions, delete evidence or
    modify audit history.
"""
from __future__ import annotations

import itertools
import time
from typing import Any, Callable, Optional

from ..agents import entity_agent, evidence_agent, network_agent, reasoning_agent, resolution_agent, temporal_agent
from ..analytics import anomaly, cross_case
from ..audit import audit_log
from ..database.neo4j_graph import graph_store
from ..database.postgres import relational
from ..database.redis_cache import cache
from ..models.domain import TaskRecord, now_iso
from ..security.rbac import AGENT_FORBIDDEN, AGENT_PERMISSIONS, can_access_case, has_permission

AGENT_NAME = "MANAGER_AGENT"
_plan_counter = itertools.count(1)


class AuthorizationError(Exception):
    pass


# --- registry of authorized analytical services ---------------------------
def _svc_document(ctx: dict[str, Any]) -> dict[str, Any]:
    processed = [e for e in relational.all("evidence")
                 if e.get("case_id") in ctx["case_ids"]
                 and e.get("processing_status") in {"EXTRACTED", "ENTITIES_FOUND", "RELATIONSHIPS_CANDIDATE"}]
    pending = [e for e in relational.all("evidence")
               if e.get("case_id") in ctx["case_ids"] and e not in processed]
    return {
        "agent": "DOCUMENT_INTELLIGENCE_AGENT",
        "documents_in_scope": len(processed) + len(pending),
        "already_processed": [e["evidence_id"] for e in processed],
        "awaiting_processing": [e["evidence_id"] for e in pending],
        "summary": f"{len(processed)} evidence document(s) already carry extracted text; "
                   f"{len(pending)} awaiting the document pipeline.",
    }


def _svc_entities(ctx: dict[str, Any]) -> dict[str, Any]:
    nodes = [n for n in graph_store.nodes() if set(n.get("cases", [])) & set(ctx["case_ids"])]
    counts: dict[str, int] = {}
    for n in nodes:
        counts[n.get("entity_type", "UNKNOWN")] = counts.get(n.get("entity_type", "UNKNOWN"), 0) + 1
    return {
        "agent": "ENTITY_RESOLUTION_AGENT",
        "backend": entity_agent.backend_info(),
        "entity_count": len(nodes),
        "by_type": counts,
        "entities": [{"entity_id": n["id"], "label": n.get("label"),
                      "entity_type": n.get("entity_type"), "cases": n.get("cases", [])}
                     for n in nodes[:60]],
        "summary": f"{len(nodes)} entities available in the authorized case scope.",
    }


def _svc_resolution(ctx: dict[str, Any]) -> dict[str, Any]:
    nodes = [{**n, "entity_id": n["id"]} for n in graph_store.nodes()
             if set(n.get("cases", [])) & set(ctx["case_ids"])]
    res = resolution_agent.resolve(nodes, min_support="LOW", case_ids=ctx["case_ids"])
    res["summary"] = (f"{len(res['candidate_matches'])} candidate identity match(es); "
                      "no identity merged automatically.")
    return res


def _svc_cross_case(ctx: dict[str, Any]) -> dict[str, Any]:
    res = cross_case.correlate(ctx["case_ids"])
    res["summary"] = (f"{len(res['associations'])} candidate cross-case association(s) detected."
                      if res["associations"] else res["message"])
    return res


def _svc_network(ctx: dict[str, Any]) -> dict[str, Any]:
    res = network_agent.analyze(ctx["case_ids"])
    res["summary"] = (f"{res['nodes']} nodes / {res['edges']} relationships analysed; "
                      f"{len(res.get('communities', []))} structural cluster(s)."
                      if res.get("sufficient") else res.get("message", ""))
    return res


def _svc_temporal(ctx: dict[str, Any]) -> dict[str, Any]:
    res = temporal_agent.analyze(ctx["case_ids"])
    res["summary"] = (f"{res['event_count']} timestamped events; {len(res['repeated_activity'])} "
                      f"repeated pattern(s); {len(res['convergence'])} potential convergence event(s)."
                      if res.get("sufficient") else res.get("message", ""))
    return res


def _svc_anomaly(ctx: dict[str, Any]) -> dict[str, Any]:
    res = anomaly.analyze(ctx["case_ids"])
    res["summary"] = (f"{len(res['anomalies'])} analytical anomaly/anomalies flagged."
                      if res.get("sufficient") else res.get("message", ""))
    return res


def _svc_corroboration(ctx: dict[str, Any]) -> dict[str, Any]:
    res = reasoning_agent.corroborate(ctx["case_ids"])
    s = res["summary"]
    res["summary"] = (f"{s['corroborated']} corroborated, {s['partial']} partial, "
                      f"{s['contradictory']} contradictory, {s['insufficient']} insufficient.")
    return res


def _svc_hypotheses(ctx: dict[str, Any]) -> dict[str, Any]:
    res = reasoning_agent.hypotheses(ctx["case_ids"])
    res["summary"] = f"{len(res['hypothesis_sets'])} competing-hypothesis set(s) generated."
    return res


def _svc_gaps(ctx: dict[str, Any]) -> dict[str, Any]:
    res = reasoning_agent.information_gaps(ctx["case_ids"])
    res["summary"] = f"{len(res['gaps'])} open information gap(s) identified."
    return res


def _svc_next_best(ctx: dict[str, Any]) -> dict[str, Any]:
    res = reasoning_agent.next_best_action(ctx["case_ids"])
    res["summary"] = (res.get("explanation") or res.get("message", ""))
    return res


def _svc_integrity(ctx: dict[str, Any]) -> dict[str, Any]:
    results = []
    for ev in relational.all("evidence"):
        if ev.get("case_id") in ctx["case_ids"]:
            results.append(evidence_agent.integrity_check(ev["evidence_id"], actor=AGENT_NAME))
    mismatches = [r for r in results if r.get("status") != "VERIFIED"]
    return {
        "agent": "EVIDENCE_PROVENANCE_AGENT",
        "checked": len(results),
        "verified": len(results) - len(mismatches),
        "mismatches": [{"evidence_id": r["evidence_id"], "status": r["status"]} for r in mismatches],
        "results": results,
        "summary": f"{len(results)} evidence object(s) hashed; {len(mismatches)} integrity issue(s).",
    }


SERVICES: dict[str, dict[str, Any]] = {
    "document_intelligence": {"fn": _svc_document, "agent": "DOCUMENT_INTELLIGENCE_AGENT",
                              "permission": "evidence:process",
                              "label": "Document Agent — Processing evidence..."},
    "entity_extraction": {"fn": _svc_entities, "agent": "ENTITY_RESOLUTION_AGENT",
                          "permission": "analysis:run",
                          "label": "Entity Agent — Extracting entities..."},
    "entity_resolution": {"fn": _svc_resolution, "agent": "ENTITY_RESOLUTION_AGENT",
                          "permission": "analysis:run",
                          "label": "Resolution Agent — Matching candidate identities..."},
    "cross_case_correlation": {"fn": _svc_cross_case, "agent": "INVESTIGATION_REASONING_AGENT",
                               "permission": "analysis:run",
                               "label": "Cross-Case Engine — Correlating cases..."},
    "network_analysis": {"fn": _svc_network, "agent": "NETWORK_TEMPORAL_AGENT",
                         "permission": "analysis:run",
                         "label": "Network Agent — Analyzing graph..."},
    "temporal_analysis": {"fn": _svc_temporal, "agent": "NETWORK_TEMPORAL_AGENT",
                          "permission": "analysis:run",
                          "label": "Temporal Agent — Analyzing timeline..."},
    "anomaly_analysis": {"fn": _svc_anomaly, "agent": "NETWORK_TEMPORAL_AGENT",
                         "permission": "analysis:run",
                         "label": "Anomaly Engine — Comparing behavioural baselines..."},
    "evidence_integrity": {"fn": _svc_integrity, "agent": "EVIDENCE_PROVENANCE_AGENT",
                           "permission": "evidence:integrity",
                           "label": "Evidence Agent — Verifying SHA-256 integrity..."},
    "corroboration": {"fn": _svc_corroboration, "agent": "INVESTIGATION_REASONING_AGENT",
                      "permission": "analysis:run",
                      "label": "Corroboration Engine — Comparing findings..."},
    "hypotheses": {"fn": _svc_hypotheses, "agent": "INVESTIGATION_REASONING_AGENT",
                   "permission": "analysis:run",
                   "label": "Reasoning Agent — Generating competing hypotheses..."},
    "information_gaps": {"fn": _svc_gaps, "agent": "INVESTIGATION_REASONING_AGENT",
                         "permission": "analysis:run",
                         "label": "Information Gap Engine — Identifying missing information..."},
    "next_best_action": {"fn": _svc_next_best, "agent": "INVESTIGATION_REASONING_AGENT",
                         "permission": "analysis:run",
                         "label": "Next-Best Action — Ranking analytical options..."},
}

OBJECTIVES: dict[str, dict[str, Any]] = {
    "CROSS_CASE_LINK": {
        "title": "Find potential links between the selected cases",
        "tasks": [
            ("T1", "Extract entities", "entity_extraction", []),
            ("T2", "Resolve candidate identities", "entity_resolution", ["T1"]),
            ("T3", "Cross-case correlation", "cross_case_correlation", ["T2"]),
            ("T4", "Network analysis", "network_analysis", ["T3"]),
            ("T5", "Temporal analysis", "temporal_analysis", ["T3"]),
            ("T6", "Corroboration", "corroboration", ["T4", "T5"]),
            ("T7", "Information gap analysis", "information_gaps", ["T6"]),
            ("T8", "Next-best analytical action", "next_best_action", ["T7"]),
        ],
    },
    "FULL_CASE_ANALYSIS": {
        "title": "Full evidence-to-intelligence analysis for the selected case scope",
        "tasks": [
            ("T1", "Document intelligence review", "document_intelligence", []),
            ("T2", "Extract entities", "entity_extraction", ["T1"]),
            ("T3", "Resolve candidate identities", "entity_resolution", ["T2"]),
            ("T4", "Evidence integrity verification", "evidence_integrity", ["T1"]),
            ("T5", "Cross-case correlation", "cross_case_correlation", ["T3"]),
            ("T6", "Network analysis", "network_analysis", ["T5"]),
            ("T7", "Temporal analysis", "temporal_analysis", ["T5"]),
            ("T8", "Anomaly analysis", "anomaly_analysis", ["T5"]),
            ("T9", "Corroboration", "corroboration", ["T6", "T7", "T8", "T4"]),
            ("T10", "Competing hypotheses", "hypotheses", ["T9"]),
            ("T11", "Information gap analysis", "information_gaps", ["T9"]),
            ("T12", "Next-best analytical action", "next_best_action", ["T11"]),
        ],
    },
    "EVIDENCE_INTEGRITY_SWEEP": {
        "title": "Verify evidence integrity and chain of custody for the case scope",
        "tasks": [
            ("T1", "Evidence integrity verification", "evidence_integrity", []),
            ("T2", "Corroboration re-check", "corroboration", ["T1"]),
            ("T3", "Information gap analysis", "information_gaps", ["T2"]),
        ],
    },
}


def agent_registry() -> list[dict[str, Any]]:
    return [
        {"agent": name, "permissions": perms, "forbidden": AGENT_FORBIDDEN,
         "services": sorted(k for k, v in SERVICES.items() if v["agent"] == name)}
        for name, perms in AGENT_PERMISSIONS.items()
    ]


def plan(objective: str, case_ids: list[str]) -> dict[str, Any]:
    spec = OBJECTIVES.get(objective) or OBJECTIVES["FULL_CASE_ANALYSIS"]
    return {
        "objective": objective,
        "title": spec["title"],
        "case_ids": case_ids,
        "tasks": [
            {"task_id": tid, "name": name, "service": svc,
             "agent": SERVICES[svc]["agent"], "label": SERVICES[svc]["label"],
             "depends_on": deps, "status": "PENDING"}
            for tid, name, svc, deps in spec["tasks"]
        ],
    }


def execute(objective: str, case_ids: list[str], principal: Any,
            audit: bool = True) -> dict[str, Any]:
    """Authorization -> plan -> ordered delegation -> result collection."""
    # 1. authorization gate (never bypassed by the Manager)
    for case_id in case_ids:
        if not can_access_case(principal.case_access, case_id):
            raise AuthorizationError(f"Case-level authorization denied for {case_id}.")
    if not has_permission(principal.role, "analysis:run"):
        raise AuthorizationError(f"Role {principal.role} may not execute analytical services.")

    plan_id = f"PLAN-{next(_plan_counter):04d}"
    blueprint = plan(objective, case_ids)
    ctx = {"case_ids": case_ids, "principal": principal.user_id}
    started = now_iso()

    task_records: list[TaskRecord] = []
    results: dict[str, Any] = {}
    completed: set[str] = set()

    if audit:
        audit_log.record(principal.user_id, principal.role, "MANAGER_PLAN_CREATED",
                         case_id=case_ids[0] if case_ids else None, object_id=plan_id,
                         detail=f"Objective={objective}; cases={','.join(case_ids)}; "
                                f"{len(blueprint['tasks'])} tasks planned.")

    for task in blueprint["tasks"]:
        svc_key = task["service"]
        svc = SERVICES[svc_key]
        rec = TaskRecord(task_id=f"{plan_id}-{task['task_id']}", plan_id=plan_id,
                         name=task["name"], agent=svc["agent"], depends_on=task["depends_on"])

        unmet = [d for d in task["depends_on"] if d not in completed]
        if unmet:
            rec.status = "SKIPPED"
            rec.summary = f"Dependency not satisfied: {', '.join(unmet)}"
            task_records.append(rec)
            relational.insert("tasks", rec.task_id, rec.model_dump())
            continue

        if not has_permission(principal.role, svc["permission"]):
            rec.status = "SKIPPED"
            rec.summary = (f"Not authorized: role {principal.role} lacks '{svc['permission']}'. "
                           "Task withheld by the security gateway.")
            task_records.append(rec)
            relational.insert("tasks", rec.task_id, rec.model_dump())
            continue

        rec.status = "RUNNING"
        rec.started_at = now_iso()
        t0 = time.perf_counter()
        try:
            out = svc["fn"](ctx)
            rec.status = "COMPLETE"
            rec.summary = out.get("summary", "")
            rec.result = out
            results[svc_key] = out
            completed.add(task["task_id"])
        except Exception as exc:  # never leak a stack trace to the caller
            rec.status = "FAILED"
            rec.summary = f"Analytical service failed: {type(exc).__name__}"
            rec.result = {"error": "The analytical service could not complete this task."}
        rec.finished_at = now_iso()
        rec.result["duration_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        task_records.append(rec)
        relational.insert("tasks", rec.task_id, rec.model_dump())

        if audit:
            audit_log.record(principal.user_id, principal.role, f"AGENT_TASK_{rec.status}",
                             case_id=case_ids[0] if case_ids else None, object_id=rec.task_id,
                             status=rec.status,
                             detail=f"{rec.agent} :: {rec.name} — {rec.summary}")

    payload = {
        "plan_id": plan_id,
        "objective": objective,
        "title": blueprint["title"],
        "case_ids": case_ids,
        "requested_by": principal.user_id,
        "role": principal.role,
        "started_at": started,
        "finished_at": now_iso(),
        "tasks": [t.model_dump() for t in task_records],
        "results": results,
        "manager_constraints": {
            "direct_database_access": False,
            "authorized_services_only": True,
            "forbidden_capabilities": AGENT_FORBIDDEN,
        },
        "conclusion": _conclusion(results),
    }
    relational.insert("plans", plan_id, {
        "plan_id": plan_id, "objective": objective, "case_ids": case_ids,
        "requested_by": principal.user_id, "started_at": started, "finished_at": payload["finished_at"],
        "task_count": len(task_records),
    })
    cache.set(f"plan:{plan_id}", payload, ttl=1800)
    return payload


def _conclusion(results: dict[str, Any]) -> dict[str, Any]:
    corr = results.get("corroboration", {})
    gaps = results.get("information_gaps", {})
    nba = results.get("next_best_action", {})
    summary = corr.get("summary", "")
    leads = corr.get("leads", [])
    top = next((l for l in leads if l["status"] == "CORROBORATED ANALYTICAL LEAD"), None)
    if top is None:
        top = next((l for l in leads if l["status"] == "CONTRADICTORY EVIDENCE"), None)
    if top is None:
        top = leads[0] if leads else None
    return {
        "headline": (top["title"] if top else
                     "No analytical lead reached a supportable threshold in this scope."),
        "status": top["status"] if top else "INSUFFICIENT EVIDENCE",
        "why": (top.get("why", []) if top else []),
        "missing_evidence": (top.get("missing_evidence", []) if top else []),
        "corroboration_summary": summary,
        "open_gaps": len(gaps.get("gaps", [])),
        "recommended_next_analysis": (nba.get("recommended") or {}).get("title"),
        "human_decision_required": True,
        "principle": ("AI finds patterns. Evidence supports them. Specialized agents corroborate them. "
                      "Security protects them. Humans decide what they mean."),
    }


def plan_from_cache(plan_id: str) -> Optional[dict[str, Any]]:
    return cache.get(f"plan:{plan_id}")
