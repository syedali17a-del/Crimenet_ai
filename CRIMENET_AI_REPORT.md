# CrimeNet AI — Delivery Report

**Evidence-Driven Criminal Network Reconstruction & Investigation Intelligence**
*Evidence → Relationships → Analysis → Validation*

> **All data in this build is labelled `SYNTHETIC DEMONSTRATION DATA`.** No real case, person, vehicle, phone,
> account or location is represented. The platform is an analytical decision-support system: it produces
> leads, hypotheses and gaps — never verdicts, guilt, risk scores or enforcement recommendations.

---

## 1. What is implemented

A complete, running two-tier application — **not** a mockup and **not** a chatbot.

| Capability | Status |
|---|---|
| JWT login, 4 seeded roles, session restore, server-side RBAC + case-level scoping | ✔ working |
| 15 pages, all wired to live APIs, all major buttons perform real backend actions | ✔ working |
| Evidence registry: register (sample / pasted text / file upload ≤5 MB), SHA-256 at intake, object storage, provenance chain | ✔ working |
| Document intelligence pipeline `UPLOADED → PROCESSING → EXTRACTED → ENTITIES_FOUND → RELATIONSHIPS_CANDIDATE` | ✔ working |
| NER (spaCy `en_core_web_sm` + rule layer for registration plates, phones, accounts, IMEI, case IDs, dates) | ✔ working |
| Entity resolution (normalize → tokenize → RapidFuzz → multi-attribute scoring), **no auto-merge** | ✔ working |
| Evidence-backed network reconstruction (Cytoscape.js graph, every edge carries evidence ID + support + verification state) | ✔ working |
| Network analytics: degree & betweenness centrality, Louvain communities, density, components, shortest path | ✔ working |
| Temporal analytics: chronology, daily activity + spikes, repeated activity, network evolution, 30-min convergence windows | ✔ working |
| Behavioural anomaly detection (scikit-learn Isolation Forest over transaction features) | ✔ working |
| Cross-case correlation (shared hard identifiers + fuzzy names + location + temporal proximity) | ✔ working |
| Corroboration engine → 4 lead statuses incl. **INSUFFICIENT EVIDENCE** and **CONTRADICTORY EVIDENCE** | ✔ working |
| Competing hypothesis generation + evidence-based ranking (always includes innocent/coincidental alternatives) | ✔ working |
| Known vs unknown information-gap analysis with named missing evidence | ✔ working |
| Next-best-action ranking by expected information value (analytical actions only), each executable from the UI | ✔ working |
| Human validation everywhere: verify / reject / annotate with rationale; rejections never delete the finding | ✔ working |
| Append-only SHA-256 audit trail + CSV export | ✔ working |
| Hash-chained permissioned-ledger abstraction for evidence notarisation + chain verification | ✔ working |
| Evidence integrity checks + full sweep, tamper case demonstrated (`EV-2042` → `INTEGRITY_MISMATCH`) | ✔ working |
| 6-agent Manager orchestration with a visible multi-agent progress modal (12-task plan) | ✔ working |
| Map intelligence (Leaflet + OSM tiles, density circles, case-link polylines, convergence markers) | ✔ working |
| Security posture page: auth, RBAC matrix, agent least-privilege, backend profiles, user management | ✔ working |

**Size:** backend ≈ 5,970 LOC Python across 43 modules; frontend ≈ 6,020 LOC TypeScript/TSX across 28 modules.

---

## 2. Frontend structure (`/home/user/frontend`)

React 19 + TypeScript + Vite + Tailwind CSS v4 + Cytoscape.js + Leaflet. No UI kit, no CSS framework other than
Tailwind, no React wrappers around Cytoscape/Leaflet (both are driven imperatively through refs).

```
src/
  main.tsx                     React root
  App.tsx                      Route table (15 routes) + page-transition wrapper + protected routes
  index.css                    Tailwind v4 theme: white/blue palette, .glass, .neu, focus ring, transitions
  types/index.ts               Shared API types
  services/api.ts              fetch wrapper: bearer token, error envelope, 401 handling, upload helper
  state/AppContext.tsx         Auth/session, case list, permission helper can(), toast notifications
  hooks/useFetch.ts            useFetch<T>() and usePost<T>() with loading/error/reload/setData
  components/
    layout/AppLayout.tsx       Sidebar (4 nav groups, permission-filtered), top bar, global search, toasts
    shared/Icon.tsx            43 inline SVG icons (no icon dependency, previews offline-safe)
    shared/ui.tsx              Card, Button, Badge, StatTile, Modal, Field, inputs, LoadingBlock, Skeleton,
                               EmptyState, ErrorState, InsufficientEvidence, SignalRow, Hash, Principle…
    agents/AgentRunModal.tsx   Multi-agent run: plan fetch → per-task progress → agent result summary
    graph/NetworkGraph.tsx     Cytoscape.js canvas, styles by entity type, support-coloured edges,
                               dashed = unverified, path highlight, community colouring, fit/reset
    graph/EntityPanel.tsx      Entity profile drawer + RelationshipPanel (evidence behind an edge)
    map/MapView.tsx            Leaflet map, OSM tiles, density circles, case polylines, popups
  pages/                       Login, Dashboard, Cases, CaseDetails, Evidence, NetworkIntelligence,
                               Timeline, MapIntelligence, CrossCase, EntityResolution, Hypotheses,
                               InformationGaps, NextBestAction, Audit, Security
```

**Design system.** Premium government-grade white + blue: `#f6f9ff` canvas, navy `#102a52` text, brand blue
`#2563eb`. Selective **glassmorphism** on panels/cards/modals (`backdrop-blur`, translucent white, 1px blue-tinted
border) and selective **neumorphism** on buttons/toggles (soft dual shadow, pressed state). Subtle page
transitions (fade + 6px rise), skeleton loaders, and a multi-agent progress modal instead of a spinner for long
analyses. Fully responsive: 16:9 desktop primary, collapsing sidebar, stacked grids on tablet/mobile.

**Route table:** `/login` `/dashboard` `/cases` `/cases/:caseId` `/evidence` `/network` `/timeline` `/map`
`/cross-case` `/entities` `/hypotheses` `/information-gaps` `/next-best-action` `/audit` `/security`.

---

## 3. Backend structure (`/home/user/backend`)

Python 3.13 + FastAPI + Pydantic v2, served by Uvicorn.

```
app/
  main.py                  App factory, CORS, security headers + timing middleware, error envelope, 8 routers
  config.py                Constants, JWT/TLS settings, DSN env vars, thresholds, DATA_CLASSIFICATION
  models/domain.py         Pydantic domain models (Case, Evidence, Entity, Relationship, Event, …)
  schemas/api.py           Request/response schemas for every endpoint
  database/
    postgres.py            RelationalStore — 14 tables (users, cases, permissions, tasks, audit, evidence,
                           annotations, verifications, transactions, events, plans, contradictions,
                           findings, notifications). Connects to PostgreSQL if CRIMENET_POSTGRES_DSN is set,
                           otherwise a clearly labelled embedded relational fallback.
    neo4j_graph.py         GraphStore — property graph over NetworkX MultiDiGraph; uses Neo4j + GDS when
                           CRIMENET_NEO4J_URI is set, otherwise the labelled embedded property graph.
    redis_cache.py         CacheStore — Redis when CRIMENET_REDIS_URL is set, else embedded TTL cache.
    object_storage.py      Write-once evidence blob store (filesystem volume in this profile).
    seed.py                Synthetic dataset loader.
  security/
    crypto.py              PBKDF2-HMAC-SHA256 (120k rounds, per-user salt) + authenticated field encryption
    jwt_handler.py         HS256 JWT issue/verify, 480-min sessions
    rbac.py                18 permissions × 4 roles matrix
    deps.py                Principal, require_permission(), authorize_case(), authorized_case_ids()
  audit/
    audit_log.py           Append-only audit records, SHA-256 per record
    ledger.py              Hash-chained permissioned-ledger abstraction + verify_chain()
  agents/                  manager, document_agent, entity_agent, resolution_agent, evidence_agent,
                           network_agent, temporal_agent, reasoning_agent
  analytics/               anomaly.py (Isolation Forest), cross_case.py (correlation)
  api/                     auth.py, cases.py, evidence.py, analysis.py, entities.py, audit.py,
                           security.py, intel.py
```

Every request passes a dependency guard that resolves the JWT → `Principal` → permission check → case-scope
check. Responses carry `X-CrimeNet-Classification`, `X-CrimeNet-TLS`, `X-Response-Time-ms`.

---

## 4. The six agents

Not all agents are LLM agents — most are deterministic, explainable analytical services. That is deliberate:
evidence work must be reproducible.

| Agent | Kind | Responsibility |
|---|---|---|
| `MANAGER_AGENT` | Orchestration service | Builds a task plan for an objective (`FULL_CASE_ANALYSIS` = 12 tasks, `CROSS_CASE_LINK` = 8, `EVIDENCE_INTEGRITY_SWEEP`), resolves dependencies, executes tasks, aggregates a conclusion, writes plan + tasks + audit records. Never decides truth. |
| `DOCUMENT_INTELLIGENCE_AGENT` | NLP pipeline | Ingests documents, normalises text, runs spaCy NER + regex rule layer, extracts structured fields, records what it could **not** read (declares OCR unavailability instead of pretending). |
| `ENTITY_RESOLUTION_AGENT` | Deterministic matcher | Normalisation → token comparison → RapidFuzz fuzzy similarity → multi-attribute scoring → candidate match with signals, contradictions and support level. Auto-merge is disabled by policy. |
| `EVIDENCE_PROVENANCE_AGENT` | Integrity service | SHA-256 at intake and on demand, provenance chain per object, ledger notarisation, registry summary, mismatch flagging without touching the original object. |
| `NETWORK_TEMPORAL_AGENT` | Graph/temporal analytics | Projects the evidence graph, centrality, communities, shortest path, chronology, spikes, repeated activity, spatio-temporal convergence. |
| `INVESTIGATION_REASONING_AGENT` | Reasoning service | Corroboration across independent methods, competing hypothesis generation and ranking, known/unknown gap analysis, next-best-action ranking by information value. |

**Agent prohibitions (enforced and displayed on the Security page):** agents cannot change permissions, cannot
merge identities, cannot delete evidence or audit records, cannot assert guilt, cannot recommend operational
or enforcement action, cannot access cases outside the caller's authorisation.

---

## 5. Algorithms

1. **NER** — spaCy `en_core_web_sm` for PERSON/ORG/GPE/DATE + a regex rule layer for Indian registration plates
   (`TN01AB1234`), phone numbers, bank accounts, IMEI/device IDs, case IDs and dates.
2. **Entity resolution** — normalise (case, punctuation, honorifics) → tokenize → `RapidFuzz`
   (`ratio`, `partial_ratio`, `token_sort_ratio`, `token_set_ratio`, `WRatio`) → initial-compatibility and
   surname boosts → weighted multi-attribute score (name 50 %, shared vehicle 22 %, phone/account 12 %,
   location 10 %, temporal proximity 8 %, −15 penalty for same-hour different-location conflict) →
   HIGH ≥ 85 & ≥3 supporting signals, MEDIUM ≥ 65 & ≥2, LOW ≥ 50, else INSUFFICIENT.
   *Demo output: `Ravi Kumar ↔ R. Kumar` 95.0 HIGH; `Ravi Kumar ↔ Ravi K.` 69.0 MEDIUM.*
3. **Isolation Forest** (scikit-learn, `contamination=0.08`) over per-account/per-hour transaction features,
   gated by deviation from the account's own baseline. *Demo: `ACC-001`, 50 transactions in the 14:00 hour of
   2025-08-22 against a 3.2/day baseline.*
4. **Degree centrality** — most connected entity (`PER-001`, 0.1429).
5. **Betweenness centrality** — bridge nodes (`PER-004`, 0.101) described as *"structurally important"*, never
   as a leader or ringleader.
6. **Community detection** — Louvain modularity (NetworkX), modularity 0.6327, 7 clusters.
7. **Shortest path** — evidence-backed path between two entities (`PER-001 → LOC-001 → PER-004`), each hop
   annotated with the relationship type and the evidence ID that supports it.
8. **Temporal analysis** — chronology, daily activity histogram, baseline + spike detection, repeated
   entity/location activity, network evolution.
9. **Spatio-temporal convergence** — entities recorded at the same location inside a 30-minute window, always
   returned with the disclaimer that co-location does not establish that individuals met.
10. **Cross-case correlation** — shared hard identifiers (vehicle/phone/account) + fuzzy name match + shared
    locations + temporal proximity; temporal-only coincidences are dropped. *Demo: `XC-101-202` strength 97.0 HIGH.*
11. **Corroboration** — counts independent analytical methods and independent evidence sources supporting a
    lead, then assigns `CORROBORATED ANALYTICAL LEAD` / `PARTIALLY CORROBORATED — FURTHER EVIDENCE REQUIRED` /
    `CONTRADICTORY EVIDENCE` / `INSUFFICIENT EVIDENCE`.
12. **Hypothesis ranking** — support score from independent sources, repeated patterns, structural consistency
    and contradiction penalties. Competing hypotheses (including the innocent/coincidental explanation) are
    always presented together.
13. **Information-gap analysis** — for each lead: what is known (with evidence IDs), what is unknown, the gap
    type (`IDENTITY_CONFIRMATION`, `CONTRADICTION`, `BEHAVIOURAL_BASELINE`, `FINANCIAL_CONTEXT`,
    `INDEPENDENT_CORROBORATION`, …) and severity.
14. **Information-value ranking** — each catalogue action scores by how many open gaps it closes and how
    decisive it would be; the top action becomes the recommended next analytical step.

---

## 6. Data model

**Relational (PostgreSQL profile)** — `users`, `cases`, `permissions`, `tasks`, `audit`, `evidence`,
`annotations`, `verifications`, `transactions`, `events`, `plans`, `contradictions`, `findings`,
`notifications`.

**Property graph (Neo4j profile)** — nodes `PERSON, ALIAS, VEHICLE, PHONE, ACCOUNT, LOCATION, ORGANIZATION,
DEVICE, CASE`; relationships `ASSOCIATED_WITH, USED, LOCATED_AT, CONNECTED_TO, PART_OF, MENTIONED_IN,
TRANSACTED_WITH, OBSERVED_AT, RELATED_TO`. Every relationship stores `evidence_id`, `source_document`,
`timestamp`, `support_level`, `verification_status`, `case_id`. **A relationship cannot exist without an
evidence reference** — that invariant is what makes the graph defensible.

**Object storage** — write-once evidence blobs keyed by evidence ID with the SHA-256 registered at intake.

**Ledger** — blocks of `{index, timestamp, event_type, evidence_id, case_id, payload_hash, previous_hash,
block_hash, integrity_status, recorded_by}`. Content, personal data and case narrative are *never* written to
the ledger — only hashes.

---

## 7. API surface (68 routes / 72 operations, all under `/api`, docs at `/api/docs`)

**Auth** `POST /auth/login` · `POST /auth/logout` · `GET /auth/me` · `GET /auth/roles`
**Cases** `GET|POST /cases` · `GET|PATCH /cases/{id}` · `/cases/{id}/entities|network|timeline|hypotheses|information-gaps|next-best-action`
**Evidence** `GET|POST /evidence` · `POST /evidence/upload` · `GET /evidence/{id}` · `POST /evidence/{id}/process|integrity-check|verify|reject|annotate` · `GET /evidence/{id}/annotations` · `GET /evidence/samples/catalogue`
**Analysis** `POST /analysis/network|temporal|anomaly|entity-resolution|corroboration|cross-case|convergence|shortest-path|hypotheses|information-gaps|next-best-action` · `POST /analysis/manager/plan|execute` · `GET /analysis/manager/objectives|plan/{id}`
**Entities & human validation** `GET /entities` · `GET /entities/{id}` · `POST /entities/{id}/verify|reject|annotate` · `GET /relationships/{id}` · `POST /relationships/{id}/verify|reject` · `POST /findings/{id}/verify|reject|annotate` · `GET /verifications`
**Intelligence** `GET /dashboard|graph|timeline|map|search|insights|contradictions`
**Assurance** `GET /audit` · `GET /ledger` · `POST /ledger/verify` · `GET /integrity/overview` · `POST /integrity/run-all`
**Security** `GET /security/status|rbac|agents` · `GET|POST /security/users` · `PATCH /security/users/{id}`
**Ops** `GET /health` · `GET /meta`

Error envelope: `{ "detail": "...", "code": "..." }`. Verification records are keyed `EVIDENCE::{id}`,
`IDENTITY::{left}::{right}`, `CROSS_CASE_LINK`, `HYPOTHESIS`, `CONVERGENCE`.

---

## 8. Security implementation

* **Authentication** — JWT (PyJWT, HS256), 480-minute sessions, bearer token, 401 auto-logout on the client.
* **Password storage** — PBKDF2-HMAC-SHA256, 120,000 rounds, per-user salt. No plaintext, ever.
* **RBAC** — 18 permissions across `INVESTIGATOR` (11), `ANALYST` (10), `SUPERVISOR` (16), `ADMIN` (18),
  enforced by a FastAPI dependency on **every** endpoint. The frontend only *hides* what the backend *refuses*:
  an analyst calling `/api/security/users` gets `403 FORBIDDEN` regardless of the UI.
* **Case-level authorisation** — every case-scoped route intersects the request scope with the principal's
  authorised case list; an investigator scoped to `CASE-101,202,512` receives 403 on `CASE-305`.
* **Field encryption** — phone/account identifiers stored with authenticated field encryption (development
  HMAC-keystream envelope; a KMS-backed AES-GCM provider is the production swap-in).
* **Evidence integrity** — SHA-256 at intake, re-verified on demand and in sweeps; mismatch preserves the
  registered hash and flags the object. Original evidence is never modified or deleted by the application.
* **Audit** — append-only, one SHA-256 per record, exportable to CSV by `audit:export` holders.
* **Ledger** — hash-chained notarisation with `verify_chain()` re-hashing every block; labelled
  `PERMISSIONED_LEDGER_ABSTRACTION (development notary profile — not a production blockchain network)`.
* **Transport** — TLS terminated at the ingress gateway in this environment; the app reports the real state
  rather than claiming end-to-end TLS it does not terminate itself.
* **Agent least privilege** — each agent has an explicit permit/forbid list shown on the Security page.

---

## 9. Synthetic demonstration scenario

**Dataset:** 5 cases · 42 graph nodes (15 persons, 5 vehicles, 6 locations, 4 phones, 3 accounts, 2 orgs,
2 devices, 5 case nodes) · 56 relationships · 10 evidence items · 17 events · 63 transactions · 1 recorded
contradiction. Every record carries `classification: "SYNTHETIC DEMONSTRATION DATA"`.

**The core walkthrough**

1. `CASE-101` *Chennai Vehicle Theft Network* — FIR `EV-1024` names **Ravi Kumar** with vehicle **TN01AB1234**
   at **Chennai Central**, 10 Aug 2025.
2. `CASE-202` *Coordinated Property Crime* — police report `EV-2041` records **R. Kumar** with the **same
   vehicle** at the same location, 18 Aug 2025, alongside **Arun Selvam** and witness **Meena Raghavan**
   inside a 13-minute window → **potential convergence event** (with the "co-location ≠ meeting" disclaimer).
3. `CASE-305` *Port Area Financial Movement* — intelligence report `EV-3071` records **Ravi K.** with the same
   vehicle at **Chennai Port**, 25 Aug 2025; financial record `EV-3070` drives the **Isolation Forest anomaly**
   on `ACC-001`.
4. **Cross-case correlation** links `CASE-101 ↔ CASE-202` at strength **97.0 HIGH** on the shared vehicle,
   shared phone, shared location, fuzzy name match and temporal proximity — presented as a
   *candidate association requiring verification*.
5. **Entity resolution** proposes `Ravi Kumar ↔ R. Kumar` at **95.0 HIGH** and `Ravi Kumar ↔ Ravi K.` at
   **69.0 MEDIUM** — both awaiting a human decision; nothing is merged.
6. **Contradiction `CON-001`** — `EV-2043` places Ravi Kumar in **Madurai** at 10:00 on 18 Aug while `EV-2041`
   places him at Chennai Central. The corroboration engine therefore returns **CONTRADICTORY EVIDENCE**, and
   gap **IG-001** (HIGH severity) states exactly what would resolve it.
7. **Tamper demonstration** — `EV-2042` fails its integrity check with `INTEGRITY_MISMATCH`; the registered
   hash is preserved and the ledger records the failed check.
8. **Evidence-poor path** — `CASE-512` returns **INSUFFICIENT EVIDENCE** with the missing evidence named,
   rather than an invented conclusion.
9. **Next best action** — `ACT-VEHICLE-XREF` "Cross-reference authorized vehicle records" ranks first
   (information value 0.92, closes 2 open gaps) and can be executed from the UI, which calls the real
   analytical endpoint and writes an audit record.

**Demo accounts**

| User ID | Password | Role | Case access |
|---|---|---|---|
| `INV-2201` | `investigate123` | INVESTIGATOR | CASE-101, CASE-202, CASE-512 |
| `ANL-3310` | `analyze123` | ANALYST | CASE-101, CASE-202, CASE-305, CASE-407 |
| `SUP-1100` | `supervise123` | SUPERVISOR | all |
| `ADM-0001` | `administer123` | ADMIN | all |

*Try the RBAC proof:* sign in as `ANL-3310`, open Security → the user-management tab is absent, and a direct
call to `/api/security/users` returns 403. Sign in as `INV-2201` and request `CASE-305` → 403 from the server.

---

## 10. How to run

Both services are already running in this workspace (frontend `:5173`, backend `:8000`).

```bash
# 1) Backend  (Python 3.13)
cd /home/user/backend
pip install fastapi uvicorn pydantic rapidfuzz PyJWT python-multipart redis neo4j \
            spacy scikit-learn pandas networkx numpy
python -m spacy download en_core_web_sm
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
#    API docs: http://localhost:8000/api/docs

# 2) Frontend  (Node 20)
cd /home/user/frontend
npm install
npm run dev          # http://localhost:5173  (proxies /api → 127.0.0.1:8000)
npm run build        # production bundle in dist/
```

**Optional real backing services** (the app auto-detects them and switches profile; otherwise it runs the
clearly labelled embedded fallbacks):

```bash
export CRIMENET_POSTGRES_DSN="postgresql://user:pass@localhost:5432/crimenet"
export CRIMENET_NEO4J_URI="bolt://localhost:7687"      # + CRIMENET_NEO4J_USER / _PASSWORD
export CRIMENET_REDIS_URL="redis://localhost:6379/0"
export CRIMENET_OBJECT_STORAGE="/var/lib/crimenet/objects"
export CRIMENET_JWT_SECRET="…"   export FIELD_ENCRYPTION_KEY="…"
```

---

## 11. Known limitations (honest list)

1. **No PostgreSQL / Neo4j / Redis server exists in this sandbox.** The adapters attempt real connections via
   the env vars above and otherwise run embedded equivalents that are labelled on the Security page
   (`EMBEDDED_RELATIONAL_FALLBACK`, `EMBEDDED_PROPERTY_GRAPH`, `EMBEDDED_TTL_CACHE`). Graph algorithms run on
   **NetworkX**, not Neo4j GDS; the GDS call path exists but reports `gds_available: false` here.
2. **Embedded stores are in-memory** — restarting the backend reloads the synthetic seed and clears runtime
   decisions. With a real PostgreSQL DSN the same code path persists.
3. **No OCR backend.** Image/PDF evidence is registered, hashed and marked as awaiting an OCR-capable
   deployment. The platform explicitly refuses to claim extraction it did not perform.
4. **No Transformers model weights** (2 GB RAM sandbox). NER runs on spaCy + the rule layer; the
   token-classification path is wired but reports "not loaded".
5. **The ledger is an abstraction**, not a distributed blockchain: a single-process hash chain with a named
   authority set, labelled as such everywhere it appears.
6. **TLS is terminated upstream** in this environment; the app reports the true state instead of asserting
   end-to-end TLS.
7. **Field encryption uses a development HMAC-keystream envelope**, not a KMS-backed AES-GCM provider.
8. Single frontend bundle (~1 MB, 306 kB gzipped) — no route-level code splitting yet.
9. Map tiles are fetched from `tile.openstreetmap.org`; in the sandboxed in-app file preview (no network) the
   basemap will not render, though it renders normally in a browser.
10. Realtime updates are request-driven (reload buttons and post-action refresh), not WebSocket-pushed.

---

## 12. Production gaps (what a real deployment must add)

| Area | Required before real casework |
|---|---|
| **Data stores** | Managed PostgreSQL (HA + PITR), Neo4j with GDS licence, Redis, S3/MinIO with object-lock (WORM) for evidence. |
| **Key management** | KMS/HSM-backed AES-GCM field encryption, JWT signing keys with rotation, per-tenant key separation. |
| **Identity** | Enterprise SSO (SAML/OIDC), MFA, device binding, short-lived tokens with refresh + revocation lists, session anomaly detection. |
| **Ledger** | A genuine permissioned ledger (e.g. Hyperledger Fabric / QLDB) with an independent authority set and external anchoring — or a notary service with third-party timestamping. |
| **ML lifecycle** | Model registry, versioned NER/ER models, drift monitoring, human-labelled evaluation sets, per-model bias and error-rate reporting, published precision/recall for entity resolution. |
| **OCR / multimedia** | Production OCR (Tesseract/Textract), speech-to-text, image forensics — each recording tool, version and confidence in provenance. |
| **Legal & governance** | Lawful-basis recording per evidence item, retention/deletion schedules, disclosure export packs, jurisdiction rules, DPIA, independent oversight, appeal path for affected persons. |
| **Assurance** | Immutable off-box audit sink (SIEM), tamper-evident log shipping, pen-test, threat model, dependency SBOM, secrets scanning in CI. |
| **Scale & ops** | Async task queue for long analyses, pagination/streaming for large graphs, graph sampling above ~10k nodes, observability (traces/metrics/alerts), backup/restore drills. |
| **Frontend hardening** | Route-level code splitting, self-hosted map tiles, offline-safe assets, WCAG 2.2 AA audit, i18n (Tamil/English), print/PDF case briefs. |
| **Human factors** | Analyst training on the "signal ≠ proof" boundary, mandatory rationale on every verification, supervisor sampling of decisions, four-eyes rule for cross-case links. |

---

### Standing safety commitments encoded in the product

* Never claims guilt; leads are "analytical leads", central nodes are "structurally important entities".
* Anomaly ≠ guilt; co-location ≠ proof of a meeting; a candidate identity match ≠ the same person.
* No predictive policing, no risk scoring of individuals, no recommendation of arrest, surveillance or any
  intrusive/unauthorised action — the action catalogue contains analytical steps only.
* Evidence is never fabricated; missing evidence is named; contradictions are displayed, never suppressed.
* Rejection preserves the original analytical finding with the rejector, rationale and timestamp.
* **"AI finds patterns. Evidence supports them. Specialized agents corroborate them. Security protects them.
  Humans decide what they mean."**
