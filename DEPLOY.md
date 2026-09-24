# Deploying CrimeNet AI live

This document deploys the app in this repository as it stands. Nothing here changes the
application: `backend/app/main.py`, every API route, the frontend build and the four
fixed UI bugs are exactly what runs in production.

---

## 0. TL;DR — pick one path

| Path | What you get | Effort | Best for |
|---|---|---|---|
| **A. Single VM + Caddy** (section 3) | `https://crimenet.example.gov.in` with auto-TLS, one process, persistent disk | ~20 min | A real demo URL you control end to end |
| **B. PaaS two-service** (section 4B) | Free/cheap tier, no server admin | ~15 min | A quick public link for judges/reviewers |
| **B2. PaaS single service** (section 4A) | One service, one URL | ~10 min | Railway / any builder with Node + Python |
| **C. Container** | — | — | Deliberately omitted (section 5) |

**The one thing that decides the architecture:** the SPA calls the API with **relative**
paths (`fetch('/api/cases')`), and the client reads no `VITE_*` base-URL variable
(`frontend/src/services/api.ts`). The UI and the API therefore **must be served from the
same origin**. A static site on one host plus an API on another host yields a login screen
that can never reach `/api` — the request goes to the static host, which has no API.
Deploy one origin, and the problem does not exist.

To make that trivial, this repository now has a production entrypoint:

```
backend/serve_prod.py
    /api/*     -> the FastAPI application, unchanged (routers, /api/docs, openapi)
    /assets/*  -> the fingerprinted build output (1-year immutable cache)
    /*         -> frontend/dist with an SPA fallback (deep links like /audit work)
```

It imports `app.main` as-is, so development (`uvicorn app.main:app` + `vite dev`) is
untouched, and `app.main:app` remains the module the verification scripts exercise.

---

## 1. What actually ships

| Piece | Runtime need | Notes |
|---|---|---|
| `backend/` (FastAPI app) | **Python 3.11–3.13** | 6.5 MB. All state is generated in code |
| `frontend/` source → `frontend/dist` | **Node** (build only) | dist is 1.4 MB; no Node needed at runtime |
| spaCy statistical model | `python -m spacy download en_core_web_sm` | Not a pip requirement. Without it the app falls back to `spacy.blank("en")` + rules and **says so** in `/api/health` — correct but lower extraction quality |
| Persistent state | disk | `backend/ledger.db*` (audit hash chain), `backend/object_storage/` (write-once evidence blobs) |
| Backing services | optional | PostgreSQL / Neo4j / Redis. Unset → clearly labelled `EMBEDDED_*` fallbacks, reported in `/api/health` |
| Uploads | 5 MB app cap (`413` from the app) | Raise the proxy limit slightly above it, not below |

`datasets/` (3.5 MB) and `tools/` (5.2 MB) are **not** needed at runtime — only the
`backend/` and `frontend/dist` trees plus the Python venv are.

Not needed: Docker, Kubernetes, any external queue/workflow system. One process serves the
whole product.

---

## 2. Before you start — decide your profile

`CRIMENET_ENVIRONMENT` controls the secret rules in `backend/app/config.py`:

| Profile | Behaviour | Use for |
|---|---|---|
| `demo` (default) | Both secrets are generated **randomly per process**. Nothing published can sign a valid token, but **every restart invalidates existing sessions** | A judge demo where a forced re-login is acceptable |
| `production` | **Refuses to start** unless `CRIMENET_JWT_SECRET` and `CRIMENET_FIELD_KEY` are set, and refuses to start if they are still the published literals | Anything you hand to real officers |

Generate the two secrets once and store them somewhere you can back up:

```bash
python3 -c "import secrets; print('CRIMENET_JWT_SECRET=' + secrets.token_urlsafe(48))"
python3 -c "import secrets; print('CRIMENET_FIELD_KEY=' + secrets.token_urlsafe(48))"
```

> Changing `CRIMENET_FIELD_KEY` later makes previously encrypted fields unreadable.
> Back it up before you rotate it.

---

## 3. Path A — single VM + Caddy (recommended)

Assumes Ubuntu 24.04 LTS, a domain you control, and `sudo`. Substitute your own hostname
for `crimenet.example.gov.in` everywhere.

### 3.1 Provision the server

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nodejs npm git curl debian-keyring debian-archive-keyring apt-transport-https

# Caddy (official repo) — provides automatic HTTPS
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy

# An unprivileged account to run the application
sudo useradd --system --create-home --shell /usr/sbin/nologin crimenet
```

Point an **A record** for `crimenet.example.gov.in` at this server's public IP now —
Caddy's certificate challenge fails without it.

### 3.2 Put the code in place

```bash
sudo mkdir -p /opt/crimenet && sudo chown crimenet:crimenet /opt/crimenet
# from your machine:  rsync -av --exclude frontend/node_modules --exclude frontend/dist \
#                     ./ root@SERVER:/opt/crimenet/
sudo -u crimenet git clone <your-repo-url> /opt/crimenet      # or rsync the tree

cd /opt/crimenet
sudo -u crimenet python3 -m venv venv
```

### 3.3 Configuration

```bash
sudo mkdir -p /etc/crimenet /var/lib/crimenet
sudo cp deploy/crimenet.env.example /etc/crimenet/crimenet.env
sudo chmod 600 /etc/crimenet/crimenet.env
sudo chown root:root /etc/crimenet/crimenet.env
sudo chown crimenet:crimenet /var/lib/crimenet
```

Edit `/etc/crimenet/crimenet.env` and set **at minimum**:

```ini
CRIMENET_ENVIRONMENT=production
CRIMENET_JWT_SECRET=<from section 2>
CRIMENET_FIELD_KEY=<from section 2>
```

The ledger/object-storage paths in that file already point at `/var/lib/crimenet`, which
is the state directory you must keep (and back up).

### 3.4 Build and start

```bash
cd /opt/crimenet
sudo bash deploy/update.sh                      # deps + spaCy model + build + restart + verify

sudo cp deploy/crimenet.service /etc/systemd/system/crimenet.service
sudo systemctl daemon-reload
sudo systemctl enable --now crimenet
sudo systemctl status crimenet --no-pager
```

### 3.5 TLS in front

```bash
sudo cp deploy/Caddyfile /etc/caddy/Caddyfile
sudo sed -i 's/CRIMENET_HOST/crimenet.example.gov.in/' /etc/caddy/Caddyfile
sudo systemctl reload caddy
journalctl -u caddy -n 20 --no-pager      # wait for "certificate obtained successfully"
```

### 3.6 Confirm it is live

```bash
curl -sI https://crimenet.example.gov.in/ | head -3
curl -s  https://crimenet.example.gov.in/api/health | python3 -m json.tool
curl -s  https://crimenet.example.gov.in/deployment | python3 -m json.tool
```

Then sign in with the synthetic credentials (`INV-2201` / `investigate123`) and walk the
workflow once.

**Every later release is two commands:**

```bash
cd /opt/crimenet && sudo -u crimenet git pull && sudo bash deploy/update.sh
```

`update.sh` refuses to print success unless the health check and the 33-stage acceptance
workflow both pass against the running service.

---

## 4. Path B — PaaS

### 4A. Single service (Railway, Render, Fly, Heroku-style)

One service builds the frontend and runs `serve_prod:app`, exactly like Path A. A ready
blueprint is in **`deploy/render.yaml`**:

```bash
cp deploy/render.yaml render.yaml && git add render.yaml && git commit -m "deploy" && git push
# Render dashboard → New → Blueprint → pick the repo
```

Set the same environment variables as in `deploy/crimenet.env.example`. Two things to get
right on any PaaS:

1. **Use the platform's `$PORT`**: `uvicorn serve_prod:app --host 0.0.0.0 --port $PORT --workers 1`.
2. **Attach a persistent volume** and point `CRIMENET_LEDGER_PATH`,
   `CRIMENET_LEDGER_WITNESS_PATH` and `CRIMENET_OBJECT_STORAGE` at it. On a free tier with
   an ephemeral filesystem the audit chain resets on every redeploy — acceptable for a
   judge demo if you say so, not acceptable otherwise.

The build step needs Node **and** Python in the same build image. Railway's Nixpacks
provides both. If a Python-only builder fails at `npm ci`, use 4B.

### 4B. Split host (no Node on the Python host) — the safest free-tier option

Build the frontend where Node always exists (Netlify / Vercel / Cloudflare Pages / Render
Static Site) and **proxy `/api` to the API service** so the browser still sees one origin.

Deploy the API first (Python service, start command as in 4A), then note its URL, e.g.
`https://crimenet-api.onrender.com`.

**Netlify** — create `frontend/public/_redirects`:

```
/api/*  https://crimenet-api.onrender.com/api/:splat  200
/*      /index.html                                    200
```

**Vercel** — `vercel.json` in the frontend root:

```json
{
  "rewrites": [
    { "source": "/api/:path*", "destination": "https://crimenet-api.onrender.com/api/:path*" },
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

**Render Static Site** — Settings → Redirects/Rewrites: source `/api/*`, destination
`https://crimenet-api.onrender.com/api/:splat`, action **Rewrite**.

Build settings for the static host: build command `npm run build`, publish directory
`dist`.

The `/api/*` rule must be a **rewrite/proxy (200), not a redirect (301/302)** — a redirect
sends the browser to the API host and breaks the same-origin rule the app depends on.
Because the proxy is server-side, CORS never comes into play.

---

## 5. Path C — containers, deliberately omitted

No `Dockerfile` is provided: the declared stack for this project excludes containers, so
adding one would contradict the architecture the rest of the work is verified against.
Both paths above deploy the same two trees without it. If you need an image later, the
build is exactly `pip install -r backend/requirements.txt && python -m spacy download
en_core_web_sm && cd frontend && npm ci && npm run build`, and the run command is
`uvicorn serve_prod:app --host 0.0.0.0 --port $PORT`.

---

## 6. Go-live hardening checklist

- [ ] `CRIMENET_ENVIRONMENT=production` **and** both secrets set from `secrets.token_urlsafe(48)` — the app refuses to boot otherwise, and it will also refuse if they are the published literals.
- [ ] `/etc/crimenet/crimenet.env` is `0600 root:root`; secrets are **not** in the repo, the image or the logs (`CRIMENET_LOG_DEMO_SECRETS` unset).
- [ ] HTTPS working, HSTS present, `http://` redirects to `https://`.
- [ ] `CRIMENET_LEDGER_PATH` / `CRIMENET_LEDGER_WITNESS_PATH` / `CRIMENET_OBJECT_STORAGE` on a persistent disk, included in your backup job.
- [ ] One worker. The login lockout (5 failures / 300 s → HTTP 429) is per-process, and the ledger is a single SQLite file. **Scale out only after** pointing `CRIMENET_POSTGRES_DSN` and `CRIMENET_REDIS_URL` at real services.
- [ ] Monitoring hits `/api/health` (unauthenticated, cheap) and alerts on non-200.
- [ ] Log retention and rotation configured (Caddy/nginx + journald).
- [ ] `/api/docs` exposure decided — useful for reviewers; restrict via the proxy (`location /api/docs { deny all; }`) if you do not want it public.
- [ ] Anyone with the URL can reach the login screen: confirm **the data is synthetic** (`SYNTHETIC DEMONSTRATION DATA` banner and the `X-CrimeNet-Classification` response header) and that no real case material has been loaded. Do not point this instance at real evidence without a legal/privacy review.
- [ ] Passwords: the four demo accounts are published in the README. On a real deployment, provision new users and remove/rotate the demo ones in `backend/app/database/seed.py` before exposure.

---

## 7. Verifying the deployment (what I actually ran here)

The production entrypoint was tested in this workspace before being handed over, on port
8080 with the real build:

| Check | Result |
|---|---|
| `GET /api/health` | `status OK`, version `1.0.0`, `SYNTHETIC DEMONSTRATION DATA` |
| Login + authenticated calls (`/api/auth/login` → `/api/cases` → `/api/graph`) | token issued, `3 cases` (Priya Raman, INVESTIGATOR), `24 nodes / 17 edges`; `/api/cases` without a token → **401** |
| Deep links `/login`, `/audit`, `/network`, `/evidence` | HTTP **200**, SPA shell served (no 404 on refresh) |
| Unknown API path `/api/does-not-exist` | **404 JSON** `{"detail":"No such analytical endpoint…","code":"NOT_FOUND"}` — never HTML |
| Missing asset `/assets/nope.js` | **404**, 41 bytes — never a silent index.html (which would surface as `Unexpected token '<'`) |
| Asset bytes served vs on disk | `index-Nzmnwzeg.js` 1 305 499 = 1 305 499 ✅, `index-BcQwu_Oh.css` 75 848 = 75 848 ✅ |
| Cache policy | `/assets/*` → `public, max-age=31536000, immutable`; SPA shell → `no-cache, no-store, must-revalidate`; `/api/*` → `no-store` |
| Gzip | `content-encoding: gzip` on the 1.3 MB bundle |
| Path traversal `/../backend/app/config.py` | **404** (cannot escape `dist/`) |
| `/api/docs` | HTTP 200 |
| **`bash backend/verify_workflow.sh http://127.0.0.1:8080`** | **33 passed, 0 failed** (all 15 stages, against the production entrypoint — not the dev server) |
| `python3 scripts/check_no_llm_in_path.py` | **PASS** — no generative model reachable from the evidence path |
| `npm run build` | exit 0, `index-BcQwu_Oh.css` 75.84 kB, `index-Nzmnwzeg.js` 1 305.49 kB (identical hashes to the recorded pre-deploy build) |

Reproduce after deploying (against your public URL):

```bash
HOST=https://crimenet.example.gov.in
curl -s $HOST/api/health | python3 -m json.tool
curl -s -o /dev/null -w 'deep link /audit -> %{http_code}\n' $HOST/audit
bash backend/verify_workflow.sh $HOST          # full 33-stage acceptance run
```

---

## 8. State, persistence and backups

| Path | Contents | If lost |
|---|---|---|
| `CRIMENET_LEDGER_PATH` (`ledger.db`, + `-wal`, `-shm`) | append-only hash-chained audit ledger | The chain cannot be rebuilt. Audit history is gone; `/api/audit` starts over |
| `CRIMENET_LEDGER_WITNESS_PATH` (`ledger_witness.db`) | independent witness copy used to detect ledger rewriting | Tamper evidence weakens to the ledger's own hashes |
| `CRIMENET_OBJECT_STORAGE` | write-once evidence blobs (SHA-256 addressed) | Registered evidence files become unreadable, though hashes/metadata remain |
| Everything else | synthetic seed data | Regenerated on next start |

Back up by copying the directory **while the service is stopped** (SQLite WAL), or use
`sqlite3 ledger.db ".backup '/backup/ledger-$(date +%F).db'"` live. Once real PostgreSQL /
Neo4j are configured, their dumps take over this role.

---

## 9. Known limits — state these honestly

- **Embedded profiles.** Without `CRIMENET_POSTGRES_DSN` / `CRIMENET_NEO4J_URI` /
  `CRIMENET_REDIS_URL` the app runs labelled embedded fallbacks
  (`EMBEDDED_RELATIONAL_FALLBACK`, `EMBEDDED_PROPERTY_GRAPH`, `EMBEDDED_TTL_CACHE`), which
  `/api/health` and `/deployment` report. The ledger is a local hash chain with a witness
  file — an abstraction of a permissioned ledger, **not** a production blockchain.
- **Single process.** Login lockout counters are in memory and the ledger is a single
  SQLite file, so keep `--workers 1` until real Redis/PostgreSQL are configured.
- **Synthetic data only.** The bundled dataset (5 cases, 42 entities, 56 relationships, 10
  evidence items, 63 transactions) is generated in code and labelled as such. Treat the
  running instance accordingly.
- **`npm run build` warns** that the JS bundle exceeds 500 kB (1.3 MB / 364 kB gzipped).
  That is the recorded, accepted state of this build — the warning is not an error.
- **Sessions end on restart** in the `demo` profile, by design: the signing key is random
  per process.

---

## 10. Rollback

```bash
# Path A
cd /opt/crimenet && sudo -u crimenet git checkout <previous-tag> && sudo bash deploy/update.sh
# PaaS: use the dashboard's "Rollback to this deploy" on the previous successful deploy
```

Roll the frontend and the API back together — the SPA is compiled with the API paths of
its release, and they ship from one origin.

---

## 11. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Login screen loads, every action says "Cannot reach the CrimeNet AI analytical services" | UI and API on different origins, so relative `/api` calls hit the static host | Serve both from one origin (Path A) or add the `/api/*` **rewrite** (4B) |
| `REFUSING TO START: CRIMENET_ENVIRONMENT=production but CRIMENET_JWT_SECRET … is not set` | Production profile without secrets | Set both secrets, or use `CRIMENET_ENVIRONMENT=demo` |
| `REFUSING TO START: no built SPA at …/frontend/dist` | Built SPA missing | `cd frontend && npm ci && npm run build`, or set `CRIMENET_DIST`, or `CRIMENET_BUILD_ON_BOOT=1` |
| Refreshing `/audit` gives 404 | SPA fallback missing (you are not using `serve_prod.py`, or the static host lacks the `/*` → `/index.html 200` rule) | Apply the rule from 4B, or run `serve_prod:app` |
| Page is blank, console shows `Unexpected token '<'` | A missing asset returned HTML | With `serve_prod.py` this cannot happen (`.js`/`.css` misses return 404); check the asset URL on a custom proxy config |
| `/api/health` says `NER backend: spaCy:blank(en) + rules` | spaCy model not installed | `python -m spacy download en_core_web_sm`, then restart |
| Everyone is logged out after a deploy | `demo` profile: random per-process signing key | Expected; set `CRIMENET_JWT_SECRET` to keep sessions across restarts |
| Audit records look "missing" after a redeploy | Ledger on an ephemeral filesystem | Move it to the persistent volume (section 4A / 6) |
| `429` on login | Rate limit: 5 failures per 300 s per officer ID | Wait `lockout_seconds_remaining`, or raise `CRIMENET_LOGIN_MAX_ATTEMPTS` |

---

## 13. Publishing this repository to GitHub

The tree is committed and ready (`main`, one commit, 253 files). Two routes, both from
your own machine so no credential is ever shared with anyone else.

### 13.1 From the git bundle (keeps the existing commit)

Download `crimenet-ai.bundle`, then:

```bash
git clone crimenet-ai.bundle crimenet-ai          # the "origin" is the bundle file
cd crimenet-ai
git remote set-url origin https://github.com/<you>/<repo>.git
git push -u origin main
```

### 13.2 From the zip (creates a fresh commit under your identity)

Download `crimenet-ai-repo.zip`, then:

```bash
unzip crimenet-ai-repo.zip -d crimenet-ai && cd crimenet-ai
git init -b main
git add -A
git -c user.name="Your Name" -c user.email="you@example.com" \
    commit -m "CrimeNet AI: evidence-driven investigative intelligence workbench"
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

Or with the GitHub CLI, both at once:

```bash
gh repo create crimenet-ai --private --source=. --remote=origin --push
```

In the repository, `bash scripts/push_to_github.sh <repo-url>` does the same thing and
re-runs the pre-push checks; with `GITHUB_TOKEN=...` it pushes directly (the token is used
once and never written to `.git/config`).

### Before you push — what is and is not included

Included: the whole application (`backend/`, `frontend/src`, configs), `datasets/`,
`tools/`, `scripts/`, `artifacts/` (acceptance-run logs), `deploy/`, and all documentation.

Excluded on purpose (`.gitignore`, verified with `git ls-files`):

| Excluded | Why |
|---|---|
| `node_modules/`, `frontend/dist/`, `*.tsbuildinfo` | Regenerated by `npm install` / `npm run build` |
| `backend/ledger.db*`, `backend/ledger_witness.db*` | Instance-specific audit state; regenerated at startup |
| `backend/object_storage/` | Evidence blobs re-created by `seed.py` on every start |
| `uploads/` | Local scratch folder (screenshots and other personal files) |
| `.env*` (except the `deploy/*.example` template), `*.pem`, `*.key` | Never commit secrets |

Two things to check before making a repository **public**: the four demo accounts in the
README are intentional and published on purpose, but re-read section 6 — a public URL means
anyone can reach the login screen, and this build ships synthetic data only.


| File | Purpose |
|---|---|
| `backend/serve_prod.py` | Production entrypoint: SPA + API on one origin, SPA fallback, cache policy, gzip, `/deployment` info |
| `deploy/crimenet.env.example` | Every environment variable, with persistent-state paths pre-filled
| `deploy/crimenet.service` | systemd unit (hardened, one worker, auto-restart) |
| `deploy/Caddyfile` | Reverse proxy with automatic HTTPS + HSTS |
| `deploy/nginx.conf` | nginx equivalent (if you already run nginx) |
| `deploy/update.sh` | Idempotent release step: deps → model → build → restart → verify |
| `deploy/render.yaml` | PaaS blueprint for a single-service deploy |

Nothing in `backend/app/**`, the API contracts, the routes or the frontend source changed
for deployment — `git diff` for this pass touches only the files above.
