"""RBAC: permission catalogue, role grants, case-level authorization, agent permissions."""
from __future__ import annotations

from typing import Any

PERMISSIONS: dict[str, str] = {
    "case:read": "View authorized cases",
    "case:create": "Create new investigation cases",
    "case:assign": "Assign investigators to a case",
    "case:close": "Change case status / close case",
    "evidence:read": "View evidence metadata and processed text",
    "evidence:upload": "Register new evidence into the registry",
    "evidence:process": "Run the document intelligence pipeline",
    "evidence:integrity": "Run SHA-256 integrity verification",
    "analysis:run": "Execute authorized analytical services",
    "entity:annotate": "Record investigator annotations",
    "verification:submit": "Submit a finding for supervisory review",
    "verification:decide": "Verify or reject analytical findings",
    "audit:read": "Read the audit trail",
    "audit:export": "Export audit / ledger records",
    "security:read": "View the security posture dashboard",
    "user:manage": "Create, disable and re-role users",
    "permission:manage": "Change role and case permissions",
    "ledger:read": "Read permissioned ledger blocks",
}

ROLE_GRANTS: dict[str, set[str]] = {
    "INVESTIGATOR": {
        "case:read", "evidence:read", "evidence:upload", "evidence:process",
        "evidence:integrity", "analysis:run", "entity:annotate",
        "verification:submit", "audit:read", "security:read", "ledger:read",
    },
    "ANALYST": {
        "case:read", "evidence:read", "evidence:process", "evidence:integrity",
        "analysis:run", "entity:annotate", "verification:submit", "audit:read",
        "security:read", "ledger:read",
    },
    "SUPERVISOR": {
        "case:read", "case:create", "case:assign", "case:close", "evidence:read",
        "evidence:upload", "evidence:process", "evidence:integrity", "analysis:run",
        "entity:annotate", "verification:submit", "verification:decide",
        "audit:read", "audit:export", "security:read", "ledger:read",
    },
    "ADMIN": set(PERMISSIONS.keys()),
}

ROLE_SUMMARY: dict[str, str] = {
    "INVESTIGATOR": "View assigned cases, process evidence, run analysis, submit findings for verification.",
    "ANALYST": "Run analytical services across authorized cases and submit findings for verification.",
    "SUPERVISOR": "Review, verify/reject findings, create and assign cases, export audit records.",
    "ADMIN": "Manage users, roles, case permissions and the full audit / ledger surface.",
}

# Capabilities that no agent may ever hold, regardless of the invoking user's role.
AGENT_FORBIDDEN = [
    "permission:manage", "user:manage", "evidence:delete", "audit:modify",
    "case:access-unauthorized", "verification:decide",
]

AGENT_PERMISSIONS: dict[str, list[str]] = {
    "MANAGER_AGENT": ["task:plan", "task:delegate", "analysis:invoke", "audit:append"],
    "DOCUMENT_INTELLIGENCE_AGENT": ["evidence:read", "evidence:process", "audit:append"],
    "ENTITY_RESOLUTION_AGENT": ["entity:read", "entity:candidate-match", "audit:append"],
    "EVIDENCE_PROVENANCE_AGENT": ["evidence:read", "evidence:hash", "ledger:append", "audit:append"],
    "NETWORK_TEMPORAL_AGENT": ["graph:read", "analysis:invoke", "audit:append"],
    "INVESTIGATION_REASONING_AGENT": ["analysis:read", "hypothesis:generate", "audit:append"],
}


def permissions_for(role: str) -> list[str]:
    return sorted(ROLE_GRANTS.get(role, set()))


def has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_GRANTS.get(role, set())


def can_access_case(case_access: list[str], case_id: str | None) -> bool:
    if case_id is None:
        return True
    return "*" in (case_access or []) or case_id in (case_access or [])


def role_matrix() -> list[dict[str, Any]]:
    return [
        {
            "permission": perm,
            "description": desc,
            "roles": [r for r in ROLE_GRANTS if perm in ROLE_GRANTS[r]],
        }
        for perm, desc in PERMISSIONS.items()
    ]
