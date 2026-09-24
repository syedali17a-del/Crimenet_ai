#!/usr/bin/env bash
# CrimeNet AI — release/deploy step for a VM install (run after `git pull`)
#
#   cd /opt/crimenet && sudo bash deploy/update.sh
#
# Run as root: it installs dependencies, builds, restarts the systemd service and
# then verifies the live deployment. Build steps are executed as the application
# user (APP_USER, default "crimenet") so node_modules/ and dist/ end up owned by
# the account the service runs as.
#
# Idempotent, and it refuses to report success unless the checks pass.
set -euo pipefail

APP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_USER="${APP_USER:-crimenet}"
VENV="${VENV:-$APP_ROOT/venv}"
PY="$VENV/bin/python"
ENV_FILE="${ENV_FILE:-/etc/crimenet/crimenet.env}"
SERVICE="${SERVICE:-crimenet}"
BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

echo "▶ CrimeNet AI release — $APP_ROOT (app user: $APP_USER)"

[ -x "$PY" ] || { echo "✖ no interpreter at $PY — create it: python3 -m venv $APP_ROOT/venv"; exit 1; }
[ -f "$ENV_FILE" ] || { echo "✖ no env file at $ENV_FILE — copy deploy/crimenet.env.example"; exit 1; }

# Root drops to the app user for build steps; a non-root run just uses the current one.
if [ "$(id -u)" -eq 0 ] && id "$APP_USER" >/dev/null 2>&1; then
  AS_APP=(runuser -u "$APP_USER" --)
else
  AS_APP=()
  echo "· (not running as root — building as $(id -un); ownership will not be adjusted)"
fi

# --- 1. host requirements ----------------------------------------------------
command -v node >/dev/null || { echo "✖ node is required at build time (npm run build)"; exit 1; }

# --- 2. backend dependencies -------------------------------------------------
echo "· python dependencies"
"${AS_APP[@]}" "$PY" -m pip install --quiet --upgrade pip
"${AS_APP[@]}" "$PY" -m pip install --quiet -r "$APP_ROOT/backend/requirements.txt"

# The statistical NER model is a separate download, not a pip requirement. Without
# it entity_agent falls back to spaCy blank(en) + rules and /api/health reports
# that honestly — correct, but lower extraction quality.
echo "· spaCy model en_core_web_sm"
"${AS_APP[@]}" "$PY" - <<'PY' || "${AS_APP[@]}" "$PY" -m pip install --quiet \
    "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl"
import spacy
spacy.load("en_core_web_sm")
print("  already installed")
PY

# --- 3. frontend build -------------------------------------------------------
echo "· frontend build"
cd "$APP_ROOT/frontend"
"${AS_APP[@]}" npm ci --no-audit --no-fund
"${AS_APP[@]}" npm run build
[ -f dist/index.html ] || { echo "✖ build produced no dist/index.html"; exit 1; }

# --- 4. persistent state directory ------------------------------------------
LEDGER_DIR=""
if LEDGER_PATH="$(grep -E '^CRIMENET_LEDGER_PATH=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '\r')" && [ -n "$LEDGER_PATH" ]; then
  LEDGER_DIR="$(dirname "$LEDGER_PATH")"
  if [ "$(id -u)" -eq 0 ]; then
    install -d -o "$APP_USER" -g "$APP_USER" -m 0750 "$LEDGER_DIR"
    echo "· state directory ready: $LEDGER_DIR (owned by $APP_USER)"
  fi
fi

# --- 5. restart --------------------------------------------------------------
echo "· restarting $SERVICE"
if command -v systemctl >/dev/null 2>&1 && [ "$(id -u)" -eq 0 ]; then
  systemctl restart "$SERVICE"
else
  echo "  (systemd not available or not root — restart the service yourself)"
fi

for _ in $(seq 1 40); do
  curl -sf "$BASE_URL/api/health" >/dev/null 2>&1 && break
  sleep 0.5
done
curl -sf "$BASE_URL/api/health" >/dev/null || { echo "✖ $BASE_URL/api/health is not answering — check journalctl -u $SERVICE -n 50"; exit 1; }

# --- 6. verify the live deployment (do not report success otherwise) ---------
cd "$APP_ROOT"
echo "· verifying (33-stage acceptance workflow)"
bash backend/verify_workflow.sh "$BASE_URL" | tail -3
"$PY" - <<PY
import json, urllib.request
h = json.load(urllib.request.urlopen("${BASE_URL}/api/health"))
print("· health:", h["status"], "| version", h["version"], "|", h["classification"])
print("· profiles:", h["backends"])
PY

[ -n "$LEDGER_DIR" ] && echo "· remember to back up: $LEDGER_DIR"
echo "✔ release complete — now confirm the public URL: curl -sI https://<your-host>/ | head -1"
