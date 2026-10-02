# Current State — baseline before V2 (tag `v1-final`)

Snapshot of what exists at commit `f783066`, recorded in V2 Phase 0 so later
phases change things deliberately rather than by accident.

## What the app does today

1. **Topic maps (v1 core, wired to the UI):** type a topic → LLM returns 6–8
   sub-concepts → React Flow graph → click to expand a node → switch a node's
   explanation between gist / standard / expert → maps saved in Postgres.
2. **Document maps (backend only, not in the UI):** upload .docx/.pdf/.txt/.md
   or pasted text → 500-word chunks with 50-word overlap → local MiniLM
   embeddings → LLM builds a concept hierarchy grounded in the document.
3. **Single-document gap check (backend only):** nodes whose best chunk
   similarity is below `GAP_THRESHOLD` (0.35) get LLM-written developer
   questions; answers are embedded back into the document.

## API

| Method | Path | Purpose | Used by UI |
|---|---|---|---|
| GET | `/health` | liveness | yes |
| GET | `/health/ready` | DB + pgvector readiness (added in Phase 0) | no |
| POST | `/maps` | create topic map | yes |
| GET | `/maps` | list maps | yes |
| GET | `/maps/{id}` | load map | yes |
| DELETE | `/maps/{id}` | delete map | yes |
| POST | `/maps/{id}/nodes/{node_id}/expand` | expand node | yes |
| PATCH | `/maps/{id}/nodes/{node_id}/depth` | change explanation depth | yes |
| PATCH | `/maps/{id}/nodes/{node_id}/read` | mark node read | no |
| POST | `/maps/{id}/gap-check` | run gap check on a document map | no |
| GET | `/maps/{id}/gaps` | list gap questions | no |
| POST | `/documents` | upload document → grounded map | no |
| PATCH | `/gaps/{gap_id}` | answer a gap question | no |

## Data model (`backend/app/models/`)

`maps`, `nodes`, `edges`, `node_explanations`, `documents`, `document_chunks`
(embedding stored as a float array, not pgvector), `node_gaps`, `llm_logs`,
plus `schema_migrations` from the custom migrator.

## LLM layer (`backend/app/llm.py`)

- Providers: Ollama, Groq, Gemini; `pick_provider()` routes by task type.
- Fallback Groq ↔ Gemini on rate limits; calls logged to `llm_logs`.
- JSON-only prompts with a few-shot example, `_extract_json` + Pydantic
  validation, one stricter retry, then HTTP error.

## Infrastructure

- **Local:** `docker-compose.yml` — Postgres (now `pgvector/pgvector:pg16`),
  Redis, backend, frontend.
- **Production:** `docker-compose.prod.yml` + `deploy.sh` on a Linux VPS
  (Contabo) — Redis, backend, frontend containers. **Postgres is external**:
  a native PostgreSQL 16.15 on Ubuntu, reached via `DATABASE_URL`.

## Known issues to address in V2

| Issue | Where | Planned fix |
|---|---|---|
| pgvector **not available** on production Postgres (checked 2026-10-02: not in `pg_available_extensions`) | prod DB server | install `postgresql-16-pgvector`, then `CREATE EXTENSION vector` (see README) |
| Vector search done in numpy by loading every chunk | `document_service.retrieve_chunks` | Phase 3: pgvector + HNSW |
| Custom migrator needs pgvector support (extension, `vector` type, HNSW/GIN indexes); can auto-`DROP COLUMN`; generated SQL not in git | `backend/migrations/` | ADR-001 → extend in Phase 1 |
| `AUTO_MIGRATE=true` in production env | server `backend/.env` | set to `false` now |
| Local `backend/.env` points at the **production** DB; `tests/test_api.py` and `tests/test_db.py` connect to whatever `DATABASE_URL` is | `backend/.env`, tests | Phase 1: dedicated test database; until then run DB tests only against local Docker Postgres |
| Redis runs but is unused | compose files | Phase 2: Celery broker |
| CORS is `*` | `main.py` | Phase 12 |
| No root README / `.env.example` | repo root | added in Phase 0 |

## Parked, not deleted

V1 topic maps and the document-map endpoints stay working on the `v2`
branch. They are removed or reshaped only when a V2 phase replaces them
(the React Flow graph is reused as the coverage map in Phase 11).
