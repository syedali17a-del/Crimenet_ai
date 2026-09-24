"""Analytical services API - every endpoint runs a real algorithm."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..agents import manager, network_agent, reasoning_agent, resolution_agent, temporal_agent
from ..analytics import anomaly, cross_case, pattern_detectors, trust
from ..audit import audit_log
from ..database.neo4j_graph import graph_store
from ..database.postgres import relational
from ..database.redis_cache import cache
from ..schemas.api import (AnalysisRequest, EvidenceSupportRequest, ManagerRequest,
                           ResolutionRequest, ShortestPathRequest, TemporalRequest)
from ..security import pii
from ..security.deps import Principal, authorize_case, authorized_case_ids, require_permission

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


def _scope(principal: Principal, case_ids: list[str]) -> list[str]:
    allowed = authorized_case_ids(principal)
    if not case_ids:
        return allowed
    for cid in case_ids:
        authorize_case(principal, cid)
    return [c for c in case_ids if c in allowed]


def _cached(key: str, builder, ttl: int = 120) -> Any:
    hit = cache.get(key)
    if hit is not None:
        hit["_cache"] = "HIT (Redis task/result cache)"
        return hit
    value = builder()
    cache.set(key, value, ttl=ttl)
    value["_cache"] = "MISS (computed)"
    return value


@router.post("/evidence-support")
def evidence_support(payload: EvidenceSupportRequest,
                     principal: Principal = Depends(require_permission("analysis:run"))
                     ) -> dict[str, Any]:
    """How much corroboration weight does this set of evidence carry?

    The same function the corroboration engine uses (`app/analytics/trust.py`), exposed so
    a supervisor can ask the question directly: "this candidate is supported by these
    documents - what do they actually support?"
    """
    return trust.support_assessment(list(dict.fromkeys(payload.evidence_ids)))


@router.post("/network")
def analyze_network(payload: AnalysisRequest,
                    principal: Principal = Depends(require_permission("analysis:run"))) -> dict[str, Any]:
    scope = _scope(principal, payload.case_ids)
    result = _cached(f"analysis:network:{','.join(sorted(scope))}",
                     lambda: network_agent.analyze(scope))
    audit_log.record(principal.user_id, principal.role, "ANALYSIS_NETWORK",
                     case_id=scope[0] if scope else None,
                     detail=f"Scope {scope}; {result.get('nodes', 0)} nodes / {result.get('edges', 0)} edges.")
    return result


@router.post("/shortest-path")
def analyze_shortest_path(payload: ShortestPathRequest,
                          principal: Principal = Depends(require_permission("analysis:run"))
                          ) -> dict[str, Any]:
    scope = _scope(principal, payload.case_ids)
    result = network_agent.shortest_path(payload.source, payload.target, scope or None)
    audit_log.record(principal.user_id, principal.role, "ANALYSIS_SHORTEST_PATH",
                     detail=f"{payload.source} -> {payload.target}: "
                            f"{'path found' if result.get('found') else result.get('status')}.")
    return result


@router.post("/temporal")
def analyze_temporal(payload: TemporalRequest,
                     principal: Principal = Depends(require_permission("analysis:run"))) -> dict[str, Any]:
    scope = _scope(principal, payload.case_ids)
    result = temporal_agent.analyze(scope, payload.entity_id, payload.start, payload.end)
    audit_log.record(principal.user_id, principal.role, "ANALYSIS_TEMPORAL",
                     case_id=scope[0] if scope else None,
                     detail=f"{result.get('event_count', 0)} events analysed.")
    return result


@router.post("/convergence")
def analyze_convergence(payload: AnalysisRequest,
                        principal: Principal = Depends(require_permission("analysis:run"))
                        ) -> dict[str, Any]:
    scope = _scope(principal, payload.case_ids)
    result = temporal_agent.convergence(scope)
    audit_log.record(principal.user_id, principal.role, "ANALYSIS_CONVERGENCE",
                     detail=f"{len(result['convergence_events'])} potential convergence event(s).")
    return result


@router.post("/anomaly")
def analyze_anomaly(payload: AnalysisRequest,
                    principal: Principal = Depends(require_permission("analysis:run"))) -> dict[str, Any]:
    scope = _scope(principal, payload.case_ids)
    result = anomaly.analyze(scope)
    # Second detector: rule-based, different question, same response - each finding is
    # labelled with the detector that produced it so the two can never be confused.
    patterns = pattern_detectors.run_all(scope or None)
    rule_findings = [f for r in patterns["results"] for f in r["findings"]]
    result["pattern_detectors"] = patterns
    result["pattern_findings"] = rule_findings
    result["detectors"] = [
        {"detector": result.get("detector", anomaly.DETECTOR_NAME),
         "detector_kind": "classical_ml",
         "question": "Does an account behave abnormally against its own transaction baseline?",
         "method": result.get("model", "IsolationForest (scikit-learn)"),
         "findings": len(result.get("anomalies", []))},
        *[{"detector": r["detector"], "detector_kind": r["detector_kind"],
           "question": r["detector_description"], "method": r["message"] or "rule matched",
           "findings": r["finding_count"]} for r in patterns["results"]],
    ]
    result["detector_count"] = len(result["detectors"])
    audit_log.record(principal.user_id, principal.role, "ANALYSIS_ANOMALY",
                     detail=f"{len(result.get('anomalies', []))} statistical anomaly/anomalies; "
                            f"{len(rule_findings)} rule-based pattern finding(s) "
                            f"({', '.join(patterns['detectors_run'])}).")
    return result


@router.post("/entity-resolution")
def analyze_resolution(payload: ResolutionRequest,
                       principal: Principal = Depends(require_permission("analysis:run"))
                       ) -> dict[str, Any]:
    scope = _scope(principal, payload.case_ids)
    nodes = [{**n, "entity_id": n["id"]} for n in graph_store.nodes()
             if set(n.get("cases", [])) & set(scope)]
    result = resolution_agent.resolve(nodes, payload.min_support, scope)
    for c in result["candidate_matches"]:
        key = f"IDENTITY::{c['left']['entity_id']}::{c['right']['entity_id']}"
        stored = relational.get("verifications", key)
        c["verification_status"] = (stored or {}).get("decision", "UNVERIFIED")
        c["match_id"] = key
    audit_log.record(principal.user_id, principal.role, "ANALYSIS_ENTITY_RESOLUTION",
                     detail=f"{len(result['candidate_matches'])} candidate identity match(es); "
                            "no automatic merge performed.")
    # A5/A6 boundary: identifier-shaped tokens in generated prose and structured
    # records are masked here too, so a masked node label is never contradicted by
    # a sentence next to it. Document text fields stay exempt (see security/pii.py).
    return pii.mask_payload(result)


@router.post("/cross-case")
def analyze_cross_case(payload: AnalysisRequest,
                       principal: Principal = Depends(require_permission("analysis:run"))
                       ) -> dict[str, Any]:
    scope = _scope(principal, payload.case_ids)
    result = cross_case.correlate(scope)
    result["entity_overlap"] = [e for e in cross_case.entity_case_overlap()
                                if set(e["cases"]) & set(scope)]
    audit_log.record(principal.user_id, principal.role, "ANALYSIS_CROSS_CASE",
                     detail=f"{len(result['associations'])} candidate cross-case association(s).")
    # A5/A6 boundary: identifier-shaped tokens in generated prose and structured
    # records are masked here too, so a masked node label is never contradicted by
    # a sentence next to it. Document text fields stay exempt (see security/pii.py).
    return pii.mask_payload(result)


@router.post("/corroboration")
def analyze_corroboration(payload: AnalysisRequest,
                          principal: Principal = Depends(require_permission("analysis:run"))
                          ) -> dict[str, Any]:
    scope = _scope(principal, payload.case_ids)
    result = reasoning_agent.corroborate(scope)
    audit_log.record(principal.user_id, principal.role, "ANALYSIS_CORROBORATION",
                     detail=f"{result['summary']}")
    # A5/A6 boundary: identifier-shaped tokens in generated prose and structured
    # records are masked here too, so a masked node label is never contradicted by
    # a sentence next to it. Document text fields stay exempt (see security/pii.py).
    return pii.mask_payload(result)


@router.post("/hypotheses")
def analyze_hypotheses(payload: AnalysisRequest,
                       principal: Principal = Depends(require_permission("analysis:run"))
                       ) -> dict[str, Any]:
    scope = _scope(principal, payload.case_ids)
    return reasoning_agent.hypotheses(scope)


@router.post("/information-gaps")
def analyze_gaps(payload: AnalysisRequest,
                 principal: Principal = Depends(require_permission("analysis:run"))) -> dict[str, Any]:
    scope = _scope(principal, payload.case_ids)
    return reasoning_agent.information_gaps(scope)


@router.post("/next-best-action")
def analyze_nba(payload: AnalysisRequest,
                principal: Principal = Depends(require_permission("analysis:run"))) -> dict[str, Any]:
    scope = _scope(principal, payload.case_ids)
    result = reasoning_agent.next_best_action(scope)
    audit_log.record(principal.user_id, principal.role, "ANALYSIS_NEXT_BEST_ACTION",
                     detail=result.get("explanation") or result.get("message", ""))
    return result


# --- Manager agent ---------------------------------------------------------
@router.get("/manager/objectives")
def manager_objectives(principal: Principal = Depends(require_permission("analysis:run"))
                       ) -> dict[str, Any]:
    return {
        "objectives": [
            {"objective": key, "title": spec["title"],
             "tasks": [{"task_id": t[0], "name": t[1], "service": t[2],
                        "agent": manager.SERVICES[t[2]]["agent"],
                        "label": manager.SERVICES[t[2]]["label"], "depends_on": t[3]}
                       for t in spec["tasks"]]}
            for key, spec in manager.OBJECTIVES.items()
        ],
        "agents": manager.agent_registry(),
    }


@router.post("/manager/plan")
def manager_plan(payload: ManagerRequest,
                 principal: Principal = Depends(require_permission("analysis:run"))) -> dict[str, Any]:
    scope = _scope(principal, payload.case_ids)
    return manager.plan(payload.objective, scope)


@router.post("/manager/execute")
def manager_execute(payload: ManagerRequest,
                    principal: Principal = Depends(require_permission("analysis:run"))
                    ) -> dict[str, Any]:
    scope = _scope(principal, payload.case_ids)
    if not scope:
        raise HTTPException(status_code=403,
                            detail="No authorized case is in scope for this analysis.")
    try:
        return manager.execute(payload.objective, scope, principal)
    except manager.AuthorizationError as exc:
        audit_log.record(principal.user_id, principal.role, "MANAGER_AUTHORIZATION_DENIED",
                         status="DENIED", detail=str(exc))
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/manager/plan/{plan_id}")
def manager_plan_result(plan_id: str,
                        principal: Principal = Depends(require_permission("analysis:run"))
                        ) -> dict[str, Any]:
    payload = manager.plan_from_cache(plan_id)
    if not payload:
        raise HTTPException(status_code=404, detail="Plan result is no longer cached.")
    return payload
