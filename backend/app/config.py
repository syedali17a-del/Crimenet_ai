"""CrimeNet AI - runtime configuration.

Declared stack: PostgreSQL, Neo4j, Redis, Object Storage.
Each adapter attempts a real connection using the environment variables below.
When a real server is not reachable in this development environment the adapter
falls back to an explicitly labelled embedded profile (never silently claimed to
be the production backing store).
"""
from __future__ import annotations

import hashlib
import os
import secrets
from typing import Optional

APP_NAME = "CrimeNet AI"
APP_TAGLINE = "Evidence → Relationships → Analysis → Validation"
APP_DESCRIPTION = "Evidence-Driven Criminal Network Reconstruction & Investigation Intelligence"
APP_VERSION = "1.0.0"

DATA_CLASSIFICATION = "SYNTHETIC DEMONSTRATION DATA"

# --- Deployment environment ------------------------------------------------
# "demo" is the hackathon/demonstration profile and is the DEFAULT, so the app runs
# out of the box. Anything else (production / staging / uat ...) is treated as a real
# deployment and is held to the secret rules below.
ENVIRONMENT = os.getenv("CRIMENET_ENVIRONMENT", "demo").strip().lower()
IS_DEMO = ENVIRONMENT == "demo"

# --- Security -------------------------------------------------------------
# The two literals below are PUBLISHED (they are in this source file and have been
# quoted in public write-ups), so they are treated as fully compromised and are
# never used as a signing or encryption key unless an operator explicitly opts in
# with CRIMENET_ALLOW_PUBLIC_DEMO_SECRET=1.
#
# Secret resolution order, per key:
#   1. the environment variable (CRIMENET_JWT_SECRET / CRIMENET_FIELD_KEY)
#   2. CRIMENET_ALLOW_PUBLIC_DEMO_SECRET=1  -> the published literal (loud warning)
#   3. demo profile with nothing set       -> a RANDOM secret generated for this
#                                             process (secrets.token_urlsafe(48))
#   4. any other environment with nothing set -> no secret; startup refuses
DEFAULT_JWT_SECRET = "crimenet-dev-secret-change-in-production"
DEFAULT_FIELD_KEY = "crimenet-field-encryption-key-v1"

ALLOW_PUBLIC_DEMO_SECRET = os.getenv("CRIMENET_ALLOW_PUBLIC_DEMO_SECRET", "").strip().lower() in {
    "1", "true", "yes", "on"}


def _resolve_secret(env_var: str, published: str) -> tuple[Optional[str], str]:
    """Return (value, source) for one secret. `source` is reported at startup."""
    from_env = os.getenv(env_var)
    if from_env:
        return from_env, "ENVIRONMENT_VARIABLE"
    if ALLOW_PUBLIC_DEMO_SECRET:
        return published, "PUBLIC_DEMO_LITERAL_EXPLICITLY_ALLOWED"
    if IS_DEMO:
        # A fresh random secret per process: two demo instances cannot forge each
        # other's tokens, and nothing published can sign a valid token.
        return secrets.token_urlsafe(48), "RANDOM_PER_PROCESS"
    return None, "MISSING"


JWT_SECRET, JWT_SECRET_SOURCE = _resolve_secret("CRIMENET_JWT_SECRET", DEFAULT_JWT_SECRET)
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = int(os.getenv("CRIMENET_JWT_EXPIRY_MINUTES", "480"))
FIELD_ENCRYPTION_KEY, FIELD_KEY_SOURCE = _resolve_secret("CRIMENET_FIELD_KEY", DEFAULT_FIELD_KEY)

# Set CRIMENET_LOG_DEMO_SECRETS=1 if you need the generated per-process values
# printed to the console (e.g. to re-sign a token in a test script). Off by default
# so secrets do not end up in logs by accident.
LOG_DEMO_SECRETS = os.getenv("CRIMENET_LOG_DEMO_SECRETS", "").strip().lower() in {"1", "true", "yes", "on"}

# TLS: terminated by the ingress/reverse proxy in this environment.
TLS_MODE = os.getenv("CRIMENET_TLS_MODE", "TERMINATED_AT_GATEWAY")

# --- Data backends --------------------------------------------------------
POSTGRES_DSN = os.getenv("CRIMENET_POSTGRES_DSN", "")
NEO4J_URI = os.getenv("CRIMENET_NEO4J_URI", "")
NEO4J_USER = os.getenv("CRIMENET_NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("CRIMENET_NEO4J_PASSWORD", "")
REDIS_URL = os.getenv("CRIMENET_REDIS_URL", "")

OBJECT_STORAGE_ROOT = os.getenv(
    "CRIMENET_OBJECT_STORAGE",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "object_storage"),
)

# --- Authentication hardening ---------------------------------------------
LOGIN_MAX_ATTEMPTS = int(os.getenv("CRIMENET_LOGIN_MAX_ATTEMPTS", "5"))
LOGIN_ATTEMPT_WINDOW_SECONDS = int(os.getenv("CRIMENET_LOGIN_ATTEMPT_WINDOW", "300"))
LOGIN_LOCKOUT_SECONDS = int(os.getenv("CRIMENET_LOGIN_LOCKOUT", "300"))


class InsecureConfigurationError(RuntimeError):
    """Raised when the application is about to run with development secrets."""


def insecure_secrets() -> list[str]:
    """Names of any secret that is currently the PUBLISHED literal.

    With per-process random generation this is empty by default; it only reports a
    finding when CRIMENET_ALLOW_PUBLIC_DEMO_SECRET=1 opted back into the literal.
    """
    findings = []
    if JWT_SECRET == DEFAULT_JWT_SECRET:
        findings.append("CRIMENET_JWT_SECRET (JWT signing key)")
    if FIELD_ENCRYPTION_KEY == DEFAULT_FIELD_KEY:
        findings.append("CRIMENET_FIELD_KEY (field-encryption key)")
    return findings


def secret_posture() -> dict[str, object]:
    """What key material this process is actually using (safe to log)."""
    return {
        "jwt_secret_source": JWT_SECRET_SOURCE,
        "field_key_source": FIELD_KEY_SOURCE,
        "jwt_secret_fingerprint": (hashlib.sha256((JWT_SECRET or "").encode()).hexdigest()[:12]
                                   if JWT_SECRET else None),
        "field_key_fingerprint": (hashlib.sha256((FIELD_ENCRYPTION_KEY or "").encode()).hexdigest()[:12]
                                  if FIELD_ENCRYPTION_KEY else None),
        "published_literal_in_use": bool(insecure_secrets()),
        "allow_public_demo_secret_flag": ALLOW_PUBLIC_DEMO_SECRET,
    }


def log_secret_posture(logger: "logging.Logger | None" = None) -> list[str]:
    """Emit the one-time startup messages about key material. Returns them too."""
    import logging as _logging
    log = logger or _logging.getLogger("crimenet")
    messages: list[str] = []
    if JWT_SECRET_SOURCE == "RANDOM_PER_PROCESS":
        messages.append("demo JWT secret generated for this process - not the published "
                        f"default (fingerprint {secret_posture()['jwt_secret_fingerprint']}); "
                        "tokens become invalid when the process restarts")
    if FIELD_KEY_SOURCE == "RANDOM_PER_PROCESS":
        messages.append("demo field-encryption key generated for this process - not the "
                        f"published default (fingerprint {secret_posture()['field_key_fingerprint']})")
    if insecure_secrets():
        messages.append("SECURITY WARNING: CRIMENET_ALLOW_PUBLIC_DEMO_SECRET is set, so the "
                        "PUBLISHED demo secrets are in use (" + "; ".join(insecure_secrets()) +
                        "). Anybody who has read the source can forge tokens for this process. "
                        "Demonstration only - never expose this instance.")
    if LOG_DEMO_SECRETS and JWT_SECRET_SOURCE == "RANDOM_PER_PROCESS":
        messages.append(f"CRIMENET_LOG_DEMO_SECRETS=1: JWT_SECRET={JWT_SECRET}")
    if LOG_DEMO_SECRETS and FIELD_KEY_SOURCE == "RANDOM_PER_PROCESS":
        messages.append(f"CRIMENET_LOG_DEMO_SECRETS=1: FIELD_ENCRYPTION_KEY={FIELD_ENCRYPTION_KEY}")
    for m in messages:
        if m.startswith("SECURITY WARNING"):
            log.warning("%s", m)
        else:
            log.info("%s", m)
    return messages


def security_preflight() -> dict[str, object]:
    """Refuse to start a non-demo deployment that is still using default secrets.

    Called at application startup. In the demo profile the defaults are permitted
    but reported loudly, so the posture is never silently insecure.
    """
    if not IS_DEMO and (JWT_SECRET is None or FIELD_ENCRYPTION_KEY is None):
        raise InsecureConfigurationError(
            "REFUSING TO START: CRIMENET_ENVIRONMENT=" + ENVIRONMENT + " but " +
            ", ".join(name for name, value in (("CRIMENET_JWT_SECRET", JWT_SECRET),
                                               ("CRIMENET_FIELD_KEY", FIELD_ENCRYPTION_KEY))
                      if value is None) +
            " is not set. A non-demo deployment must supply its own secrets "
            "(for example: python -c \"import secrets;print(secrets.token_urlsafe(48))\")."
        )
    findings = insecure_secrets()
    if findings and not IS_DEMO:
        raise InsecureConfigurationError(
            "REFUSING TO START: CRIMENET_ENVIRONMENT=" + ENVIRONMENT +
            " but the following secrets are still the published development "
            "defaults: " + "; ".join(findings) +
            ". Set CRIMENET_JWT_SECRET and CRIMENET_FIELD_KEY to strong random "
            "values (for example: python -c \"import secrets;print(secrets.token_urlsafe(48))\")."
        )
    return {"environment": ENVIRONMENT, "insecure_defaults": findings,
            "published_literal_allowed": ALLOW_PUBLIC_DEMO_SECRET,
            "enforced": not IS_DEMO, **secret_posture()}


# --- Analytics ------------------------------------------------------------
RESOLUTION_HIGH = 88.0
RESOLUTION_MEDIUM = 72.0
CONVERGENCE_WINDOW_MINUTES = 30
