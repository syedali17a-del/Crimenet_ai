"""Security posture, RBAC administration and agent permission API."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ..agents import evidence_agent, manager
from ..agents.document_agent import ocr_engine
from ..agents.entity_agent import backend_info
from ..audit import audit_log, ledger, ledger_store
from ..config import (APP_VERSION, DATA_CLASSIFICATION, ENVIRONMENT, IS_DEMO, JWT_ALGORITHM,
                      JWT_EXPIRY_MINUTES, LOGIN_ATTEMPT_WINDOW_SECONDS, LOGIN_LOCKOUT_SECONDS,
                      LOGIN_MAX_ATTEMPTS, TLS_MODE, insecure_secrets, secret_posture)
from ..database.neo4j_graph import graph_store
from ..database.object_storage import object_storage
from ..database.postgres import relational
from ..database.redis_cache import cache
from ..models.domain import now_iso
from ..schemas.api import UserCreate, UserPatch
from ..security.crypto import hash_password, sha256_bytes
from ..security.deps import Principal, get_principal, require_permission
from ..security.rbac import AGENT_FORBIDDEN, PERMISSIONS, ROLE_SUMMARY, permissions_for, role_matrix

router = APIRouter(prefix="/api/security", tags=["security"])


@router.get("/status")
def security_status(principal: Principal = Depends(require_permission("security:read"))) -> dict[str, Any]:
    integrity = evidence_agent.registry_summary()
    chain = ledger.verify_chain()
    return {
        "authentication": {
            "status": "AUTHENTICATED",
            "mechanism": "JWT (PyJWT)",
            "algorithm": JWT_ALGORITHM,
            "session_lifetime_minutes": JWT_EXPIRY_MINUTES,
            "user": principal.user_id,
            "display_name": principal.display_name,
            "role": principal.role,
        },
        "authorization": {
            "model": "RBAC + case-level authorization",
            "role": principal.role,
            "role_summary": ROLE_SUMMARY.get(principal.role, ""),
            "permissions": principal.permissions,
            "case_access": principal.case_access,
            "enforcement": "Server-side on every endpoint (FastAPI dependency guard).",
        },
        "transport": {
            "tls": TLS_MODE,
            "detail": "TLS is terminated at the ingress gateway in this environment. "
                      "The application enforces auth on every request regardless of transport.",
        },
        "encryption": {
            "at_rest_fields": "Phone / account identifiers stored with authenticated field encryption.",
            "algorithm": "AES-256-GCM (authenticated encryption, fresh 96-bit nonce per value, "
                         "256-bit key derived from CRIMENET_FIELD_KEY)",
            "legacy_readable": "Values written by the earlier enc:v1 development profile are still "
                               "readable; nothing new is written in that format.",
            "password_storage": "PBKDF2-HMAC-SHA256, 120k rounds, per-user salt.",
            "evidence_hashing": "SHA-256 at intake and on every integrity check.",
            "production_note": "Set CRIMENET_FIELD_KEY to a strong random value (managed KMS preferred) "
                               "for a real deployment.",
        },
        "hardening": {
            "environment": ENVIRONMENT,
            "demo_profile": IS_DEMO,
            "default_secrets_in_use": insecure_secrets(),
            "secret_posture": secret_posture(),
            "startup_policy": "The published demo secret is never used as a signing key unless "
                              "CRIMENET_ALLOW_PUBLIC_DEMO_SECRET=1 is set explicitly. With no "
                              "environment variables, the demo profile generates a random secret "
                              "for the process. A non-demo environment with no CRIMENET_JWT_SECRET "
                              "/ CRIMENET_FIELD_KEY REFUSES to start.",
            "token_transport": "Authorization: Bearer header only - tokens in the URL query string "
                               "are not accepted (they leak into logs and referrer headers).",
            "login_rate_limit": {
                "max_attempts": LOGIN_MAX_ATTEMPTS,
                "window_seconds": LOGIN_ATTEMPT_WINDOW_SECONDS,
                "lockout_seconds": LOGIN_LOCKOUT_SECONDS,
                "scope": "per officer ID, checked before the password is verified",
            },
        },
        "evidence_integrity": integrity,
        "audit": {
            "records": audit_log.count(),
            "append_only": True,
            "per_record_hash": "SHA-256",
            "hash_chained": True,
            "chain": audit_log.verify_chain(),
        },
        "ledger": {
            "profile": ledger.LEDGER_PROFILE,
            "persistence": ledger_store.status(),
            "witness": chain.get("witness"),
            "blocks": chain["blocks"],
            "chain_intact": chain["chain_intact"],
            "head_hash": chain["head_hash"],
        },
        "data_backends": {
            "postgresql": relational.status(),
            "neo4j": graph_store.status(),
            "redis": cache.status(),
            "object_storage": object_storage.status(),
        },
        "ai_backends": {
            "ner": backend_info(),
            "ocr": ocr_engine.status(),
        },
        "agent_permissions": manager.agent_registry(),
        "agent_prohibitions": AGENT_FORBIDDEN,
        "least_privilege": "Agents receive only the capabilities required for their task and can never "
                           "change permissions, delete evidence, modify audit history or reach "
                           "unauthorized cases.",
        "classification": DATA_CLASSIFICATION,
        "version": APP_VERSION,
        "checked_at": now_iso(),
    }


@router.get("/rbac")
def rbac_matrix(principal: Principal = Depends(require_permission("security:read"))) -> dict[str, Any]:
    return {
        "permissions": PERMISSIONS,
        "matrix": role_matrix(),
        "roles": {r: {"summary": s, "permissions": permissions_for(r)} for r, s in ROLE_SUMMARY.items()},
    }


@router.get("/users")
def list_users(principal: Principal = Depends(require_permission("user:manage"))) -> dict[str, Any]:
    users = [{k: v for k, v in u.items() if k != "password_hash"} for u in relational.all("users")]
    return {"count": len(users), "users": users}


@router.post("/users", status_code=201)
def create_user(payload: UserCreate,
                principal: Principal = Depends(require_permission("user:manage"))) -> dict[str, Any]:
    uid = payload.user_id.strip().upper()
    if relational.get("users", uid):
        raise HTTPException(status_code=409, detail=f"User {uid} already exists.")
    record = {
        "user_id": uid, "display_name": payload.display_name, "role": payload.role,
        "badge": f"TN-{payload.role[:3]}-{uid[-4:]}", "unit": payload.unit or "Unassigned (synthetic)",
        "password_hash": hash_password(payload.password), "case_access": payload.case_access,
        "active": True, "created_at": now_iso(), "classification": DATA_CLASSIFICATION,
    }
    relational.insert("users", uid, record)
    audit_log.record(principal.user_id, principal.role, "USER_CREATED", object_id=uid,
                     detail=f"Role {payload.role}; case access {payload.case_access}.")
    return {k: v for k, v in record.items() if k != "password_hash"}


@router.patch("/users/{user_id}")
def patch_user(user_id: str, payload: UserPatch,
               principal: Principal = Depends(require_permission("permission:manage"))) -> dict[str, Any]:
    user = relational.get("users", user_id)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {user_id} not found.")
    if user_id == principal.user_id and payload.active is False:
        raise HTTPException(status_code=400, detail="You cannot disable your own account.")
    patch = {k: v for k, v in payload.model_dump().items() if v is not None}
    user.update(patch)
    relational.upsert("users", user_id, user)
    audit_log.record(principal.user_id, principal.role, "USER_PERMISSIONS_UPDATED", object_id=user_id,
                     detail=", ".join(f"{k}={v}" for k, v in patch.items()))
    return {k: v for k, v in user.items() if k != "password_hash"}


@router.get("/ai-safety-posture")
def ai_safety_posture(principal: Principal = Depends(require_permission("security:read"))
                      ) -> dict[str, Any]:
    """Hallucination / prompt-injection posture of the evidence path.

    This is a claim the system can back up on demand: the evidence path contains no
    generative model. `backend/scripts/check_no_llm_in_path.py` re-checks the source and
    exits non-zero if that ever stops being true, so the claim cannot rot into marketing
    copy while the code changes underneath it.
    """
    return {
        "generative_model_in_evidence_path": False,
        "reasoning": "Entity extraction, resolution, network/anomaly analysis and hypothesis "
                     "generation are all rule-based or classical ML (spaCy NER, RapidFuzz, "
                     "NetworkX, IsolationForest). No LLM or generative model receives untrusted "
                     "document text with the ability to write to the graph, so there is no "
                     "hallucination surface and no prompt-injection surface in the evidence path.",
        "verified_by": "backend/scripts/check_no_llm_in_path.py",
        "what_that_means": {
            "untrusted_text_never_reaches_a_generative_model": True,
            "no_model_can_write_to_the_graph": True,
            "every_extracted_entity_carries_its_method": "entity_agent records the methods "
                                                         "(rule / NER / vocabulary / structural hint) "
                                                         "on each extracted entity, so a reviewer "
                                                         "sees why it was proposed.",
            "no_generated_text_in_the_ui": "Interpretation strings are templates filled from "
                                           "computed values, not generated prose.",
        },
        "model_inventory": {
            "statistical_ner": "spaCy en_core_web_sm (en_core_web_sm, statistical NER for "
                               "English text; a token-classification Transformers model is used "
                               "only if local weights are present, and it is deliberately not "
                               "required)",
            "string_matching": "RapidFuzz (deterministic edit-distance ratios)",
            "graph": "NetworkX (degree/betweenness centrality, Louvain communities)",
            "anomaly": "scikit-learn IsolationForest (classical ML, feature space documented in "
                       "app/analytics/anomaly.py)",
            "generative": "none - no openai / anthropic / langchain / LLM client is imported "
                          "anywhere in app/agents, app/analytics or app/api",
        },
        "residual_risks_we_do_not_claim_to_have_solved": [
            "Extraction is imperfect: a false positive is possible and is why every extracted "
            "entity carries a confidence and a method string, and why nothing is auto-merged.",
            "Uploaded documents can be wrong or poisoned at the source; source_trust records how "
            "the document arrived and corroboration weighs low-trust sources less.",
            "A rule-based pipeline can be wrong in a consistent way - the evaluation harness "
            "(scripts/eval_extraction.py) measures that against labelled ground truth, including "
            "negative cases that must NOT be extracted.",
        ],
        "verified_at_runtime_by": "scripts/check_no_llm_in_path.py (static check, non-zero exit "
                                  "on a generative import in the evidence path)",
        "checked_by": principal.user_id,
        "checked_at": now_iso(),
    }


@router.get("/agents")
def agents(principal: Principal = Depends(get_principal)) -> dict[str, Any]:
    return {
        "agents": [
            {"name": "MANAGER_AGENT", "kind": "Orchestration service",
             "responsibilities": ["task creation", "dependency resolution", "execution order",
                                  "result collection", "authorization checks"],
             "implementation": "app/agents/manager.py"},
            {"name": "DOCUMENT_INTELLIGENCE_AGENT", "kind": "OCR + NLP pipeline",
             "responsibilities": ["OCR abstraction", "cleaning", "language detection", "normalization"],
             "implementation": "app/agents/document_agent.py"},
            {"name": "ENTITY_RESOLUTION_AGENT", "kind": "NER + regex + RapidFuzz",
             "responsibilities": ["entity extraction", "event extraction", "normalization",
                                  "token comparison", "fuzzy matching", "multi-attribute matching"],
             "implementation": "app/agents/entity_agent.py, app/agents/resolution_agent.py"},
            {"name": "EVIDENCE_PROVENANCE_AGENT", "kind": "Integrity service",
             "responsibilities": ["SHA-256 hashing", "provenance", "chain of custody", "ledger anchoring"],
             "implementation": "app/agents/evidence_agent.py"},
            {"name": "NETWORK_TEMPORAL_AGENT", "kind": "Graph + time-series analytics",
             "responsibilities": ["centrality", "community detection", "shortest paths",
                                  "temporal patterns", "convergence", "anomaly detection"],
             "implementation": "app/agents/network_agent.py, app/agents/temporal_agent.py, "
                               "app/analytics/anomaly.py"},
            {"name": "INVESTIGATION_REASONING_AGENT", "kind": "Structured reasoning service",
             "responsibilities": ["corroboration", "competing hypotheses", "information gaps",
                                  "next-best analytical action"],
             "implementation": "app/agents/reasoning_agent.py"},
        ],
        "registry": manager.agent_registry(),
        "note": "Not all agents are LLM agents. These are specialized deterministic analytical services.",
    }


@router.post("/integrity-demo/tamper")
def integrity_tamper_demo(principal: Principal = Depends(require_permission("evidence:integrity"))
                          ) -> dict[str, Any]:
    """DEMO CONTROL - simulated insider evidence tampering (ADMIN/SUPERVISOR only).

    Runs the Phase 4 acceptance scenario against the live server, on a DEDICATED
    probe object (EV-9901) so that no real case evidence is touched:

      step 1  register the probe                -> three-way check: VERIFIED
      step 2  an "attacker" rewrites the stored object AND the registry hash so
              the two agree with each other (the case a two-way check cannot see)
      step 3  three-way check                   -> INTEGRITY MISMATCH, because the
              digest anchored in the permissioned ledger at registration still
              disagrees, and the ledger chain + independent witness are re-verified

    Every step is recorded in the audit trail.
    """
    probe_id = "EV-9901"
    key = "integrity_demo/probe.txt"
    body = b"integrity demonstration probe - original content"
    probe = {
        "evidence_id": probe_id, "case_id": "CASE-101", "evidence_type": "TEXT",
        "object_key": key, "source": "PHASE 4 integrity demonstration probe",
        "verification_status": "UNVERIFIED", "processing_status": "UPLOADED",
        "uploaded_by": principal.user_id, "sha256": "", "integrity_status": "UNCHECKED",
        "timestamp": now_iso(), "provenance": [], "text_origin": "NATIVE_TEXT",
        "notes": "Dedicated probe object for the integrity demonstration. Not case evidence.",
        # demo probes are excluded from the evidence registry views: they are not
        # case evidence and must never be presented as such.
        "demo_probe": True,
    }
    relational.upsert("evidence", probe_id, probe)
    evidence_agent.register_evidence(probe, body, principal.user_id)
    before = evidence_agent.integrity_check(probe_id, actor=principal.user_id)

    altered = b"integrity demonstration probe - content REPLACED after registration"
    object_storage.put_bytes(key, altered)
    rec = relational.get("evidence", probe_id)
    rec["sha256"] = sha256_bytes(altered)          # attacker also rewrites the stored hash
    rec["notes"] = ("Probe object altered outside the application; the registry hash was "
                    "overwritten to match, which is the tamper a two-way check cannot detect.")
    relational.upsert("evidence", probe_id, rec)
    after = evidence_agent.integrity_check(probe_id, actor=principal.user_id)

    audit_log.record(principal.user_id, principal.role, "INTEGRITY_TAMPER_DEMO",
                     case_id="CASE-101", object_id=probe_id,
                     status="SUCCESS" if after["status"] != "VERIFIED" else "FAILED",
                     detail=f"Simulated insider rewrite of {probe_id}; three-way check reported "
                            f"{after['status']}.")
    return {
        "demo": "DEMO_TAMPER_SIMULATION",
        "probe_evidence_id": probe_id,
        "note": "No case evidence is modified by this endpoint; it acts on a dedicated probe object.",
        "step_1_registered": {"status": before["status"], "legs": before["legs"]},
        "step_2_attacker_rewrote": {
            "object_replaced": True,
            "registry_hash_overwritten_to_match_object": True,
            "two_way_check_would_report": "VERIFIED (object hash == registry hash)",
        },
        "step_3_three_way_check": {
            "status": after["status"],
            "legs": after["legs"],
            "message": after["message"],
        },
        "ledger_chain": after["ledger_chain"],
    }
