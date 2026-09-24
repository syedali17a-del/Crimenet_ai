# CrimeNet AI — Codebase Inspection & Phased Implementation Plan

*Inspection performed on the running system (backend `:8000`, frontend `:5173`) plus a full
stage-by-stage execution of the pipeline via `verify_workflow.sh` — **33/33 checks passed**.*

---

## PART A — Inspection findings

### 1. Frontend framework and structure
| Item | Finding |
|---|---|
| Framework | React 19 + TypeScript 6, bundled by **Vite 8** (bundler only — no Next.js/Vue/Angular) |
| Styling | **Tailwind CSS v4** via `@tailwindcss/vite`, custom `@theme` palette (navy/brand/mist). No Bootstrap/MUI/AntD |
| Routing | `react-router-dom` v7 — 16 routes, protected wrapper + page-transition wrapper |
| Graph | **Cytoscape.js** driven imperatively through a ref (`components/graph/NetworkGraph.tsx`) |
| Maps | **Leaflet** + OSM raster tiles, imperative ref (`components/map/MapView.tsx`) |
| State | React Context (`state/AppContext.tsx`): session, cases, permissions, toasts. No Redux |
| Data access | `services/api.ts` (single fetch wrapper) + `hooks/useFetch.ts` (`useFetch`, `usePost`) |
| Structure | `pages/` (16), `components/{layout,shared,graph,map,agents,brand,system}`, `types/`, `hooks/`, `services/`, `state/` |
| Build | `tsc -b && vite build` — clean, 0 type errors |

### 2. Backend structure
FastAPI + Pydantic v2 on Python 3.13, 43 modules / ~6,000 LOC, served by Uvicorn.
`app/main.py` (app factory, CORS, security + timing middleware, error envelope, 8 routers) →
`api/` (auth, cases, evidence, analysis, entities, audit, security, intel) →
`agents/` (8 modules, 6 named agents) → `analytics/` (Isolation Forest, cross-case) →
`database/` (postgres, neo4j_graph, redis_cache, object_storage, seed) →
`security/` (crypto, jwt_handler, rbac, deps) → `audit/` (audit_log, ledger) →
`models/domain.py`, `schemas/api.py`, `config.py`.

### 3. Current database implementation
| Store | Spec target | Current profile | Behaviour |
|---|---|---|---|
| Relational | PostgreSQL | `EMBEDDED_RELATIONAL_FALLBACK` | 14 tables; connects to real PostgreSQL when `CRIMENET_POSTGRES_DSN` is set |
| Graph | Neo4j + GDS | `EMBEDDED_PROPERTY_GRAPH` (NetworkX) | 44 nodes / 56 relationships; switches to Neo4j when `CRIMENET_NEO4J_URI` is set; `gds_available:false` here |
| Cache | Redis | `EMBEDDED_TTL_CACHE` | Real Redis when `CRIMENET_REDIS_URL` is set |
| Objects | Object storage | `FILESYSTEM_BACKED_OBJECT_STORAGE` | Write-once evidence blobs under `backend/object_storage/` |
| Ledger | Permissioned ledger | `PERMISSIONED_LEDGER_ABSTRACTION` | Hash chain, 24 blocks, `verify_chain()` re-hashes every block |
No real DB servers exist in this sandbox — every profile is labelled truthfully on the Security page. **In-memory stores reset on backend restart.**

### 4. Existing components
`layout/AppLayout` (sidebar + topbar + global search + notifications + profile),
`shared/ui.tsx` (Card, Button, Badge, StatTile, Modal, Field, inputs, Skeleton/LoadingBlock, EmptyState,
ErrorState, **InsufficientEvidence**, SignalRow, Hash, ClassificationTag, Principle),
`shared/Icon.tsx` (43 inline SVG icons), `graph/NetworkGraph`, `graph/EntityPanel` (+`RelationshipPanel`),
`map/MapView`, `agents/AgentRunModal` (multi-agent progress).
**New this pass:** `brand/Brand.tsx` (BrandMark/Wordmark/Tagline), `system/BootSplash.tsx`.

### 5. Existing APIs
68 routes / 72 operations, all under `/api`, OpenAPI at `/api/docs`. Groups: auth (4), cases (9),
evidence (11), analysis (15), entities/verification (11), intel (7), audit/integrity/ledger (5),
security (7), ops (2). Error envelope `{detail, code}`; headers `X-CrimeNet-Classification`,
`X-CrimeNet-TLS`, `X-Response-Time-ms`.

### 6. Existing graph implementation
Property graph with 9 node types and 9 relationship types. **Invariant: no relationship exists
without `evidence_id` + `source_document` + `timestamp` + `support_level` + `verification_status`.**
Projection for analytics deliberately excludes `CASE` nodes and hidden `PART_OF` edges (fixed earlier —
otherwise case nodes dominated centrality). Algorithms: degree/betweenness centrality, Louvain
(modularity 0.63), shortest path, density/components — NetworkX today, Neo4j GDS call path present.

### 7. Existing authentication
JWT HS256 (PyJWT), 480-min sessions, PBKDF2-HMAC-SHA256 (120k rounds, per-user salt),
18 permissions × 4 roles, case-level authorization on every case-scoped route, `Principal` dependency
guard. Verified live: bad password → 401; investigator → 403 on `CASE-305`; supervisor → 403 on
`/api/security/users`.

### 8. Existing synthetic data
5 cases · 15 persons · 5 vehicles · 6 locations · 4 phones · 3 accounts · 2 orgs · 2 devices ·
56 relationships · 10 evidence items · 17 events · 63 transactions · 1 contradiction (`CON-001`) ·
1 tamper case (`EV-2042`) · 1 evidence-poor case (`CASE-512`). Every record carries
`classification: "SYNTHETIC DEMONSTRATION DATA"`.

### 9. What is already functional (verified live, 33/33)
Login/RBAC/case scoping · case CRUD · evidence registration + upload + SHA-256 · document
intelligence (spaCy + rules, 11 entities from a fresh document) · entity resolution (95.0 HIGH, no
auto-merge) · cross-case correlation (97.0 HIGH) · knowledge graph (44/37 in scope) · centrality +
communities + shortest path · timeline + spikes + convergence + Isolation Forest anomaly ·
corroboration incl. CONTRADICTORY EVIDENCE and CASE-512 INSUFFICIENT EVIDENCE · 5 information gaps ·
next-best action ranking (analytical only) · human verify/reject for relationships, entities,
cross-case links, identity matches, hypotheses, convergences · integrity sweep incl. the
`EV-2042` mismatch · append-only audit + intact ledger chain · 6-agent manager plans.

### 10. What was missing / fixed in this pass
| Gap | Resolution |
|---|---|
| **Sign-in appeared to fail** — services were down after a sandbox reset, so `fetch` failed and the page stayed put | Services restarted; `start.sh` added (auto-installs deps + starts both); login now shows a live **service-status pill** and an explicit "services offline · Retry" state instead of silently failing |
| Stale cached profile with no token could render the shell then bounce to login | `AppContext` now clears any cached profile when no token exists |
| No app-open experience | **`BootSplash`** — centred CrimeNet AI mark, animated ring/wordmark, and four **real** start-up steps (client → `/api/health` → `/api/meta` → session), with a blocking, actionable error if the backend is unreachable |
| Entry screen felt plain | Login rebuilt: deep-navy intelligence panel (animated grid/glow, pillars, pipeline strip), glass sign-in card, password reveal, Caps-Lock hint, staged sign-in progress, richer role cards |
| Pipeline was spread across 15 pages with no single end-to-end view | New **`/workflow`** page: the 15 stages as an executable checklist against the real services |
| No repeatable proof of the pipeline | `verify_workflow.sh` — 33 assertions across all 15 stages |

---

## PART B — Phased implementation plan

**Phase 0 — Runtime reliability (DONE)**
`start.sh` restores dependencies and starts both services; boot handshake surfaces backend state;
login degrades honestly when the API is down.

**Phase 1 — Entry experience (DONE)**
Boot splash → premium entry screen → authenticated shell. Session-scoped so it plays on app open,
not on every route change. Respects `prefers-reduced-motion`.

**Phase 2 — End-to-end workflow surface (DONE)**
`/workflow` executes and reports all 15 stages with real payloads, honest `INSUFFICIENT EVIDENCE`
and `NOT AUTHORIZED` outcomes, and a deep link into the working page for each stage.

**Phase 3 — Stage-level depth (next)**
Per-stage refinements that add analyst value without changing the stack:
1. Evidence: side-by-side document ↔ extracted-entity highlighting.
2. Resolution: merge-preview diff (what a confirmed identity would change in the graph) — still human-decided.
3. Graph: saved views/filters per case; edge bundling above ~150 edges.
4. Timeline: brush-to-zoom range selection feeding all other pages.
5. Hypotheses: side-by-side hypothesis comparison with evidence deltas.

**Phase 4 — Assurance depth**
Case brief export (print/PDF via the browser), audit filter presets, ledger block explorer with
per-evidence anchoring history, verification queue with supervisor sampling.

**Phase 5 — Production hardening (documented, out of sandbox scope)**
Real PostgreSQL/Neo4j+GDS/Redis/S3 via the existing env-var switches, KMS-backed field encryption,
SSO+MFA, async task queue for long analyses, route-level code splitting, self-hosted map tiles.

---

## How to run it again after a sandbox reset

```bash
bash /home/user/start.sh          # installs missing deps, starts API :8000 + UI :5173
bash /home/user/verify_workflow.sh # 33 assertions across the 15 pipeline stages
```
