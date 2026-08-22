@@ -0,0 +1,290 @@
# Backend Setup & Startup Guide

How to get the TrackIT Flask API running locally, and what to change for production.

The backend is a Flask 2.3 application built with the app-factory pattern. It lives
entirely in `backend/`, serves a JSON API under `/api/*`, and streams real-time updates
over Server-Sent Events (`GET /api/analytics/stream`) — there is no WebSocket layer.

> **Run every command from the `backend/` directory.** The app factory does
> `from config import config_by_name`, which only resolves when `backend/` is the
> working directory (or on `sys.path`). Running `python backend/run.py` from the repo
> root will fail with `ModuleNotFoundError: No module named 'config'`.

---

## 1. Prerequisites

- **Python 3.13+** — the root `pyproject.toml` sets `requires-python = ">=3.13"`, and the
  checked-in virtualenv is CPython 3.13.13.
- **Node 18+** — only if you also want to run the frontend (see §7).

---

## 2. Install dependencies

A `.venv` already exists at the repo root, but do not assume it is complete — it has
previously drifted out of sync with `requirements.txt` (missing `flask-migrate` and
`gevent`). Because `backend/app/__init__.py` imports `flask_migrate` at module load, a
missing dependency stops the server before it prints anything useful. Always run the
install step.

```powershell
# from the repo root
.\.venv\Scripts\Activate.ps1

cd backend
pip install -r requirements.txt
```

To build a fresh environment instead:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

---

## 3. Configure (optional in development)

`run.py` calls `load_dotenv()` with no path, so it reads `backend/.env` if one exists.
**You do not need one to start in development** — every setting has a working dev
default: SQLite for the database, and `"dev-secret-key"` for both `SECRET_KEY` and
`JWT_SECRET_KEY`.

Create `backend/.env` only when you want to override something:

```dotenv
FLASK_ENV=development
PORT=5000

# Point at Postgres instead of the default SQLite file
# DATABASE_URL=postgresql://user:pass@localhost:5432/trackit

# Only needed to exercise password-reset emails
# MAIL_USERNAME=you@gmail.com
# MAIL_PASSWORD=your-app-password
```

Other useful knobs read by `config.py`: `HOST`, `DEBUG`, `CORS_ORIGINS`,
`FRONTEND_BASE_URL`, `TRACKING_PUBLIC_URL`, `REDIS_URL`, `CRON_SECRET`. All have
defaults; see `backend/config.py` for the full list.

Live-tracking knobs, all optional:

| Variable | Default | What it does |
|---|---|---|
| `SCAN_DEDUP_SECONDS` | `30` | Window in which an identical repeat scan is suppressed |
| `ENABLE_MISPLACED_DETECTION_PER_SCAN` | `true` | Run misplaced-item detection on every scan |
| `MAX_PLAUSIBLE_SPEED_KMH` | `900` | Ceiling for impossible-travel detection. Roughly commercial-jet cruise |
| `SYSTEM_EVENT_RETENTION_DAYS` | `7` | How long `system_events` rows are kept before the pruning job deletes them |

---

## 4. Prepare the database

Development uses SQLite. The URI `sqlite:///trackit_dev.db` resolves relative to the app
package under Flask-SQLAlchemy 2.5.1, so the actual file is
**`backend/app/trackit_dev.db`** — which already exists locally and is populated.

**On SQLite you do not run migrations.** `run.py` calls `db.create_all()` at boot whenever
the config is in debug or testing mode, so the schema is built and kept up to date for you
on startup. The factory additionally runs `ensure_movement_schema_columns()`, which patches
any missing columns on `item_issues` / `item_returns`. Starting the server is all you need.

> Running `alembic -c alembic.ini upgrade head` against the SQLite dev database **fails**.
> Revision `7ae1ef9507ee` issues `ALTER TABLE assets ALTER COLUMN purchase_value TYPE
> NUMERIC(12, 2)`, which SQLite rejects with `near "ALTER": syntax error`. The migration
> history targets PostgreSQL.

When you are pointed at PostgreSQL (`DATABASE_URL` / `DATABASE_URL_PROD`), apply the 34
Alembic revisions:

```powershell
# from backend/
alembic -c alembic.ini upgrade head
```

Or via the Flask CLI:

```powershell
$env:FLASK_APP = "run.py"
flask db upgrade
```

If `upgrade head` complains about multiple heads, use `upgrade heads` (plural) — the
history contains merge revisions. `backend/scripts/apply_migrations.py` handles that
fallback automatically:

```powershell
python scripts/apply_migrations.py --env production
```

## 5. Seed test data (optional)

```powershell
# from backend/
python db_seed.py
```

The script is idempotent (get-or-create), so it is safe to re-run. It creates 2
organizations, 3 departments, 5 users, 2 assets, 2 inventory items, and 3 stock
movements, then prints:

| Role | Email | Password |
|---|---|---|
| Admin | `admin@techcorp.com` | `Admin123!` |
| Staff | `staff1@techcorp.com` | `Staff123!` |
| Dept Head | `depthead@techcorp.com` | `Head123!` |
| Store Manager | `storemgr@techcorp.com` | `Store123!` |
| Superadmin | `frankadmin@trackit.com` | `P@55w0rd123!_` |

---

## 6. Start the server

```powershell
# from backend/
python run.py
```

The API is now on **http://localhost:5000** (defaults: `HOST=0.0.0.0`, `PORT=5000`).

Verify it:

```powershell
curl http://localhost:5000/health
```

`/health` checks database connectivity and disk, returning 200 when healthy and 503 when
not. There is also `GET /` for service info and `GET /ping` for a bare liveness check.

Set `DEBUG=true` in your environment to enable the Flask debugger and auto-reloader —
`run.py` only turns on the reloader in explicit debug mode.

---

## 7. Connecting the frontend

```powershell
cd frontend
npm install
npm run dev
```

Vite serves on **port 5173** and proxies `/api` and `/static` to `http://localhost:5000`,
so the backend must already be running.

> **Use `http://localhost:5173`, not `http://127.0.0.1:5173`.** The development CORS
> whitelist covers `localhost` on ports 3000, 5000, 5173, 5174, and 8080 — it does not
> include `127.0.0.1`. Since auth uses credentialed cookies, requests from the
> `127.0.0.1` origin are rejected. Note that `frontend/start.bat` binds to `127.0.0.1`;
> prefer `npm run dev`.

---

## 8. Running the tests

```powershell
# from backend/
pytest tests/
```

Pass `tests/` explicitly. A bare `pytest` also collects the ad-hoc `test_*.py`,
`scratch_*.py`, and `tmp_*.py` scripts sitting loose in `backend/`, which are not part of
the suite. Tests run against an in-memory SQLite database via `TestingConfig`.

Coverage is available but not preconfigured: `pytest tests/ --cov=app`.

As of this branch the suite reports **191 passed, 7 failed**. The failures are in
`test_misplaced_items.py`, `test_sse_integration.py`, and `test_tracking_ai.py` and are
pre-existing — they are not a sign of a broken local setup.

---

## 9. Production

Production uses the `wsgi.py` entry point with gunicorn's gevent worker — the gevent
worker is what lets four workers hold open SSE connections. From `backend/Procfile`:

```
web: gunicorn -w 4 -k gevent -b 0.0.0.0:$PORT wsgi:app
```

Unlike `run.py`, `wsgi.py` does **not** call `load_dotenv()`, so the process environment
must supply everything. Required:

| Variable | Notes |
|---|---|
| `FLASK_ENV=production` | Selects `ProductionConfig`; also enables HTTPS enforcement |
| `DATABASE_URL_PROD` | PostgreSQL/Supabase URL. Falls back to `DATABASE_URL`. Direct `db.*.supabase.co` hosts are auto-rewritten to the pooler, and `sslmode=require` is appended |
| `JWT_SECRET_KEY` | **Must be at least 32 characters** — `create_app` raises on startup otherwise |
| `SECRET_KEY` | No default in production |
| `CORS_ORIGINS` | Comma-separated. Defaults to the two Vercel deployment URLs |

Generate a secret with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## 10. Scheduled jobs

Both are plain HTTP endpoints rather than a scheduler dependency, guarded by
`CRON_SECRET` and called from cron-job.org. Each accepts the token either as
`?token=...` or as an `X-Cron-Secret` header. If `CRON_SECRET` is unset the
endpoints are unauthenticated — set it in production.

| Endpoint | Cadence | Purpose |
|---|---|---|
| `/cron/keepalive` | every ~10 min | Wakes the Render free-tier host. Add `?db=1` to also check the database |
| `/cron/prune-system-events` | daily | Deletes `system_events` rows older than `SYSTEM_EVENT_RETENTION_DAYS` |

Both are also registered under `/api/...`.

### Why pruning matters

`system_events` is disposable plumbing: every `event_bus.publish()` call writes one
row, from fifty call sites, into the very table every open SSE stream polls every
two seconds. Left unpruned it grows without bound and the poll degrades with it.

It is **not** `scan_events`. That table is the permanent business ledger — an item
moved, here is where and when — and nothing in this job touches it.

The job deletes in bounded batches of 500, committing as it goes, so it never holds
a long lock on a table that live streams are reading. It returns the deleted count:

```json
{"ok": true, "purpose": "prune-system-events", "retention_days": 7, "deleted": 1432}
```

---

## 11. SSE access tokens in request URLs

`GET /api/analytics/stream` accepts its JWT as an `access_token` query parameter.
This is deliberate: the browser `EventSource` API cannot set request headers, so
there is nowhere else for a token to go. The endpoint still accepts a normal
`Authorization` header or cookie when the caller can send one.

**The operational consequence is that a full access token lands in every access log
that records query strings**, and also in browser history and in any `Referer` the
page emits. Before deploying:

- Scrub or mask query strings for this path in the reverse proxy's access log. On
  nginx, log `$uri` rather than `$request` for `/api/analytics/stream`, or define a
  dedicated `log_format` for that location.
- Check the same for the hosting platform's own request logs (Render logs the full
  request line by default).
- Keep `JWT_ACCESS_TOKEN_EXPIRES` short — it is one hour today — so a leaked token
  from a log has a bounded life.

The durable fix is a short-lived, stream-scoped ticket: a dedicated endpoint mints a
single-use token valid only for the stream, and `/analytics/stream` accepts only
that, never a full access token. That needs its own auth review and is tracked
separately — the logging measures above are what stands in the meantime.
