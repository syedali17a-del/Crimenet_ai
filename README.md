# CrimeNet AI

**Evidence-Driven Criminal Network Reconstruction & Investigation Intelligence**
*Evidence → Relationships → Analysis → Validation*

> All data in this build is **SYNTHETIC DEMONSTRATION DATA**. The platform produces analytical leads,
> hypotheses and information gaps — never verdicts, guilt or enforcement recommendations.

## Quick start

```bash
# Backend — FastAPI on :8000  (docs at /api/docs)
cd backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend — Vite dev server on :5173 (proxies /api to the backend)
cd frontend && npm install && npm run dev
```

## Demo accounts

| User ID | Password | Role | Case access |
|---|---|---|---|
| `INV-2201` | `investigate123` | INVESTIGATOR | CASE-101, CASE-202, CASE-512 |
| `ANL-3310` | `analyze123` | ANALYST | CASE-101, CASE-202, CASE-305, CASE-407 |
| `SUP-1100` | `supervise123` | SUPERVISOR | all cases |
| `ADM-0001` | `administer123` | ADMIN | all cases + user management |

## Suggested demo path

1. **Dashboard** → *Run full case analysis* — watch the 6 agents execute a 12-task plan.
2. **Evidence** → open `EV-2042` → *Integrity check* → `INTEGRITY_MISMATCH` (tamper demo).
3. **Network** → *Run network analysis*, highlight the path `PER-001 → LOC-001 → PER-004`, click an edge to
   see the evidence behind the relationship.
4. **Cross-Case** → `CASE-101 ↔ CASE-202` at 97.0 HIGH → verify or reject with a rationale.
5. **Entities** → `Ravi Kumar ↔ R. Kumar` 95.0 HIGH → confirm or keep separate (never auto-merged).
6. **Hypotheses** → competing explanations, ranked, with the contradiction `CON-001` visible.
7. **Information Gaps** → `IG-001` known vs unknown → **Next-Best Action** → execute the top-ranked analysis.
8. **Audit** → audit trail, integrity register, ledger chain verification, human decisions.
9. Open `CASE-512` for the deliberate **INSUFFICIENT EVIDENCE** path.

## Synthetic dataset pack

Every dataset the platform uses is also exported as standalone, realistically-formatted
source files in [`datasets/`](./datasets/) — one folder per evidence type:

| Folder | Contents |
|---|---|
| `01_FIR` | FIRs in Form IF1 layout (TXT + PDF) |
| `02_POLICE_REPORT` | Case diary extracts (TXT + PDF) |
| `03_CDR_CALL_DETAIL_RECORDS` | LEA-format CDR dumps, cell-site master, s.94 BNSS requisition |
| `04_FINANCIAL_RECORDS` | Certified bank statements with running balances |
| `05_SURVEILLANCE_REPORTS` | Field observation log + ANPR camera log |
| `06_INTELLIGENCE_REPORTS` | 5×5×5-graded intelligence notes |
| `07_IMAGE_EVIDENCE` | CCTV/ANPR stills with camera OSD + EXIF-style metadata |
| `08_PDF_CASE_BUNDLES` | One printable PDF bundle per case |
| `09_CSV_STRUCTURED_DATASETS` | 16 machine-readable registers |
| `10_CHAIN_OF_CUSTODY_AND_CERTIFICATES` | Custody registers + s.63(4)(c) BSA certificates |

Start at [`datasets/00_START_HERE_DATASET_INDEX.md`](./datasets/00_START_HERE_DATASET_INDEX.md).
`datasets/DATASET_MANIFEST.csv` carries a SHA-256 for every file. The pack is generated
**from `backend/app/database/seed.py`** by `python3 -m tools.build_datasets`, so the
documents and the running application can never disagree.

## Deploying it live

The SPA calls the API with relative paths (`fetch('/api/cases')`), so in production the UI
and the API must be served from **one origin**. `backend/serve_prod.py` does exactly that:
`/api/*` → FastAPI, `/assets/*` → the fingerprinted build, everything else → the SPA with a
fallback so a hard refresh on `/audit` still works.

```bash
# production entrypoint (serves the built SPA + the API on one port)
cd frontend && npm install && npm run build && cd ..
cd backend && python -m uvicorn serve_prod:app --host 0.0.0.0 --port 8000
```

Full instructions — VM + Caddy auto-TLS (`deploy/Caddyfile`), systemd unit
(`deploy/crimenet.service`), one-command releases (`deploy/update.sh`), PaaS
(`deploy/render.yaml`), environment reference (`deploy/crimenet.env.example`), persistence,
backups and a go-live hardening checklist: **[`DEPLOY.md`](./DEPLOY.md)**.

## Repository layout

| Path | Contents |
|---|---|
| `backend/` | FastAPI application, agents, analytics, audit ledger, `serve_prod.py` entrypoint |
| `frontend/` | React 19 + TypeScript + Tailwind SPA (`src/`), build config |
| `deploy/` | Deployment kit: env template, systemd unit, Caddyfile, nginx.conf, release script, PaaS blueprint |
| `datasets/` | The synthetic dataset pack as standalone source files |
| `tools/` | Dataset-pack generators |
| `scripts/` | Verification and acceptance harnesses |
| `artifacts/` | Raw acceptance-run logs referenced by the documentation |
| `DEPLOY.md` · `RUN_IN_VSCODE.md` · `CRIMENET_AI_REPORT.md` | Deployment, local setup, full technical report |
| `PART_A_ACCEPTANCE.md` · `PART_B_ACCEPTANCE.md` · `BUGFIX_EVIDENCE.md` | Acceptance records: hardening proofs, design audit, the four UI-bug fixes |

Runtime state (`backend/ledger.db*`, `backend/object_storage/`, `frontend/dist/`,
`node_modules/`) is deliberately **not** tracked — see [`.gitignore`](./.gitignore).

## Stack

React 19 · TypeScript · Tailwind CSS v4 · Cytoscape.js · Leaflet · Vite —
Python 3.13 · FastAPI · Pydantic · spaCy · scikit-learn · pandas · NetworkX · RapidFuzz · PyJWT

Full documentation: [`CRIMENET_AI_REPORT.md`](./CRIMENET_AI_REPORT.md)
