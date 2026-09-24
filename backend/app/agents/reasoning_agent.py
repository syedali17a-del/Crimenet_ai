"""INVESTIGATION REASONING AGENT.

Structured (non-generative) reasoning:
  * Evidence corroboration across independent analytical methods
  * Competing hypothesis generation and ranking
  * Information gap analysis
  * Next-best analytical action ranking by information value

No claim of certainty, no guilt determination, no predictive policing. Where the
evidence base is thin the agent returns INSUFFICIENT EVIDENCE and names the gap.
"""
from __future__ import annotations

from typing import Any, Optional

from ..agents import network_agent, temporal_agent
from ..analytics import anomaly, cross_case
from ..analytics import trust
from ..database.neo4j_graph import graph_store
from ..database.postgres import relational

AGENT_NAME = "INVESTIGATION_REASONING_AGENT"

# Catalogue of authorized analytical actions. Nothing operational, intrusive or
# enforcement-related may ever appear here.
ACTION_CATALOGUE: list[dict[str, Any]] = [
    {
        "action_id": "ACT-VEHICLE-XREF",
        "title": "Cross-reference authorized vehicle records",
        "endpoint": "/api/analysis/cross-case",
        "method": "POST",
        "gap_types": ["IDENTITY_CONFIRMATION", "VEHICLE_LINK", "INDEPENDENT_CORROBORATION"],
        "base_value": 0.86,
        "rationale": "Vehicle registration is a hard identifier; confirming it across authorized "
                     "case records resolves identity ambiguity faster than any other available step.",
    },
    {
        "action_id": "ACT-ENTITY-RESOLUTION",
        "title": "Run multi-attribute entity resolution on candidate identities",
        "endpoint": "/api/analysis/entity-resolution",
        "method": "POST",
        "gap_types": ["IDENTITY_CONFIRMATION"],
        "base_value": 0.80,
        "rationale": "Adds token, fuzzy and attribute evidence to an unresolved identity pair before "
                     "any investigative reliance.",
    },
    {
        "action_id": "ACT-TEMPORAL",
        "title": "Analyze available event timeline for the linked entities",
        "endpoint": "/api/analysis/temporal",
        "method": "POST",
        "gap_types": ["TEMPORAL_CONTEXT", "REPEATED_ACTIVITY"],
        "base_value": 0.68,
        "rationale": "Establishes whether observed co-occurrence is repeated or isolated.",
    },
    {
        "action_id": "ACT-NETWORK",
        "title": "Recompute network structure over the joined case scope",
        "endpoint": "/api/analysis/network",
        "method": "POST",
        "gap_types": ["STRUCTURAL_CONTEXT", "INDEPENDENT_CORROBORATION"],
        "base_value": 0.62,
        "rationale": "Reveals bridging entities and clusters that may explain an unexplained link.",
    },
    {
        "action_id": "ACT-ANOMALY",
        "title": "Review behavioural anomaly baseline for linked accounts",
        "endpoint": "/api/analysis/anomaly",
        "method": "POST",
        "gap_types": ["FINANCIAL_CONTEXT", "BEHAVIOURAL_BASELINE"],
        "base_value": 0.55,
        "rationale": "Tests whether financial activity deviates from the account's own baseline.",
    },
    {
        "action_id": "ACT-INTEGRITY",
        "title": "Run SHA-256 integrity verification on supporting evidence",
        "endpoint": "/api/evidence/{evidence_id}/integrity-check",
        "method": "POST",
        "gap_types": ["EVIDENCE_RELIABILITY"],
        "base_value": 0.58,
        "rationale": "A finding can only be relied upon if its underlying evidence is intact.",
    },
    {
        "action_id": "ACT-CORROBORATION",
        "title": "Re-run corroboration across network, temporal and documentary findings",
        "endpoint": "/api/analysis/corroboration",
        "method": "POST",
        "gap_types": ["INDEPENDENT_CORROBORATION", "CONTRADICTION"],
        "base_value": 0.64,
        "rationale": "Checks whether independent analytical methods agree before escalation.",
    },
    {
        "action_id": "ACT-REQUEST-VERIFICATION",
        "title": "Submit candidate finding for supervisory human verification",
        "endpoint": "/api/entities/{entity_id}/verify",
        "method": "POST",
        "gap_types": ["HUMAN_VALIDATION"],
        "base_value": 0.72,
        "rationale": "Analytical candidates require a human decision before they carry investigative weight.",
    },
]


def _case_titles(case_ids: list[str]) -> str:
    return ", ".join(f"{c}" for c in case_ids)


def _evidence_rows(ids: list[str]) -> list[dict[str, Any]]:
    out = []
    for eid in ids:
        ev = relational.get("evidence", eid)
        if ev:
            out.append({
                "evidence_id": eid, "type": ev.get("evidence_type"), "source": ev.get("source"),
                "case_id": ev.get("case_id"), "timestamp": ev.get("timestamp"),
                "integrity_status": ev.get("integrity_status"),
                "verification_status": ev.get("verification_status"),
                "source_trust": trust.trust_of(ev),
                "source_trust_weight": trust.weight(trust.trust_of(ev)),
            })
    return out


def _contradictions_for(subject_ids: list[str], case_ids: list[str]) -> list[dict[str, Any]]:
    rows = relational.all("contradictions")
    out = []
    for r in rows:
        if r.get("case_id") in case_ids or set(r.get("entity_ids", [])) & set(subject_ids):
            out.append(r)
    return out


# --------------------------------------------------------------------------
# CORROBORATION
# --------------------------------------------------------------------------
def corroborate(case_ids: Optional[list[str]] = None) -> dict[str, Any]:
    scope = case_ids or [c["case_id"] for c in relational.all("cases")]
    network = network_agent.analyze(scope)
    temporal = temporal_agent.analyze(scope)
    xcase = cross_case.correlate(scope)
    anomalies = anomaly.analyze(scope)

    leads: list[dict[str, Any]] = []

    # 1. cross-case associations corroborated by network + temporal evidence
    for assoc in xcase["associations"]:
        subject_ids = [p["left"] for p in assoc["entity_pairs"]] + \
                      [p["right"] for p in assoc["entity_pairs"]]
        methods: list[dict[str, Any]] = []
        methods.append({
            "method": "Cross-case correlation",
            "finding": f"{assoc['support_level']} support candidate association "
                       f"{assoc['case_a']} ↔ {assoc['case_b']}",
            "agrees": True,
        })
        rep = [r for r in temporal.get("repeated_activity", [])
               if r["entity_id"] in subject_ids]
        methods.append({
            "method": "Temporal analysis",
            "finding": (f"Repeated activity observed for {len(rep)} linked entity/location pair(s)"
                        if rep else "No repeated temporal pattern for the linked entities"),
            "agrees": bool(rep),
        })
        deg = {d["entity_id"]: d for d in network.get("degree_centrality", [])}
        structural = [deg[s] for s in subject_ids if s in deg]
        methods.append({
            "method": "Network analysis",
            "finding": (f"{len(structural)} linked entity/entities are among the most connected "
                        f"nodes in the joined scope" if structural else
                        "Linked entities are not structurally prominent"),
            "agrees": bool(structural),
        })

        supporting_evidence = _evidence_rows(assoc["evidence_ids"])
        # SOURCE-TRUST WEIGHTING: two documents only corroborate each other to the extent
        # that they can be trusted. A single external submission cannot carry a candidate
        # into the confident band no matter how many methods appear to agree with it.
        assessment = trust.support_assessment(assoc["evidence_ids"])
        independent_sources = assessment["independent_sources"]
        weighted_support = assessment["weighted_support"]
        contradictions = _contradictions_for(subject_ids, [assoc["case_a"], assoc["case_b"]])
        agreeing = sum(1 for m in methods if m["agrees"])
        raw_level = assoc["support_level"]
        # The association engine's own level is capped by what the evidence can support.
        support_level = trust.cap_level(raw_level, assessment)
        downgraded = support_level != raw_level

        if (agreeing >= 2 and independent_sources >= trust.HIGH_MIN_SOURCES
                and weighted_support >= trust.HIGH_MIN_WEIGHT and not contradictions):
            status = "CORROBORATED ANALYTICAL LEAD"
        elif contradictions:
            status = "CONTRADICTORY EVIDENCE"
        elif agreeing >= 2 or independent_sources >= 2:
            status = "PARTIALLY CORROBORATED - FURTHER EVIDENCE REQUIRED"
        else:
            status = "INSUFFICIENT EVIDENCE"

        missing = []
        if contradictions:
            missing.append("Resolution of contradictory evidence (" +
                           ", ".join(c.get("contradiction_id", "CON") for c in contradictions) + ")")
        if independent_sources < 2:
            missing.append("Independent corroborating source (currently a single source type)")
        if weighted_support < trust.HIGH_MIN_WEIGHT:
            missing.append(f"Higher-trust corroboration (weighted support {weighted_support:.2f} "
                           f"of {trust.HIGH_MIN_WEIGHT:.2f}; the current support comes from "
                           + ", ".join(f"{e['source_trust']}" for e in assessment["sources"])
                           + ")")
        if not any(e["verification_status"] == "HUMAN_VERIFIED" for e in supporting_evidence):
            missing.append("Human-verified supporting evidence")
        if not rep:
            missing.append("Repeated temporal pattern")
        if assoc["support_level"] != "HIGH":
            missing.append("Identity confirmation for the candidate person match")

        leads.append({
            "lead_id": f"LEAD-{assoc['link_id']}",
            "title": f"Potential cross-case association {assoc['case_a']} ↔ {assoc['case_b']}",
            "subject_ids": sorted(set(subject_ids)),
            "case_ids": [assoc["case_a"], assoc["case_b"]],
            "status": status,
            "support_level": support_level,
            "support_level_raw": raw_level,
            "support_level_capped_by_source_trust": downgraded,
            "support_level_cap_reason": (
                f"evidence weighted {weighted_support:.2f} (needs "
                f"{trust.HIGH_MIN_WEIGHT:.2f} from {trust.HIGH_MIN_SOURCES} independent "
                f"sources for the confident band)" if downgraded else ""),
            "weighted_support": weighted_support,
            "source_trust_breakdown": assessment,
            "methods": methods,
            "independent_sources": independent_sources,
            "supporting_evidence": supporting_evidence,
            "contradicting_evidence": contradictions,
            "missing_evidence": missing,
            "why": assoc["why_connected"],
            "verification_status": assoc["verification_status"],
            "disclaimer": "Analytical lead only. It does not establish wrongdoing by any person.",
        })

    # 2. anomaly-derived leads
    for an in anomalies.get("anomalies", []):
        ev_rows = _evidence_rows(an["evidence_ids"])
        leads.append({
            "lead_id": f"LEAD-ANOM-{an['account_id']}",
            "title": f"Behavioural anomaly on account {an['account_id']}",
            "subject_ids": [an["account_id"]],
            "case_ids": [an["case_id"]],
            "status": ("PARTIALLY CORROBORATED - FURTHER EVIDENCE REQUIRED"
                       if len({e['source'] for e in ev_rows}) >= 2 else "INSUFFICIENT EVIDENCE"),
            "support_level": "MEDIUM" if an["anomaly_score"] > 0 else "LOW",
            "methods": [
                {"method": "Anomaly analysis (Isolation Forest)",
                 "finding": f"{an['observed']['transactions_in_hour']} transactions in one hour vs "
                            f"baseline {an['baseline']['mean_transactions_per_day']}/day",
                 "agrees": True},
                {"method": "Network analysis",
                 "finding": "Account participates in the evidence graph" if graph_store.node(an["account_id"])
                            else "Account not linked in the evidence graph",
                 "agrees": bool(graph_store.node(an["account_id"]))},
            ],
            "independent_sources": len({e["source"] for e in ev_rows}),
            "supporting_evidence": ev_rows,
            "contradicting_evidence": [],
            "missing_evidence": ["Authorized financial record corroboration",
                                 "Explanation of legitimate business activity"],
            "why": ["Transaction volume deviates sharply from the account's own baseline"],
            "verification_status": "UNVERIFIED",
            "disclaimer": "Analytical anomaly / investigative lead. An anomaly is not evidence of "
                          "criminal activity.",
        })

    # 3. explicit insufficient-evidence cases
    for case_id in scope:
        case_events = [e for e in relational.all("events") if e.get("case_id") == case_id]
        case_rels = [r for r in graph_store.relationships(case_id)]
        case_ev = [e for e in relational.all("evidence") if e.get("case_id") == case_id]
        if not case_rels and len(case_ev) <= 1:
            leads.append({
                "lead_id": f"LEAD-INSUFF-{case_id}",
                "title": f"{case_id}: no supported relationship can be established",
                "subject_ids": [],
                "case_ids": [case_id],
                "status": "INSUFFICIENT EVIDENCE",
                "support_level": "INSUFFICIENT",
                "methods": [
                    {"method": "Network analysis", "finding": "No evidence-backed relationships present",
                     "agrees": False},
                    {"method": "Temporal analysis",
                     "finding": f"{len(case_events)} timestamped event(s) available", "agrees": False},
                ],
                "independent_sources": len({e["source"] for e in case_ev}),
                "supporting_evidence": _evidence_rows([e["evidence_id"] for e in case_ev]),
                "contradicting_evidence": [],
                "missing_evidence": [
                    "Any prior linked case", "Communication records (CDR)", "Surveillance record",
                    "Vehicle association", "Financial record", "Any corroborated relationship",
                ],
                "why": ["Available evidence is insufficient to establish a supported relationship."],
                "verification_status": "UNVERIFIED",
                "disclaimer": "The absence of evidence is reported explicitly rather than inferred over.",
            })

    order = {"CORROBORATED ANALYTICAL LEAD": 0, "CONTRADICTORY EVIDENCE": 1,
             "PARTIALLY CORROBORATED - FURTHER EVIDENCE REQUIRED": 2, "INSUFFICIENT EVIDENCE": 3}
    leads.sort(key=lambda l: (order.get(l["status"], 9), -l["independent_sources"]))

    return {
        "agent": AGENT_NAME,
        "case_scope": scope,
        "leads": leads,
        "summary": {
            "corroborated": sum(1 for l in leads if l["status"] == "CORROBORATED ANALYTICAL LEAD"),
            "contradictory": sum(1 for l in leads if l["status"] == "CONTRADICTORY EVIDENCE"),
            "partial": sum(1 for l in leads if l["status"].startswith("PARTIALLY")),
            "insufficient": sum(1 for l in leads if l["status"] == "INSUFFICIENT EVIDENCE"),
        },
        "sufficient": bool(leads),
        "message": "" if leads else "INSUFFICIENT EVIDENCE: nothing in the authorized scope reaches "
                                    "the threshold for an analytical lead.",
    }


# --------------------------------------------------------------------------
# HYPOTHESES
# --------------------------------------------------------------------------
def hypotheses(case_ids: Optional[list[str]] = None) -> dict[str, Any]:
    corr = corroborate(case_ids)
    sets: list[dict[str, Any]] = []

    for lead in corr["leads"]:
        if lead["status"] == "INSUFFICIENT EVIDENCE" and not lead["subject_ids"]:
            sets.append({
                "hypothesis_set_id": f"HS-{lead['lead_id']}",
                "observation": lead["title"],
                "case_ids": lead["case_ids"],
                "hypotheses": [{
                    "hypothesis_id": "H0",
                    "statement": "No supportable relationship can currently be assessed",
                    "supporting_evidence": [],
                    "contradicting_evidence": [],
                    "missing_information": lead["missing_evidence"],
                    "support_score": 0.0,
                    "support_level": "INSUFFICIENT",
                    "rank": 1,
                }],
                "status": "INSUFFICIENT EVIDENCE",
                "note": "Available evidence is insufficient to establish a supported relationship.",
            })
            continue

        supporting = lead["supporting_evidence"]
        contradicting = lead["contradicting_evidence"]
        independent = lead["independent_sources"]
        repeated = any("Repeated activity" in m["finding"] for m in lead["methods"] if m["agrees"])
        structural = any(m["method"] == "Network analysis" and m["agrees"] for m in lead["methods"])

        h1_support = round(min(0.92, 0.18 * independent + (0.22 if repeated else 0)
                               + (0.14 if structural else 0)
                               + (0.20 if lead["support_level"] == "HIGH" else 0.10)
                               - (0.18 if contradicting else 0)), 2)
        h2_support = round(min(0.85, 0.30 + (0.12 if not repeated else 0)
                               + (0.18 if contradicting else 0)
                               + (0.10 if independent < 2 else 0)), 2)
        h3_support = round(min(0.80, 0.34 - 0.08 * max(0, independent - 1)
                               + (0.16 if not repeated else -0.06)), 2)

        hyps = [
            {
                "hypothesis_id": "H1",
                "statement": "Potential operational association between the linked entities",
                "supporting_evidence": [e["evidence_id"] for e in supporting],
                "supporting_signals": lead["why"],
                "contradicting_evidence": [c.get("contradiction_id") for c in contradicting],
                "missing_information": lead["missing_evidence"],
                "support_score": max(h1_support, 0.0),
            },
            {
                "hypothesis_id": "H2",
                "statement": "Legitimate shared activity (shared transport, employment, family or "
                             "commercial relationship)",
                "supporting_evidence": [e["evidence_id"] for e in supporting[:1]],
                "supporting_signals": ["Same identifiers can arise from lawful shared use",
                                       "No independent evidence of unlawful purpose"],
                "contradicting_evidence": [],
                "missing_information": ["Ownership / employment records", "Purpose-of-use statement"],
                "support_score": max(h2_support, 0.0),
            },
            {
                "hypothesis_id": "H3",
                "statement": "Repeated coincidence in a high-traffic location or shared public infrastructure",
                "supporting_evidence": [],
                "supporting_signals": ["Locations involved are public and high-throughput"],
                "contradicting_evidence": [e["evidence_id"] for e in supporting[1:2]],
                "missing_information": ["Location footfall baseline", "Independent identification"],
                "support_score": max(h3_support, 0.08),
            },
        ]
        hyps.sort(key=lambda h: h["support_score"], reverse=True)
        for i, h in enumerate(hyps):
            h["rank"] = i + 1
            h["support_level"] = ("MEDIUM" if h["support_score"] >= 0.55 else
                                  "LOW" if h["support_score"] >= 0.3 else "INSUFFICIENT")

        sets.append({
            "hypothesis_set_id": f"HS-{lead['lead_id']}",
            "observation": lead["title"],
            "case_ids": lead["case_ids"],
            "subject_ids": lead["subject_ids"],
            "hypotheses": hyps,
            "status": lead["status"],
            "ranking_method": "Structured evidence support: independent sources, repeated temporal "
                              "pattern, structural corroboration, contradictions.",
            "note": "Competing hypotheses are presented without any claim of certainty. "
                    "No hypothesis asserts guilt.",
        })

    return {
        "agent": AGENT_NAME,
        "case_scope": corr["case_scope"],
        "hypothesis_sets": sets,
        "sufficient": bool(sets),
        "message": "" if sets else "INSUFFICIENT EVIDENCE: no observation supports hypothesis generation.",
    }


# --------------------------------------------------------------------------
# INFORMATION GAPS
# --------------------------------------------------------------------------
GAP_TYPE_MAP = {
    "CONTRADICTION": "CONTRADICTION",
    "Independent corroborating source (currently a single source type)": "INDEPENDENT_CORROBORATION",
    "Human-verified supporting evidence": "HUMAN_VALIDATION",
    "Repeated temporal pattern": "TEMPORAL_CONTEXT",
    "Identity confirmation for the candidate person match": "IDENTITY_CONFIRMATION",
    "Authorized financial record corroboration": "FINANCIAL_CONTEXT",
    "Explanation of legitimate business activity": "BEHAVIOURAL_BASELINE",
}


def information_gaps(case_ids: Optional[list[str]] = None) -> dict[str, Any]:
    corr = corroborate(case_ids)
    gaps: list[dict[str, Any]] = []
    counter = 1

    for lead in corr["leads"]:
        known = list(lead["why"])
        for m in lead["methods"]:
            if m["agrees"]:
                known.append(f"{m['method']}: {m['finding']}")
        unknown = lead["missing_evidence"]
        if not unknown:
            continue
        gap_types = sorted({
            "CONTRADICTION" if u.startswith("Resolution of contradictory evidence")
            else GAP_TYPE_MAP.get(u, "INDEPENDENT_CORROBORATION")
            for u in unknown})
        severity = ("HIGH" if lead["status"] in {"INSUFFICIENT EVIDENCE", "CONTRADICTORY EVIDENCE"}
                    else "MEDIUM" if len(unknown) >= 3 else "LOW")
        recommended = rank_actions(gap_types, lead["case_ids"])[:1]
        gaps.append({
            "gap_id": f"IG-{counter:03d}",
            "lead_id": lead["lead_id"],
            "case_ids": lead["case_ids"],
            "question": "What evidence would strengthen or weaken this relationship?",
            "hypothesis": lead["title"],
            "known": known,
            "unknown": unknown,
            "gap_types": gap_types,
            "severity": severity,
            "status": lead["status"],
            "statement": ("Available evidence is insufficient to establish a supported relationship."
                          if lead["status"] == "INSUFFICIENT EVIDENCE" else
                          "Current evidence is insufficient to strongly establish this relationship."),
            "recommended_analysis": recommended[0]["title"] if recommended else
                                    "No authorized analytical action available for this gap.",
            "recommended_action": recommended[0] if recommended else None,
        })
        counter += 1

    return {
        "agent": AGENT_NAME,
        "case_scope": corr["case_scope"],
        "gaps": gaps,
        "sufficient": bool(gaps),
        "message": "" if gaps else "No open information gaps in the authorized scope.",
    }


# --------------------------------------------------------------------------
# NEXT-BEST ANALYTICAL ACTION
# --------------------------------------------------------------------------
def rank_actions(gap_types: list[str], case_ids: list[str]) -> list[dict[str, Any]]:
    ranked = []
    for action in ACTION_CATALOGUE:
        overlap = set(action["gap_types"]) & set(gap_types)
        if not overlap:
            continue
        value = round(min(0.99, action["base_value"] + 0.05 * (len(overlap) - 1)), 2)
        ranked.append({
            **{k: v for k, v in action.items() if k != "base_value"},
            "information_value": value,
            "addresses": sorted(overlap),
            "case_ids": case_ids,
        })
    ranked.sort(key=lambda a: a["information_value"], reverse=True)
    for i, a in enumerate(ranked):
        a["rank"] = i + 1
    return ranked


def next_best_action(case_ids: Optional[list[str]] = None) -> dict[str, Any]:
    gaps = information_gaps(case_ids)
    gap_types: dict[str, int] = {}
    for g in gaps["gaps"]:
        for t in g["gap_types"]:
            gap_types[t] = gap_types.get(t, 0) + 1

    if not gap_types:
        return {
            "agent": AGENT_NAME, "actions": [], "sufficient": False,
            "message": "No open information gaps - no analytical action is currently prioritised.",
            "gap_profile": {},
        }

    scope = gaps["case_scope"]
    ranked = []
    for action in ACTION_CATALOGUE:
        overlap = set(action["gap_types"]) & set(gap_types.keys())
        if not overlap:
            continue
        demand = sum(gap_types[t] for t in overlap)
        value = round(min(0.99, action["base_value"] + 0.03 * demand), 2)
        ranked.append({
            "action_id": action["action_id"],
            "title": action["title"],
            "endpoint": action["endpoint"],
            "method": action["method"],
            "addresses": sorted(overlap),
            "open_gaps_addressed": demand,
            "information_value": value,
            "rationale": action["rationale"],
            "authorization": "Analytical decision support only - no operational or enforcement action.",
            "case_ids": scope,
        })
    ranked.sort(key=lambda a: (a["information_value"], a["open_gaps_addressed"]), reverse=True)
    for i, a in enumerate(ranked):
        a["rank"] = i + 1

    top = ranked[0] if ranked else None
    return {
        "agent": AGENT_NAME,
        "case_scope": scope,
        "gap_profile": gap_types,
        "actions": ranked,
        "recommended": top,
        "explanation": (f"'{top['title']}' has the highest expected information value for resolving "
                        f"the current gap ({', '.join(top['addresses'])})." if top else ""),
        "sufficient": bool(ranked),
        "constraint": "The catalogue contains analytical actions only. Arrest, surveillance, "
                      "intrusive or unauthorized actions are never recommended.",
    }
