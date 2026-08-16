# IsSiteLive

Synthetic monitoring: drives a real headless browser through each site's login flow on a schedule, watches for AJAX calls that fail (500/502/504) even when the page itself loads fine, and alerts on failures and recoveries.

Stack: FastAPI + Playwright + APScheduler + SQLite on the backend, React + Vite + Tailwind on the frontend.

## Prerequisites

- **Docker Desktop** (recommended path) — on Windows, use the **WSL2 backend** (Docker Desktop enables this by default on a modern install); on Linux, [Docker Engine](https://docs.docker.com/engine/install/) works just as well as Docker Desktop, or
- **Python 3.10+** and **Node 20+** for running the two services directly

Supported on macOS, Linux, and Windows. Commands below are given for **macOS/Linux** (bash/zsh) and **Windows (PowerShell)** wherever they differ — PowerShell is the default terminal in Windows Terminal and VS Code. If you're on the classic Command Prompt instead, swap `Copy-Item` for `copy` and `$env:VAR="value"; command` for `set VAR=value&& command`.

## Quick start (Docker)

1. Create the backend env file and generate an encryption key (used to encrypt stored account passwords at rest):

   ```bash
   # macOS/Linux
   cp backend/.env.example backend/.env
   python3 -c "import base64, secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
   ```
   ```powershell
   # Windows (PowerShell)
   Copy-Item backend\.env.example backend\.env
   python -c "import base64, secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
   ```

   Paste the printed key into `ENCRYPTION_KEY` in `backend/.env`. (This uses only Python's standard library, deliberately — the Docker path shouldn't require `cryptography` to already be installed locally just to generate one key. The result is a valid Fernet key either way: that's exactly what `Fernet.generate_key()` does internally.)

2. Build and start both services:

   ```
   docker compose up --build
   ```

3. Open the app:

   - Frontend (dashboard + admin UI): http://localhost:5173
   - Backend API docs (Swagger UI): http://localhost:28743/docs

   Data (SQLite file + failure screenshots) persists in a named Docker volume across restarts.

   To point the frontend at a non-localhost backend (e.g. deploying to a server), set `VITE_API_BASE` before building:
   ```bash
   # macOS/Linux
   VITE_API_BASE=https://your-host:28743 docker compose up --build
   ```
   ```powershell
   # Windows (PowerShell)
   $env:VITE_API_BASE="https://your-host:28743"; docker compose up --build
   ```

Stop everything with `docker compose down` (add `-v` only if you also want to wipe stored data).

### Using custom ports

By default the backend listens on `28743` and the frontend on `5173` (both configurable, chosen to avoid the usual dev-server defaults like 3000/8000/8080). The simplest cross-platform way is a `.env` file in the project root (Docker Compose reads it automatically) with `BACKEND_PORT=9000` / `FRONTEND_PORT=4000` / `VITE_API_BASE=http://localhost:9000` — then just run `docker compose up --build` as usual. Or set them inline for one run:

**Docker — macOS/Linux:**
```bash
BACKEND_PORT=9000 FRONTEND_PORT=4000 VITE_API_BASE=http://localhost:9000 docker compose up --build
```
**Docker — Windows (PowerShell):**
```powershell
$env:BACKEND_PORT="9000"; $env:FRONTEND_PORT="4000"; $env:VITE_API_BASE="http://localhost:9000"; docker compose up --build
```
(The frontend is built as static assets, so it needs to know the backend's URL *at build time* — always pass a matching `VITE_API_BASE` alongside a custom `BACKEND_PORT`.)

**Without Docker — macOS/Linux:**
```bash
./venv/bin/uvicorn app.main:app --reload --port 9000
npm run dev -- --port 4000
```
**Without Docker — Windows (PowerShell):**
```powershell
.\venv\Scripts\uvicorn.exe app.main:app --reload --port 9000
npm run dev -- --port 4000
```
If the backend isn't on the default `28743`, point the frontend at it via `frontend/.env` (copy from `frontend/.env.example`) or inline — `VITE_API_BASE=http://localhost:9000 npm run dev` (macOS/Linux) / `$env:VITE_API_BASE="http://localhost:9000"; npm run dev` (Windows PowerShell).

## Running without Docker

**Backend — macOS/Linux:**
```bash
cd backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/playwright install chromium   # one-time: downloads the headless browser
cp .env.example .env                     # then fill in ENCRYPTION_KEY as above
./venv/bin/uvicorn app.main:app --reload --port 28743
```

**Backend — Windows (PowerShell):**
```powershell
cd backend
python -m venv venv
.\venv\Scripts\pip.exe install -r requirements.txt
.\venv\Scripts\playwright.exe install chromium   # one-time: downloads the headless browser
Copy-Item .env.example .env                  # then fill in ENCRYPTION_KEY as above
.\venv\Scripts\uvicorn.exe app.main:app --reload --port 28743
```
(These call the venv's executables directly rather than "activating" it first, so it works the same whether or not PowerShell's script execution policy allows running `Activate.ps1` — one less thing to troubleshoot. If `python` isn't found, you likely installed Python without checking "Add python.exe to PATH"; re-run the installer and check that box, or use the `py` launcher instead: `py -m venv venv`.)

`UVICORN_PORT` is read directly by uvicorn's own CLI (it auto-derives environment variables from every `--flag`, e.g. `--port` ⟷ `UVICORN_PORT`) -- this happens before the app or its `.env` file is ever loaded, which is why the port can't just be a setting inside the app itself. Without it set, plain `uvicorn app.main:app --reload` falls back to uvicorn's own default of port `8000`, not `28743`.

Backend runs at http://localhost:28743.

**Frontend** (in a second terminal, same on every OS):
```
cd frontend
npm install
npm run dev
```
Frontend runs at http://localhost:5173 and expects the backend at `http://localhost:28743` by default (override via a `VITE_API_BASE` env var or `frontend/.env`, see `frontend/.env.example`).

## First-time walkthrough

Once both services are running, open the frontend and:

1. **Sites → + Add site** — give it a name, base URL, and check interval.
2. On the site's page, add a **demo account** (label, username, password) — a real but low-privilege login the checker will use.
3. Fill in the **testing flow** as JSON steps (`navigate`, `click`, `fill`, `wait_for_selector`, `assert_selector_absent`, `assert_text_contains`, …) — use `{{username}}` / `{{password}}` in `fill` steps, or record it by clicking through the real site instead of writing JSON by hand. Optionally add AJAX URL patterns to watch for 4xx/5xx responses.
4. Under **Alert channels**, add a Slack webhook or email recipients, optionally marking one as default.
5. Click **Run now** on the site to trigger an immediate check and confirm the flow works before waiting for the schedule.

For a full worked example — a real SSO login flow, an annotated flow JSON, reading a failed run's step detail and screenshot, and how alerts behave — see **[USAGE.md](USAGE.md)**.

## Configuration reference (`backend/.env`)

| Variable | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | SQLite connection string | `sqlite:///./data/issitelive.db` |
| `ENCRYPTION_KEY` | Fernet key encrypting stored account passwords — **required**, no default | — |
| `SCREENSHOTS_DIR` | Where per-step screenshots are written (served at `/screenshots`) | `./data/screenshots` |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_FROM` / `SMTP_USE_TLS` | Shared default mail server for email alert channels. Any individual channel can override some or all of these fields with its own mail server, configured entirely through the UI — no `.env` access needed | `localhost:1025`, no auth |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_WHATSAPP_FROM` | Twilio account used by WhatsApp alert channels — one account per deployment, recipients are set per channel | empty (WhatsApp channels no-op until set) |
| `DEFAULT_CHECK_CONCURRENCY` | Max checks run in parallel per scheduler tick | `3` |
| `DEFAULT_STEP_TIMEOUT_MS` | Per-step timeout in a flow (can be overridden per step) | `300000` |
| `SCREENSHOT_RETENTION_DAYS` | How long screenshot *files* are kept before being deleted (run history/status is kept regardless) | `180` (6 months) |

Every check now captures a screenshot after each step (not just on failure), so screenshots are pruned automatically once a day — anything older than `SCREENSHOT_RETENTION_DAYS` gets its image file deleted (the run's pass/fail history stays). To trigger a sweep on demand instead of waiting for the daily cycle, or to run it with a different cutoff just once (`curl` ships with Windows 10/11 by default too, so this command is the same everywhere):
```
curl -X POST "http://localhost:28743/api/screenshots/cleanup"        # uses SCREENSHOT_RETENTION_DAYS
curl -X POST "http://localhost:28743/api/screenshots/cleanup?days=30" # one-off override
```

## Tests

```bash
# macOS/Linux
cd backend
./venv/bin/pytest tests/
```
```powershell
# Windows (PowerShell)
cd backend
.\venv\Scripts\pytest.exe tests\
```

Reads `ENCRYPTION_KEY` from `backend/.env` the same way the app does, so no extra setup is needed beyond the Quick start step above. Covers the flow step executor and the alert dispatcher's state machine (fail-every-time, recover-once, silent-on-repeat-success).

## Project structure

```
backend/
  app/
    checker/     # Playwright step runner + AJAX response watcher
    recorder/    # Live flow recorder: CDP screencast + click/type capture -> flow JSON
    alerts/      # Slack/email senders + fail/recovery dispatch logic
    routers/     # FastAPI endpoints (sites, accounts, flows, alert channels, runs)
    scheduler.py # APScheduler jobs, one per active site, rescheduled live on edits
    reports.py   # Excel (.xlsx) export: raw run log + collapsed up/down timeline
    models.py    # SQLAlchemy schema
  tests/
frontend/
  src/
    pages/        # Dashboard, SiteDetail, admin screens
    components/    # PulseStrip, StatusBadge
    api/client.ts   # typed fetch wrapper around the backend API
docker-compose.yml
```

## Troubleshooting

- **`ENCRYPTION_KEY` errors on startup** — `.env` is missing or the key wasn't generated/pasted in; see step 1 above.
- **Docker build hangs or fails to connect** — Docker Desktop isn't running; start it first. On Windows, also confirm Docker Desktop is set to use the **WSL2 backend** (Settings → General) — the older Hyper-V backend is no longer the default and can behave differently.
- **Checks fail with a browser launch error (non-Docker)** — run `./venv/bin/playwright install chromium` (macOS/Linux) or `.\venv\Scripts\playwright.exe install chromium` (Windows) once inside the backend venv.
- **Frontend loads but shows fetch/network errors** — the backend isn't running or `VITE_API_BASE` doesn't match where it's listening.
- **Windows: `python` / `pip` not recognized** — Python wasn't added to `PATH` during install. Re-run the Python installer and check "Add python.exe to PATH", or use the `py` launcher instead (`py -m venv venv`).
- **Windows: `running scripts is disabled on this system`** — this only happens if you try to `venv\Scripts\Activate.ps1` directly; the commands above avoid that by calling `.\venv\Scripts\<tool>.exe` directly instead of activating the venv first, so it isn't necessary to change PowerShell's execution policy.
- **Windows: `cp`, `source`, or `VAR=value command` not recognized** — those are bash/zsh syntax; use the Windows (PowerShell) command shown alongside each step instead (`Copy-Item`, calling the venv executable directly, `$env:VAR="value"; command`).
