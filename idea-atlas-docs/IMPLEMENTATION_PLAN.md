# Implementation plan — Idea Atlas

Companion to all other docs in this set. Sequenced so each phase produces
something runnable and testable before moving to the next — don't skip
ahead to the frontend before the backend's core loop works against real
(or scripted) requests.

## Phase 0 — project setup

- [ ] Initialize repo with the structure below
- [ ] `docker-compose.yml` with Postgres + Redis (Redis optional but stub it in)
- [ ] Backend: FastAPI skeleton, health-check endpoint (`GET /health`)
- [ ] Frontend: Vite + React skeleton, single page that calls `/health` and
      shows "backend connected" — proves the two talk to each other before
      any real feature work starts
- [ ] Install Ollama locally, pull a model (`ollama pull llama3.1:8b` or
      `phi3:mini`), confirm `ollama run llama3.1:8b "hello"` works in a terminal

**Done when:** `docker compose up` runs Postgres + backend, frontend dev
server shows "backend connected," Ollama responds to a manual test prompt.

## Phase 1 — database layer

- [ ] SQLAlchemy models for `maps`, `nodes`, `node_explanations`, `edges`
      per `BACKEND_SCHEMA.md`
- [ ] Alembic initialized, first migration creates all four tables
- [ ] A simple script or test that creates a map + a few nodes directly via
      the ORM and reads them back, to confirm the schema works before any
      API or LLM logic touches it

**Done when:** you can create and query rows in all four tables without
errors, migrations run cleanly from scratch.

## Phase 2 — LLM integration (the core risky piece, build it first)

- [ ] `app/llm.py`: a function that takes a topic and returns a list of
      concept objects, calling Ollama's local API
- [ ] Strict prompt template instructing JSON-only output, with one example
      in the prompt
- [ ] Validation: parse the response, validate against a Pydantic model,
      retry once on failure with a stricter follow-up prompt, raise a clear
      error after 2 failed attempts
- [ ] A standalone script (not yet wired to the API) that calls this
      function with a few different topics and prints the result — eyeball
      the quality before building anything on top of it

**Done when:** running the script against 5-10 different topics reliably
produces valid, sensible JSON at least 90% of the time without manual fixes.
This is the phase most likely to take longer than expected — budget for it.

## Phase 3 — backend API

- [ ] `POST /maps` — wires Phase 1 (persistence) + Phase 2 (LLM) together:
      generate concepts, save map/nodes/edges, return the full map
- [ ] `GET /maps`, `GET /maps/{id}` — list and load
- [ ] `POST /maps/{id}/nodes/{node_id}/expand` — same generation logic,
      scoped to a parent node's context
- [ ] `PATCH /maps/{id}/nodes/{node_id}/depth` — check cache in
      `node_explanations` first, only call the LLM on a cache miss
- [ ] `DELETE /maps/{id}`
- [ ] pytest coverage: one full create -> expand -> change-depth flow,
      plus the JSON validation/retry logic in isolation

**Done when:** every endpoint in `TRD.md` works and is covered by at least
one test, verifiable via `/docs` (FastAPI's auto-generated Swagger UI)
without the frontend existing yet.

## Phase 4 — frontend skeleton + graph rendering

- [ ] Topic input component, calls `POST /maps`, shows loading state
- [ ] React Flow canvas, renders returned nodes/edges
- [ ] Center node styled distinctly per `UI_UX_BRIEF.md`
- [ ] Click a node -> side panel shows its current explanation

**Done when:** typing a topic in the browser produces a visible, correct
graph end to end, no mock data involved.

## Phase 5 — interactions

- [ ] Expand button on the side panel, wired to the expand endpoint, new
      nodes animate in
- [ ] Depth toggle, wired to the depth endpoint, panel updates in place
- [ ] Recent maps panel, wired to `GET /maps`, clicking loads a saved map
- [ ] Error states per `APP_FLOW.md` section 8 (Ollama not running,
      generation failure, etc.)
- [ ] Manual node dragging persists position on save

**Done when:** the full user journey in `APP_FLOW.md` works exactly as
described, including error cases.

## Phase 6 — polish and open-source readiness

- [ ] Light/dark mode
- [ ] README with setup instructions (Ollama install, model pull, docker
      compose up, in under 5 steps)
- [ ] GitHub Actions CI running backend tests on push
- [ ] LICENSE (MIT recommended, consistent with the stack)
- [ ] CONTRIBUTING.md
- [ ] A short demo gif or screen recording in the README

**Done when:** a stranger can clone the repo and have a working app
following only the README, with no extra context from you.

## Phase 7 — deferred features (only after Phase 6 is genuinely done)

- [ ] Document upload (PDF) as an alternate input type
- [ ] URL/article scraping as an alternate input type
- [ ] Video transcript ingestion (YouTube first, since transcripts are
      readily extractable)

Do not start Phase 7 early. Each of these is genuinely easier once the core
map-generation engine already exists and is solid — resist the urge to
build all input types in parallel.

## Repo structure reference

```
idea-atlas/
  backend/
    app/
      api/              FastAPI routes
      services/         business logic (atlas_service.py)
      db/               SQLAlchemy models, session, Alembic migrations
      llm.py            the only file that talks to Ollama
      schemas.py        Pydantic models
      main.py           FastAPI app entrypoint
    tests/
    requirements.txt
    alembic.ini
  frontend/
    src/
      components/       AtlasGraph.jsx, DepthPanel.jsx, RecentMaps.jsx, TopicInput.jsx
      store/             Zustand store
      App.jsx
    package.json
  docker-compose.yml
  README.md
  LICENSE
  CONTRIBUTING.md
  .github/workflows/ci.yml
```
