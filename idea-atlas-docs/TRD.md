# TRD — Idea Atlas

Companion to `PRD.md`. This defines the technical stack, architecture, and
non-functional engineering requirements. See `BACKEND_SCHEMA.md` for the
database design and `APP_FLOW.md` for the request/response flow in detail.

## 1. Tech stack

| Layer | Choice | Why | License |
|---|---|---|---|
| Frontend framework | React 18 + Vite | Fast dev loop, you already know React | MIT |
| Graph UI | React Flow (`@xyflow/react`) | Purpose-built node/edge graph component — click, drag, zoom, expand built in | MIT |
| Frontend state | Zustand | Lighter than Redux, enough for single-user local state (selected node, depth, current map) | MIT |
| Styling | Tailwind CSS | Fast to build with, consistent spacing/type scale without writing custom CSS from scratch | MIT |
| Backend framework | FastAPI (Python 3.11+) | Async, auto-generated OpenAPI docs, you already know it from the labour-market project | MIT |
| ORM | SQLAlchemy 2.0 | Standard, well-documented, works cleanly with Postgres | MIT |
| Migrations | Alembic | Pairs with SQLAlchemy, versioned schema changes | MIT |
| Database | PostgreSQL 16 | Requested explicitly; also gives you real relational modeling practice and JSONB if you need flexible fields later | PostgreSQL License (permissive) |
| Local dev orchestration | Docker Compose | One command spins up Postgres + backend + frontend consistently | Apache 2.0 |
| AI / concept decomposition | Ollama running a local open-weight model (`llama3.1:8b` or `phi3:mini` for lighter hardware) | Fully local, no API key, no cost | Ollama: MIT. Models: open-weight licenses, check each card |
| Caching (optional, recommended) | Redis | Cache LLM responses for identical (topic, depth) requests so re-expanding a node doesn't always re-call the model | BSD-3 |
| Testing | pytest (backend), Vitest + React Testing Library (frontend) | Standard, free | MIT |
| CI | GitHub Actions | Free for public repos | — |

Everything in this stack is free and open source. Nothing requires a paid
account to develop or run locally.

## 2. High-level architecture

```
React + React Flow (frontend)
        │  HTTP/JSON
        ▼
FastAPI (backend)
        │
        ├──▶ Ollama (local LLM) — concept decomposition & explanations
        ├──▶ Redis (optional) — cache identical requests
        └──▶ PostgreSQL — persisted maps, nodes, explanations
```

The backend is the only thing that talks to Ollama and Postgres. The
frontend never calls the LLM directly — this keeps the API key/connection
logic, prompt templates, and validation in one place, and makes it trivial
to swap Ollama for a hosted model later (single file change, see
`app/llm.py`).

## 3. Backend service boundaries

- `app/api/` — FastAPI routes only. No business logic here, just request
  validation (Pydantic) and calling into `app/services/`.
- `app/services/atlas_service.py` — orchestrates: build prompt, call LLM,
  validate response shape, persist to DB, return to API layer.
- `app/llm.py` — the only file that knows about Ollama. Exposes a single
  function like `generate_concepts(topic: str, depth: str) -> list[Concept]`.
  Swapping the AI provider later means editing only this file.
- `app/db/` — SQLAlchemy models, session management, Alembic migrations.
- `app/schemas.py` — Pydantic request/response models, shared between API
  and service layer.

## 4. API endpoints (v1)

| Method | Path | Purpose |
|---|---|---|
| POST | `/maps` | Create a new map from a typed topic. Returns the map with its root node and first-level sub-concepts. |
| GET | `/maps` | List previously saved maps (id, topic, created_at) for the "recent maps" view. |
| GET | `/maps/{map_id}` | Load a full saved map (all nodes + edges) to reopen it. |
| POST | `/maps/{map_id}/nodes/{node_id}/expand` | Expand a node into its own sub-concepts. Persists new nodes/edges. |
| PATCH | `/maps/{map_id}/nodes/{node_id}/depth` | Re-explain a node at a different depth (gist/standard/expert). Returns cached explanation if it already exists, otherwise calls the LLM and caches it. |
| DELETE | `/maps/{map_id}` | Delete a saved map. |

Full request/response shapes belong in the OpenAPI docs FastAPI generates
automatically (`/docs`) once endpoints exist — don't hand-write a separate
spec, let the code be the source of truth.

## 5. LLM interaction contract

The backend must instruct the model to return **only valid JSON**, shaped
like:

```json
{
  "concepts": [
    { "label": "Attention mechanism", "summary": "..." },
    { "label": "Tokenization", "summary": "..." }
  ]
}
```

`app/llm.py` must read an `LLM_PROVIDER` environment variable (`ollama` for
local dev, `groq` for production) and instantiate the right client behind a
single shared interface — see `DEPLOYMENT.md` for why production doesn't use
Ollama. No other file in the codebase should branch on which provider is
active; if that happens, the abstraction has leaked.

Required engineering, because small/free-tier models don't reliably return
clean JSON every time:

- Use a strict system prompt with an explicit schema and one example
- Parse with a try/except around `json.loads`; on failure, retry once with
  a stricter "you must return only JSON, no prose" follow-up
- Validate the parsed result against a Pydantic model before trusting it
- Cap retries at 2 — if it still fails, return a clear error to the
  frontend rather than silently returning garbage

This retry/validation logic is one of the more interesting engineering
pieces of the whole project — budget real time for it.

## 6. Non-functional requirements

- All services runnable via a single `docker compose up`
- Backend must work without Redis (cache layer optional, not required) —
  design it so caching is a clean optional wrapper, not load-bearing
- Database migrations must be version-controlled via Alembic, never manual
  schema edits
- Tests should cover: API contract (status codes, shapes), the JSON
  validation/retry logic, and at least one full create-map → expand-node
  flow against a real (or mocked) Ollama response
