# Deployment — Idea Atlas

Companion to `TRD.md`. Two distinct environments: local development (Ollama,
Docker Compose, your laptop) and production (Railway, hosted free-tier
inference). Read the note in `README.md`'s architecture section first if
you haven't already — the AI provider is intentionally swappable.

## 1. Why production differs from local dev

Local dev uses Ollama because it's genuinely free when you already own the
hardware. Railway is metered cloud compute — a constantly-loaded 8B model
would burn through the $5/month Hobby plan's usage credit quickly, separate
from whether the compute tier even comfortably runs it. So:

| | Local dev | Production (Railway) |
|---|---|---|
| AI provider | Ollama (`llama3.1:8b` or `phi3:mini`), fully local | Groq free tier (hosted, open-weight models, fast) |
| Database | Postgres via Docker Compose | Railway managed Postgres plugin |
| Cache | Redis via Docker Compose (optional) | Railway managed Redis plugin (optional) |
| Backend | `uvicorn` with `--reload` | Railway service running the same FastAPI app |
| Frontend | Vite dev server | Railway static service (built with `vite build`) |

`app/llm.py` reads an environment variable (`LLM_PROVIDER=ollama` or
`LLM_PROVIDER=groq`) and picks the right client. Nothing else in the
codebase should know or care which provider is active — if you find
yourself branching on provider anywhere outside `app/llm.py`, that's a sign
the abstraction leaked and needs fixing.

## 2. Local development setup

```bash
git clone <your-repo-url>
cd idea-atlas
cp .env.example .env          # fill in local values, LLM_PROVIDER=ollama
ollama pull llama3.1:8b       # one-time, ~5GB download
docker compose up --build
```

Backend: `http://localhost:8000` (docs at `/docs`)
Frontend: `http://localhost:5173`

## 3. Getting a free Groq API key (for production)

1. Sign up at console.groq.com — no payment method required for the free tier
2. Generate an API key
3. Note the free tier has rate limits (requests per minute and per day) —
   fine for a single-user portfolio project, not for real concurrent traffic.
   Check console.groq.com's current limits before relying on this for
   anything beyond personal/demo use, since free-tier terms can change.

## 4. Railway setup — step by step

### 4.1 Create the project

1. railway.app -> New Project -> Deploy from GitHub repo -> select your repo
2. Railway will try to auto-detect a single service from the repo root —
   stop and instead add services manually as below, since this is a
   multi-service app (backend + frontend + Postgres), not one deployable unit

### 4.2 Add Postgres

1. In the project, "New" -> "Database" -> "PostgreSQL"
2. Railway provisions it and exposes a `DATABASE_URL` variable automatically
   inside that service's scope

### 4.3 Add Redis (optional)

1. "New" -> "Database" -> "Redis"
2. Same pattern — exposes a `REDIS_URL`

### 4.4 Add the backend service

1. "New" -> "GitHub Repo" -> same repo, but set the root directory to `/backend`
2. Railway should detect the `Dockerfile` in `/backend` and build from it
   (Nixpacks also works without a Dockerfile, but a Dockerfile is more
   predictable — reuse the one from `TRD.md`'s stack if you already have it)
3. Under this service's Variables tab, reference the Postgres and Redis
   services so the backend gets their connection strings — Railway lets you
   reference another service's variable directly (e.g.
   `${{Postgres.DATABASE_URL}}`) instead of copy-pasting values, so it stays
   correct if Railway rotates credentials
4. Add the rest of the variables from section 5 below
5. Set the start command if not already in the Dockerfile:
   `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   (Railway injects `$PORT` — don't hardcode 8000 in production)

### 4.5 Run migrations on deploy

Add a release/predeploy step so Alembic migrations run automatically before
the new version starts serving traffic. In Railway, this is typically set
under the backend service's settings as a "Deploy" or "Release" command:

```bash
alembic upgrade head
```

Check Railway's current docs for the exact field name (this has moved
around between "Pre-Deploy Command" and similar in different Railway UI
versions) — the important part is that migrations run before the new
backend instance starts accepting requests, not after.

### 4.6 Add the frontend service

1. "New" -> "GitHub Repo" -> same repo, root directory `/frontend`
2. Build command: `npm run build`
3. Railway can serve the built static files directly, or you can point the
   frontend's `VITE_API_URL` variable at the backend service's public
   Railway URL (Railway gives every service a `*.up.railway.app` domain by
   default, or attach a custom domain later)

### 4.7 Verify

- Backend health check: `https://<backend-url>/health`
- Frontend loads and can successfully call the backend (check browser
  network tab for CORS errors — see section 6)
- Create a test map end to end against the live Groq-backed deployment

## 5. Environment variables

| Variable | Local value | Railway value |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | `groq` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | unused in production |
| `OLLAMA_MODEL` | `llama3.1:8b` | unused in production |
| `GROQ_API_KEY` | unused locally | your Groq key, set as a Railway secret, never committed |
| `GROQ_MODEL` | unused locally | a current open-weight model on Groq's free tier — check console.groq.com for what's currently available, model names change as Groq updates its lineup |
| `DATABASE_URL` | from `docker-compose.yml` | auto-provided by Railway's Postgres plugin |
| `REDIS_URL` | from `docker-compose.yml`, optional | auto-provided by Railway's Redis plugin, optional |
| `PORT` | `8000` (fixed locally) | injected by Railway, don't hardcode |
| `CORS_ORIGINS` | `http://localhost:5173` | your frontend's Railway URL |

Keep a `.env.example` in the repo with these keys and placeholder values —
never commit a real `.env` with actual secrets.

## 6. CORS

Local dev and production both involve the frontend and backend living on
different origins (different ports locally, different Railway domains in
production), so FastAPI's CORS middleware needs the frontend's actual origin
in `CORS_ORIGINS`, read from the environment rather than hardcoded, so the
same code works in both environments without edits.

## 7. Staying within the $5/month Railway credit

- Don't run a self-hosted model on Railway (section 1's whole point)
- Postgres and Redis at low, single-user traffic volumes are cheap on
  Railway's usage-based pricing — the backend and frontend services are the
  main variable cost, and both are lightweight for a single-user app
- If you add a custom domain, that's typically free on Railway itself
  (you pay your domain registrar separately, not Railway)
- Check Railway's current usage dashboard regularly for the first month to
  see your actual cost pattern — pricing/limits are the kind of thing that
  changes over time, so trust Railway's live dashboard over any number
  written here

## 8. What NOT to do

- Don't commit `GROQ_API_KEY` or any secret to the repo, even in `.env.example`
  (use placeholder text like `your-key-here`)
- Don't point production at Ollama — there's no Ollama running on Railway
  unless you explicitly add a service for it, which section 1 argues against
- Don't skip the migration step on deploy — a backend running against an
  out-of-date schema fails in confusing ways
