"""CrimeNet AI - FastAPI application entrypoint.

Evidence-Driven Criminal Network Reconstruction & Investigation Intelligence.
Evidence → Relationships → Analysis → Validation.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api import analysis, audit, auth, cases, entities, evidence, intel, security
from .config import (APP_DESCRIPTION, APP_NAME, APP_TAGLINE, APP_VERSION, DATA_CLASSIFICATION,
                     TLS_MODE, log_secret_posture, security_preflight)
from .database.neo4j_graph import graph_store
from .database.object_storage import object_storage
from .database.postgres import relational
from .database.redis_cache import cache
from .database.seed import load as load_seed

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("crimenet")

# Fail fast (before the app is served) if a non-demo deployment has no secrets or is
# still on the published literals. In the demo profile a fresh random secret is
# generated per process instead of falling back to the published one, so the
# published string cannot sign a valid token anywhere by default.
_PREFLIGHT = security_preflight()
_SECRET_MESSAGES = log_secret_posture(logger)

app = FastAPI(
    title=APP_NAME,
    description=f"{APP_DESCRIPTION} — {APP_TAGLINE}",
    version=APP_VERSION,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=".*",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:  # pragma: no cover - safety net, never leak a stack trace
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "An internal analytical service error occurred. "
                               "The request was not completed.", "code": "INTERNAL_ERROR"},
        )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-CrimeNet-Classification"] = DATA_CLASSIFICATION
    response.headers["X-CrimeNet-TLS"] = TLS_MODE
    response.headers["X-Response-Time-ms"] = f"{(time.perf_counter() - started) * 1000:.1f}"
    return response


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    codes = {400: "BAD_REQUEST", 401: "UNAUTHENTICATED", 403: "FORBIDDEN", 404: "NOT_FOUND",
             409: "CONFLICT", 413: "PAYLOAD_TOO_LARGE", 422: "VALIDATION_ERROR"}
    return JSONResponse(status_code=exc.status_code,
                        content={"detail": exc.detail, "code": codes.get(exc.status_code, "ERROR")})


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    fields = []
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", []) if p not in ("body", "query"))
        fields.append(f"{loc}: {err.get('msg')}")
    return JSONResponse(
        status_code=422,
        content={"detail": "Request validation failed. " + "; ".join(fields[:4]),
                 "code": "VALIDATION_ERROR"},
    )


for r in (auth.router, cases.router, evidence.router, entities.router, analysis.router,
          audit.router, security.router, intel.router):
    app.include_router(r)


@app.on_event("startup")
def startup() -> None:
    result = load_seed()
    logger.info("CrimeNet AI startup — synthetic dataset: %s", result)
    logger.info("PostgreSQL profile: %s", relational.profile)
    logger.info("Neo4j profile: %s", graph_store.profile)
    logger.info("Redis profile: %s", cache.profile)


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "OK",
        "product": APP_NAME,
        "tagline": APP_TAGLINE,
        "version": APP_VERSION,
        "classification": DATA_CLASSIFICATION,
        "backends": {
            "postgresql": relational.profile,
            "neo4j": graph_store.profile,
            "redis": cache.profile,
            "object_storage": object_storage.profile,
        },
    }


@app.get("/api/meta")
def meta() -> dict[str, Any]:
    return {
        "name": APP_NAME,
        "tagline": APP_TAGLINE,
        "description": APP_DESCRIPTION,
        "classification": DATA_CLASSIFICATION,
        "principle": ("AI finds patterns. Evidence supports them. Specialized agents corroborate them. "
                      "Security protects them. Humans decide what they mean."),
        "workflow": ["LOGIN", "DASHBOARD", "CREATE / SELECT CASE", "UPLOAD / SELECT EVIDENCE",
                     "PROCESS EVIDENCE", "VIEW EXTRACTED ENTITIES", "CROSS-CASE CORRELATION",
                     "ENTITY RESOLUTION", "BUILD GRAPH", "ANALYZE NETWORK", "ANALYZE TIMELINE",
                     "ANALYZE ANOMALIES", "CORROBORATE", "VIEW HYPOTHESES", "VIEW INFORMATION GAPS",
                     "VIEW NEXT-BEST ACTION", "HUMAN VALIDATION", "INTEGRITY / AUDIT"],
        "safety_rules": [
            "Never infer identity from a single weak signal.",
            "Never automatically label a person a criminal.",
            "Never automatically merge identities.",
            "Never treat an anomaly as guilt.",
            "Never treat co-location as proof of meeting.",
            "Never treat graph centrality as proof of criminal leadership.",
            "Never fabricate evidence, CCTV or CDR records.",
            "Synthetic demonstration data is always labelled.",
            "Insufficient evidence is reported explicitly with the information gap.",
        ],
    }
