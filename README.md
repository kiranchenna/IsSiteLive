# IsSiteLive

Synthetic monitoring: drives a real headless browser through each site's login flow on a schedule, watches for AJAX calls that fail (500/502/504) even when the page itself loads fine, and alerts on failures and recoveries.

Stack: FastAPI + Playwright + APScheduler + SQLite on the backend, React + Vite + Tailwind on the frontend.

## Prerequisites

- **Docker Desktop** (recommended path), or
- **Python 3.10+** and **Node 20+** for running the two services directly

## Quick start (Docker)

1. Create the backend env file and generate an encryption key (used to encrypt stored account passwords at rest):

   ```
   cp backend/.env.example backend/.env
   python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

   Paste the printed key into `ENCRYPTION_KEY` in `backend/.env`.

2. Build and start both services:

   ```
   docker compose up --build
   ```

3. Open the app:

   - Frontend (dashboard + admin UI): http://localhost:5173
   - Backend API docs (Swagger UI): http://localhost:8000/docs

   Data (SQLite file + failure screenshots) persists in a named Docker volume across restarts.

   To point the frontend at a non-localhost backend (e.g. deploying to a server), set `VITE_API_BASE` before building:
   ```
   VITE_API_BASE=https://your-host:8000 docker compose up --build
   ```

Stop everything with `docker compose down` (add `-v` only if you also want to wipe stored data).

### Using custom ports

By default the backend listens on `8000` and the frontend on `5173` (both configurable):

**Docker:**
```
BACKEND_PORT=9000 FRONTEND_PORT=4000 docker compose up --build
```
Since the frontend is built as static assets, it needs to know the backend's URL *at build time* — if you change `BACKEND_PORT`, pass a matching `VITE_API_BASE` too:
```
BACKEND_PORT=9000 FRONTEND_PORT=4000 VITE_API_BASE=http://localhost:9000 docker compose up --build
```

**Without Docker:**
```
./venv/bin/uvicorn app.main:app --reload --port 9000
```
```
npm run dev -- --port 4000
```
If the backend isn't on the default `8000`, point the frontend at it via `frontend/.env` (copy from `frontend/.env.example`) or inline: `VITE_API_BASE=http://localhost:9000 npm run dev`.

## Running without Docker

**Backend:**
```
cd backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/playwright install chromium   # one-time: downloads the headless browser
cp .env.example .env                     # then fill in ENCRYPTION_KEY as above
./venv/bin/uvicorn app.main:app --reload
```
Backend runs at http://localhost:8000.

**Frontend** (in a second terminal):
```
cd frontend
npm install
npm run dev
```
Frontend runs at http://localhost:5173 and expects the backend at `http://localhost:8000` by default (override via a `VITE_API_BASE` env var or `frontend/.env`, see `frontend/.env.example`).

## First-time walkthrough

Once both services are running, open the frontend and:

1. **Sites → + Add site** — give it a name, base URL, and check interval.
2. On the site's page, add a **demo account** (label, username, password) — a real but low-privilege login the checker will use.
3. Fill in the **login flow** as JSON steps (`navigate`, `click`, `fill`, `wait_for_selector`, `assert_selector_absent`, …) — use `{{username}}` / `{{password}}` in `fill` steps. Optionally add AJAX URL patterns to watch for 4xx/5xx responses.
4. Under **Alert channels**, add a Slack webhook or email recipients, optionally marking one as default.
5. Click **Run now** on the site to trigger an immediate check and confirm the flow works before waiting for the schedule.

For a full worked example — a real SSO login flow, an annotated flow JSON, reading a failed run's step detail and screenshot, and how alerts behave — see **[USAGE.md](USAGE.md)**.

## Configuration reference (`backend/.env`)

| Variable | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | SQLite connection string | `sqlite:///./data/issitelive.db` |
| `ENCRYPTION_KEY` | Fernet key encrypting stored account passwords — **required**, no default | — |
| `SCREENSHOTS_DIR` | Where per-step screenshots are written (served at `/screenshots`) | `./data/screenshots` |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_FROM` / `SMTP_USE_TLS` | Outgoing mail server used by email alert channels | `localhost:1025`, no auth |
| `DEFAULT_CHECK_CONCURRENCY` | Max checks run in parallel per scheduler tick | `3` |
| `DEFAULT_STEP_TIMEOUT_MS` | Per-step timeout in a flow (can be overridden per step) | `300000` |
| `SCREENSHOT_RETENTION_DAYS` | How long screenshot *files* are kept before being deleted (run history/status is kept regardless) | `180` (6 months) |

Every check now captures a screenshot after each step (not just on failure), so screenshots are pruned automatically once a day — anything older than `SCREENSHOT_RETENTION_DAYS` gets its image file deleted (the run's pass/fail history stays). To trigger a sweep on demand instead of waiting for the daily cycle, or to run it with a different cutoff just once:
```
curl -X POST "http://localhost:8000/api/screenshots/cleanup"        # uses SCREENSHOT_RETENTION_DAYS
curl -X POST "http://localhost:8000/api/screenshots/cleanup?days=30" # one-off override
```

## Tests

```
cd backend
./venv/bin/pytest tests/
```

Covers the flow step executor and the alert dispatcher's state machine (fail-every-time, recover-once, silent-on-repeat-success).

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
- **Docker build hangs or fails to connect** — Docker Desktop isn't running; start it first.
- **Checks fail with a browser launch error (non-Docker)** — run `./venv/bin/playwright install chromium` once inside the backend venv.
- **Frontend loads but shows fetch/network errors** — the backend isn't running or `VITE_API_BASE` doesn't match where it's listening.
