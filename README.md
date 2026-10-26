# Cadence

**Uptime, on a steady cadence.**

Cadence watches a handful of URLs, checks them every five minutes, and publishes the results on a dense public status page: uptime, latency percentiles, incidents, and a small game layer (streaks, HP, achievements) computed from real data.

**Live demo:** not deployed yet. The runbook is [`docs/DEPLOY.md`](docs/DEPLOY.md); the live links and a screenshot are added to this README after the first deploy.

> Once deployed on the free tiers, the first load can take up to a minute because the Render backend sleeps when idle.
> The page is server-rendered and cached, so visitors still see the last results while it wakes up.

## Architecture

```mermaid
flowchart LR
    Cron["GitHub Actions cron<br/>*/5 * * * *"] -- "POST /internal/run-sweep<br/>X-Cron-Secret" --> API
    subgraph Render["Render (Docker)"]
        API["FastAPI + httpx"]
    end
    API -- "async GET x N in parallel" --> Targets["Monitored URLs"]
    API <--> DB[("Neon Postgres")]
    Browser["Visitor"] --> Next["Next.js on Vercel<br/>server-rendered, revalidate 60s"]
    Next -- "GET /summary, /monitors, ..." --> API
    Browser -- "refresh every 60s" --> API
```

| Part | Tech |
| --- | --- |
| Backend | Python 3.13+ (3.14 in Docker and CI), FastAPI, httpx, SQLAlchemy 2.0 async + asyncpg, Alembic, Pydantic v2 |
| Database | PostgreSQL (Docker/Podman locally, Neon in production) |
| Frontend | Next.js (App Router), TypeScript, Tailwind, plain SVG charts |
| Scheduler | GitHub Actions cron |
| Hosting | Render (API), Vercel (web) |

A **sweep** checks every monitor in parallel. **Down** = timeout, connection error or 5xx; **slow** = OK but over 500 ms; an **incident** opens after two consecutive failures. The full rules, module map and the reasoning behind each choice are in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Docs

| Doc | Read it for |
| --- | --- |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | How it works, the module map, and the decisions and trade-offs |
| [`docs/DEPLOY.md`](docs/DEPLOY.md) | The step-by-step deploy runbook (Neon, Render, Vercel, GitHub secrets) |
| [`docs/BUG_JOURNAL.md`](docs/BUG_JOURNAL.md) | Real bugs hit while building it: symptom, cause, fix, lesson |
| [`docs/INTERVIEW_QA.md`](docs/INTERVIEW_QA.md) | Short answers about the design |
| [`frontend/README.md`](frontend/README.md) | The Next.js app: scripts, data flow, components |

## Run locally

Prerequisites: Python 3.13+ with [uv](https://docs.astral.sh/uv/), Node 22+, and Docker or Podman. No paid keys or API accounts are needed to run it locally.

```bash
# 1. Database (use `podman` instead of `docker` if you prefer)
docker compose up -d db

# 2. Backend
cd backend
cp .env.example .env
uv sync
uv run alembic upgrade head
uv run python -m scripts.seed          # monitors come from seed/monitors.json
uv run uvicorn app.main:app --reload   # http://localhost:8000/docs

# 3. Trigger a sweep (any time; the cron does this in production)
curl -X POST -H "X-Cron-Secret: change-me" localhost:8000/internal/run-sweep

# 4. Frontend
cd ../frontend
cp .env.example .env.local
npm install
npm run dev                             # http://localhost:3000
```

Configuration (all environment variables, see the `.env.example` files):

| Variable | Where | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | backend | Postgres connection string (Neon's plain URL works) |
| `CRON_SECRET` | backend + GitHub secret | Shared secret for `POST /internal/run-sweep` |
| `CORS_ORIGIN` | backend | The only browser origin allowed to call the API |
| `NEXT_PUBLIC_API_URL` | frontend | Base URL of the API |

### Tests and checks

The backend has **103 tests** (`pytest` collects them). They need Postgres running and use a separate `cadence_test` database, created automatically:

```bash
cd backend
uv run pytest                 # tests
uv run ruff check .           # lint
cd ../frontend
npm run lint && npx tsc --noEmit && npm run build
```

CI runs the backend tests and `ruff` on Python 3.13 and 3.14 against a Postgres service, plus the frontend lint, type-check and build.

Regenerate the frontend API types after changing the backend schema (backend must be running):

```bash
cd frontend && npm run gen:types
```

Edit the monitored URLs in `backend/seed/monitors.json`. The seed runs on every deploy and updates monitors by `short_code`. Point it at your own services.

## API

Interactive docs at `/docs`. Try it:

```bash
curl localhost:8000/health
curl localhost:8000/summary                      # KPIs, streaks, next sweep ETA
curl localhost:8000/monitors                     # per-service state, uptime, HP, rank, 30-day history
curl "localhost:8000/monitors/1/latency?range=7d"  # 24h | 7d | 30d
curl "localhost:8000/checks/recent?limit=12"
curl localhost:8000/incidents
curl localhost:8000/achievements
curl -X POST -H "X-Cron-Secret: change-me" localhost:8000/internal/run-sweep
```

Errors use a uniform `{"detail": "..."}` body: 4xx for bad input, 502/503/504 when the database misbehaves, and 401 for a wrong cron secret.

## Deploy

Short version (full runbook in [`docs/DEPLOY.md`](docs/DEPLOY.md)):

1. **Neon**: create a project and copy the connection string.
2. **Render**: new Blueprint from this repo (`render.yaml`). Set `DATABASE_URL` (Neon string, used as-is), `CRON_SECRET` (`openssl rand -hex 32`) and `CORS_ORIGIN` (your Vercel URL).
3. **Vercel**: import the repo, root directory `frontend`, env var `NEXT_PUBLIC_API_URL` = Render URL.
4. **GitHub**: repo secrets `API_URL` (Render URL) and `CRON_SECRET` (same value as Render). The `Sweep` workflow then runs every 5 minutes. Until both secrets exist it logs a warning and does nothing.

## Limitations

- The free Neon and Render tiers sleep and have storage and compute caps, so the first request after idle is slow.
- GitHub's cron is best-effort: "every 5 minutes" can slip by a few minutes, and runs may be throttled on busy days.
- Nothing in the repo authenticates visitors; the dashboard is a public read-only page by design.
- It is not deployed yet, so the numbers above describe the code and tests, not a running instance.

## Status

All of the v1 scope is built: sweeps, incidents, the read API, the game layer, the dashboard with its loading, empty, error and incident states, CI, and the cron workflow. Deployment and the live links are the remaining manual steps.

## Repo layout

```
backend/    FastAPI app, Alembic migrations, seed, tests
frontend/   Next.js app
docs/       architecture, deploy runbook, bug journal, interview Q&A
.github/    CI (backend tests + ruff on Python 3.13/3.14, frontend lint/type-check/build) and the sweep cron
render.yaml docker-compose.yml
```

Built by Bhavanjot Singh.
