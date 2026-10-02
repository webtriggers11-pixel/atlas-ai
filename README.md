# Idea Atlas

Open-source **document gap analysis**: upload the documents that describe what
*should* exist (requirements, specs, a job description) and the documents that
describe what *does* exist (design docs, API docs, a resume). Idea Atlas finds
every requirement, searches for evidence, and reports what is **covered,
partial, missing, conflicting or unclear**, with a link to the source sentence
for each finding.

> **Status:** V2 is under active development on the `v2` branch.
> The `v1-final` tag is the earlier topic-to-concept-map explorer, which still works.
> Plan: [`idea-atlas-docs/v2/V2_IMPROVED_PLAN.md`](idea-atlas-docs/v2/V2_IMPROVED_PLAN.md) ·
> Current state: [`idea-atlas-docs/v2/CURRENT_STATE.md`](idea-atlas-docs/v2/CURRENT_STATE.md)

## Stack

FastAPI · SQLAlchemy 2 · Pydantic v2 · PostgreSQL 16 + pgvector · Redis ·
React 18 + Vite + React Flow + Zustand + Tailwind · Docker Compose ·
LLMs: Ollama (local), Groq, Gemini · Embeddings: all-MiniLM-L6-v2 (local)

## Run locally

Requirements: Docker Desktop, plus one LLM option (Ollama running locally, or a
Groq or Gemini API key).

```bash
cp backend/.env.example backend/.env    # fill in a key or point at Ollama
docker compose up --build
```

| URL | What |
|---|---|
| http://localhost:5173 | frontend |
| http://localhost:8000/health | backend liveness |
| http://localhost:8000/health/ready | DB + pgvector readiness (expects `"status": "ready"`) |
| http://localhost:8000/docs | interactive API docs |

If you created the Postgres volume before pgvector was added, recreate it once:
`docker compose down -v && docker compose up --build` (this deletes local data).

## Tests

```bash
cd backend
pytest tests/test_health.py -v        # no database needed
pytest -v                             # needs a Postgres; use the local Docker one, never production
```

## Production (self-hosted Linux VPS)

`deploy.sh` builds `docker-compose.prod.yml`. Postgres runs outside Docker and
needs pgvector installed once on the database server:

```bash
sudo apt install postgresql-16-pgvector
sudo -u postgres psql -d atlas-ai -c "CREATE EXTENSION IF NOT EXISTS vector;"
curl https://<your-api-host>/health/ready
```

## Docs

- V2 product and technical docs: [`idea-atlas-docs/v2/`](idea-atlas-docs/v2/)
- Architecture decisions: [`idea-atlas-docs/adr/`](idea-atlas-docs/adr/)
