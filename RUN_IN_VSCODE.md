# Running CrimeNet AI in VS Code — step by step

Two processes make up the app:

| Service | Port | What it is |
|---|---|---|
| **API server** | `8000` | Python · FastAPI · the agents, algorithms, databases, audit and ledger |
| **Web app** | `5173` | React · TypeScript · Tailwind · Cytoscape.js · Leaflet (Vite dev server) |

The web app proxies every `/api/...` call to the API server, so you always open **http://localhost:5173** — never port 8000 directly (except for the API docs).

---

## Step 0 — Install the prerequisites (once)

| Tool | Version | Check with | Get it |
|---|---|---|---|
| Python | **3.11 – 3.13** | `python --version` | <https://www.python.org/downloads/> — tick **“Add python.exe to PATH”** |
| Node.js | **20 LTS or newer** | `node --version` | <https://nodejs.org/> (LTS installer) |
| VS Code | any current | — | <https://code.visualstudio.com/> |

> Windows note: if `python --version` opens the Microsoft Store, install Python from python.org and re-open your terminal.

---

## Step 1 — Get the project onto your computer

1. In the Arena workspace panel (folder icon, top-right), **download the project folder**.
2. Unzip it somewhere simple, e.g. `C:\Projects\crimenet-ai`.
3. The folder must contain: `backend/`, `frontend/`, `.vscode/`, `start.bat`, `start.sh`, `verify_workflow.sh`, `README.md`.

---

## Step 2 — Open the folder in VS Code

`File → Open Folder…` → select **`crimenet-ai`** (the folder that contains `backend` and `frontend`, not one of them).

When VS Code asks *“Do you want to install the recommended extensions?”* click **Install**. They are:
Python, Debugpy, ESLint, Tailwind CSS IntelliSense, Prettier, Ruff.

---

## Step 3 — Create the Python environment

Open the terminal with **`Ctrl + ~`** (View → Terminal), then run:

**Windows (PowerShell):**
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m spacy download en_core_web_sm
cd ..
```

*If PowerShell blocks the activate script* (`running scripts is disabled`), run this once and retry:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
…or just use **Command Prompt** instead: `.\.venv\Scripts\activate.bat`

**macOS / Linux:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
cd ..
```

Then tell VS Code to use it: **`Ctrl+Shift+P` → “Python: Select Interpreter” → `./backend/.venv`**.

The install takes 3–6 minutes the first time (spaCy, scikit-learn, pandas). It is a one-off.

---

## Step 4 — Install the frontend packages

In the same terminal:

```bash
cd frontend
npm install
cd ..
```

---

## Step 5 — Run both services

Pick **one** of these three ways.

### Way A — One click (recommended)
Press **`Ctrl+Shift+B`** (Run Build Task) → choose **“▶ Run CrimeNet AI (API + Web)”**.
Two terminal panels start side by side: the API server and the web app.

### Way B — Debugger (breakpoints in Python and React)
Open the **Run and Debug** panel (`Ctrl+Shift+D`) → select **“▶ CrimeNet AI — full stack”** → press **F5**.
You can now set breakpoints in `backend/app/**.py` and they will hit.

### Way C — Two terminals by hand
Terminal 1:
```bash
cd backend
.\.venv\Scripts\Activate.ps1      # Windows  (source .venv/bin/activate on macOS/Linux)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Terminal 2 (`Ctrl+Shift+5` to split):
```bash
cd frontend
npm run dev
```

> Windows shortcut: outside VS Code you can simply double-click **`start.bat`** — it creates the venv, installs everything, starts both services and opens the browser.

---

## Step 6 — Open the app

Go to **<http://localhost:5173>**

1. The **boot screen** appears: the CrimeNet AI mark, then four real start-up checks
   (client → API health → platform profile → session).
2. The **entry screen** follows. The pill must read **“Analytical services online”** — that means the API server is answering.
3. Click a demonstration account to fill it in, then **Sign In**:

| User ID | Password | Role |
|---|---|---|
| `SUP-1100` | `supervise123` | Supervisor — sees everything, can verify/reject |
| `ADM-0001` | `administer123` | Admin — adds user management |
| `ANL-3310` | `analyze123` | Analyst — runs analysis, cannot manage users |
| `INV-2201` | `investigate123` | Investigator — 3 assigned cases only |

API documentation (Swagger): **<http://localhost:8000/api/docs>**

---

## Step 7 — Prove the pipeline works (optional)

With both services running:

```bash
bash verify_workflow.sh          # Git Bash / WSL / macOS / Linux
```
or in VS Code: `Ctrl+Shift+P` → **Tasks: Run Task** → *CrimeNet: verify pipeline (33 checks)*.

It walks all 15 stages — login → case → evidence → extraction → resolution → cross-case → graph →
network → timeline → corroboration → gaps → next-best action → verification → SHA-256 → audit —
and prints **33 passed, 0 failed**.

The same run exists inside the app: sign in and open **Workflow** in the sidebar → **Run full workflow**.

---

## Step 8 — Suggested five-minute tour

1. **Dashboard** → *Run full case analysis* — six agents execute a 12-task plan.
2. **Evidence** → open `EV-2042` → *Integrity check* → `INTEGRITY_MISMATCH` (tamper demo).
3. **Network** → *Run network analysis*; highlight the path `PER-001 → LOC-001 → PER-004`; click an edge to see the evidence behind the relationship.
4. **Cross-Case** → `CASE-101 ↔ CASE-202`, strength 97.0 → verify or reject with a rationale.
5. **Entities** → `Ravi Kumar ↔ R. Kumar` 95.0 HIGH → confirm or keep separate (never auto-merged).
6. **Information Gaps** → `IG-001` → **Next-Best Action** → execute the top-ranked analysis.
7. **Audit** → audit trail, integrity register, *Verify ledger chain*.
8. Open **CASE-512** for the deliberate **INSUFFICIENT EVIDENCE** path.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Entry screen shows **“Analytical services offline”** | API server not running / crashed | Look at the API terminal; restart Step 5. Test directly: <http://localhost:8000/api/health> |
| Sign-in does nothing, no error | Same as above — the browser cannot reach the API | Same fix; the pill now tells you immediately |
| `ModuleNotFoundError: fastapi` | Wrong interpreter — venv not active | Activate `.venv`, or `Ctrl+Shift+P → Python: Select Interpreter → ./backend/.venv` |
| `Can't find model 'en_core_web_sm'` | spaCy model not downloaded | `python -m spacy download en_core_web_sm` inside the venv |
| `Port 8000 is already in use` | An old server is still running | Windows: `netstat -ano \| findstr :8000` then `taskkill /PID <pid> /F` · macOS/Linux: `lsof -ti:8000 \| xargs kill` |
| `Port 5173 is already in use` | Old Vite instance | Same approach with `:5173`, or let Vite pick the next port and open that URL |
| `npm : cannot be loaded ... running scripts is disabled` | PowerShell policy | `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` or use Command Prompt |
| Map tiles blank | No internet access for OpenStreetMap tiles | Everything else works offline; tiles need a connection |
| Data looks changed after a restart | Embedded stores are in-memory in this profile | Restarting the API reloads the clean synthetic seed — this is expected |

---

## Optional — connect real databases

The app auto-detects these and switches profile; without them it runs the clearly labelled embedded
fallbacks shown on the **Security** page.

```powershell
$env:CRIMENET_POSTGRES_DSN = "postgresql://user:pass@localhost:5432/crimenet"
$env:CRIMENET_NEO4J_URI    = "bolt://localhost:7687"
$env:CRIMENET_NEO4J_USER   = "neo4j"
$env:CRIMENET_NEO4J_PASSWORD = "..."
$env:CRIMENET_REDIS_URL    = "redis://localhost:6379/0"
$env:CRIMENET_JWT_SECRET   = "change-me"
```

```bash
export CRIMENET_POSTGRES_DSN="postgresql://user:pass@localhost:5432/crimenet"
export CRIMENET_NEO4J_URI="bolt://localhost:7687"
export CRIMENET_REDIS_URL="redis://localhost:6379/0"
export CRIMENET_JWT_SECRET="change-me"
```

Set them **before** starting the API server, then check **Settings/Security → Data & AI backends** —
the profile labels change from `EMBEDDED_*` to the connected service.

---

## Building for production

```bash
cd frontend
npm run build      # static bundle in frontend/dist
npm run preview    # serve the built bundle on :5173
```
The API server still needs to be running; deploy `dist/` behind any web server that proxies `/api` to the FastAPI service.
