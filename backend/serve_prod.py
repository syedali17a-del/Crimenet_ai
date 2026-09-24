"""CrimeNet AI — single-origin production entrypoint (deployment only).

Why this file exists
--------------------
The SPA calls the API with *relative* paths (`fetch('/api/cases')`) and the client
reads no `VITE_*` base-URL variable, so in production the UI and the API must be
served from the SAME origin. Anyone who deploys `frontend/dist` on a static host
and the API on a second host gets a login screen that can never reach `/api` —
the relative request hits the static host, which has no API.

This entrypoint removes that failure mode by serving both from one process:

    /api/*    -> the FastAPI application, unchanged (routers, /api/docs, openapi)
    /assets/* -> the fingerprinted build output (immutable, 1-year cache)
    /*        -> the built SPA, with an index.html fallback so a deep link such
                 as /audit or /network still loads the app (client-side routing)

It is additive: `app.main` is imported as-is, so nothing about the development
setup (`uvicorn app.main:app` + `vite dev`) changes. `app.main` is also still the
module the verification scripts and the API contract tests exercise.

Run
---
    uvicorn serve_prod:app --host 0.0.0.0 --port "${PORT:-8000}"
    # or simply:  python3 serve_prod.py

Environment
-----------
    CRIMENET_DIST        path to the built SPA (default: ../frontend/dist)
    CRIMENET_BUILD_ON_BOOT  "1" to run `npm run build` first if dist is missing
    PORT                 port used by `python3 serve_prod.py` (default 8000)

Everything else (secrets, ledger path, object storage, TLS mode, backing services)
is read by app.main / app.config exactly as in development.
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.staticfiles import StaticFiles

from app.config import APP_VERSION, DATA_CLASSIFICATION, ENVIRONMENT, TLS_MODE
from app.main import app

_HERE = Path(__file__).resolve().parent
FRONTEND = _HERE.parent / "frontend"
DIST = Path(os.getenv("CRIMENET_DIST", str(FRONTEND / "dist"))).resolve()
INDEX = DIST / "index.html"

# Gzip is applied to API JSON and to the HTML/CSS/JS the app serves. (In a typical
# gateway deployment Caddy/nginx also compresses; doing it here keeps a bare
# `uvicorn serve_prod:app` deployment correct on its own.)
app.add_middleware(GZipMiddleware, minimum_size=1024)

_CACHE = "public, max-age=31536000, immutable"          # hashed asset filenames
_NO_CACHE = "no-cache, no-store, must-revalidate"       # index.html / API


def _ensure_dist() -> None:
    """Build the SPA if it is missing and the operator opted in; else fail loudly."""
    if INDEX.is_file():
        return
    if os.getenv("CRIMENET_BUILD_ON_BOOT", "").strip().lower() in {"1", "true", "yes", "on"}:
        print(f"· {DIST} not found — running `npm run build` (CRIMENET_BUILD_ON_BOOT=1)", flush=True)
        subprocess.run(["npm", "install", "--no-audit", "--no-fund"], cwd=FRONTEND, check=True)
        subprocess.run(["npm", "run", "build"], cwd=FRONTEND, check=True)
        if INDEX.is_file():
            return
    raise RuntimeError(
        f"REFUSING TO START: no built SPA at {INDEX}. Build it first:\n"
        f"    cd {FRONTEND} && npm install && npm run build\n"
        "or set CRIMENET_DIST to the directory that holds index.html."
    )


_ensure_dist()
_ASSETS = DIST / "assets"
if _ASSETS.is_dir():
    app.mount("/assets", StaticFiles(directory=str(_ASSETS)), name="assets")

_EXTRA_ROOT_FILES = {
    "favicon.ico", "favicon.svg", "robots.txt", "manifest.webmanifest", "logo.svg",
}


@app.middleware("http")
async def cache_policy(request, call_next):
    """Cache policy for everything this process serves.

    `/assets/*` is served by the StaticFiles mount above, which sets ETag /
    Last-Modified but no Cache-Control, so the rule is applied here rather than in
    the route body: fingerprinted filenames are immutable for a year, while the SPA
    shell and every API response must revalidate (a stale index.html would pin
    users to an old bundle).
    """
    response = await call_next(request)
    path = request.url.path
    if response.status_code == 200 and "cache-control" not in response.headers:
        if path.startswith("/assets/"):
            response.headers["Cache-Control"] = _CACHE
        elif path.startswith("/api/"):
            # Case data, evidence text and audit records must not be retained by any
            # shared/proxy cache between the officer and the application.
            response.headers["Cache-Control"] = "no-store"
        else:
            response.headers["Cache-Control"] = _NO_CACHE
    return response


@app.get("/deployment", include_in_schema=False)
def deployment_info() -> dict[str, object]:
    """Small operational endpoint: what this process is serving and from where."""
    return {
        "serving": "SPA + API on one origin",
        "spa_root": str(DIST),
        "spa_built": datetime.fromtimestamp(INDEX.stat().st_mtime, tz=timezone.utc).isoformat(),
        "environment": ENVIRONMENT,
        "app_version": APP_VERSION,
        "classification": DATA_CLASSIFICATION,
        "tls_mode": TLS_MODE,
    }


@app.get("/{full_path:path}", include_in_schema=False)
def spa(full_path: str) -> Response:
    """Serve the SPA, and only the SPA.

    Ordering note: this catch-all is registered AFTER the API routers and after the
    /assets mount, so real API routes win. The rules below keep the two failure
    modes honest: an unknown /api/... path returns a JSON 404 (never HTML), and a
    missing asset returns 404 (never index.html, which would turn a broken script
    tag into a confusing "Unexpected token '<'").
    """
    path = full_path.lstrip("/")

    if path == "api" or path.startswith("api/"):
        raise HTTPException(status_code=404, detail=f"No such analytical endpoint: /{path}")

    if path:
        candidate = (DIST / path).resolve()
        if str(candidate).startswith(str(DIST)) and candidate.is_file():
            # Hashed build output under /assets is immutable; anything else revalidates.
            cache = _CACHE if path.startswith("assets/") else _NO_CACHE
            return FileResponse(candidate, headers={"Cache-Control": cache})
        if Path(path).suffix and path not in _EXTRA_ROOT_FILES:
            raise HTTPException(status_code=404, detail=f"Not found: /{path}")

    return FileResponse(
        INDEX,
        media_type="text/html",
        headers={
            "Cache-Control": _NO_CACHE,
            "X-CrimeNet-Classification": DATA_CLASSIFICATION,
        },
    )


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    print(f"▶ CrimeNet AI — serving {DIST} and the API on http://0.0.0.0:{port}", flush=True)
    uvicorn.run(app, host="0.0.0.0", port=port, proxy_headers=True, forwarded_allow_ips="*")


# Keep linters that expect a module-level ASGI callable quiet about the import order.
_ = JSONResponse  # noqa: F841 - kept so the import list reads as a manifest
_ = sys
