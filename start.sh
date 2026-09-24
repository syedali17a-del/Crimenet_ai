#!/usr/bin/env bash
# CrimeNet AI - start both services (backend :8000, frontend :5173)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "▶ CrimeNet AI — starting analytical services"

# --- dependency check (sandbox resets wipe node_modules / site-packages) ------
python3 - <<'PY' || pip install -q fastapi uvicorn rapidfuzz PyJWT python-multipart redis neo4j
import importlib, sys
for m in ("fastapi", "uvicorn", "rapidfuzz", "jwt", "multipart"):
    importlib.import_module(m)
PY
python3 -c "import spacy; spacy.load('en_core_web_sm')" 2>/dev/null || \
  pip install -q https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
[ -d "$ROOT/frontend/node_modules" ] || (cd "$ROOT/frontend" && npm install --silent)

# --- backend ------------------------------------------------------------------
cd "$ROOT/backend"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level warning &
BACKEND_PID=$!
trap 'kill $BACKEND_PID 2>/dev/null || true' EXIT

for _ in $(seq 1 40); do
  curl -sf http://127.0.0.1:8000/api/health >/dev/null 2>&1 && break
  sleep 0.5
done
echo "✔ API server ready on :8000  (docs http://localhost:8000/api/docs)"

# --- frontend (foreground) ----------------------------------------------------
cd "$ROOT/frontend"
exec npm run dev
