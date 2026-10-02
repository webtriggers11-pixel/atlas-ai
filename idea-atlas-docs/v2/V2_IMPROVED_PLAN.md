# Idea Atlas V2 — Improved Build Plan

This plan refines `idea_atlas_v2_docs` (PRD / TRD / ROADMAP / ARCHITECTURE /
DEVELOPMENT_RULES). Those docs stay the source of truth for principles; this
file changes **scope, phase order, and a few design decisions** so the product
solves a real user problem and every phase produces an interview story.

Legend: ⭐ = important change vs the original V2 docs.

---

## 1. Positioning

### ⭐ One primary use case, not "broad document analysis"

**Spec Coverage Analyzer** — "Does our technical documentation actually cover
our requirements, and where is the proof?"

- **Reference (expected):** SRS / BRD / PRD / acceptance criteria / RFP
- **Existing (actual):** SDD / API docs / design docs / proposal / test plan
- **Output:** a **requirements traceability matrix** — every requirement
  marked covered / partial / missing / conflict / unclear, with the exact
  source sentence as evidence.

Why this user is real: business analysts, QA leads, tech leads and pre-sales
teams build traceability matrices by hand in Excel today. It is slow, boring,
and errors (a missed requirement) are expensive.

Secondary preset (demo only): **Resume vs Job Description** — everyone
understands it in 5 seconds, so it's the best demo for recruiters. Same
pipeline, different prompts.

### What makes it different from "paste both docs into ChatGPT"

1. **Structured + persistent** — findings are rows in a database, not a chat reply.
2. **Verifiable** — every finding links to the exact chunk; evidence quotes are
   checked by code to really exist in the source (see §3.4).
3. **Repeatable** — re-run after documents change and see a **diff**
   (new gaps, resolved gaps).
4. **Measured** — an evaluation set proves how accurate it is.
5. **Private option** — runs fully local with Ollama.

---

## 2. Improved user flow

```text
1. Create project            "Payments API v2 review"   preset: Spec Coverage
2. Upload documents          left column: Reference     right column: Existing
3. Processing (background)   uploaded → processing → indexed   (live status)
4. ⭐ Review requirements     system extracts REQ-001..REQ-n, user edits /
                             merges / deletes / adds before analysis
5. Run analysis (background) progress bar: 37 / 120 requirements
6. Findings view             table + filter by status + evidence drawer
                             + coverage map (reuses v1 React Flow graph)
7. ⭐ Investigate             unclear / conflict rows → "Investigate" runs the
                             agent; user sees its step-by-step trace
8. ⭐ Ask                     "Which security requirements are missing?" —
                             tool-calling Q&A over the analysis
9. Export                    traceability matrix (CSV / Markdown / PDF)
10. ⭐ Re-analyze             upload new doc version → diff vs previous run
```

---

## 3. Key design decisions (the "important things")

### 3.1 ⭐ Human-in-the-loop requirement review
LLM requirement extraction from prose is unreliable (over-splitting, missed
items, background text treated as requirements). Instead of hoping it's
right, the user approves the list before analysis. Each requirement gets a
stable ID (`REQ-014`) and a content hash.
*Interview story:* "I designed for model failure instead of pretending it doesn't happen."

### 3.2 ⭐ Deterministic first, LLM second, agent last
```text
Stage 1  Retrieval (deterministic)     hybrid search → top-k evidence + scores
Stage 2  Classification (LLM, batched) 5–10 requirements per call, Pydantic-validated
Stage 3  Investigation (agent)         ONLY for unclear / conflict / low-confidence
```
Most requirements never touch the agent → cheaper, faster, predictable.
This is the honest answer to "why did you use an agent?".

### 3.3 ⭐ "Missing" needs proof of absence
A false "missing" destroys user trust. Before a requirement can be marked
`missing`:
- search with the original text **and** 2 LLM-rewritten queries
- use hybrid retrieval (keyword + vector)
- if the best score is in a grey zone → `unclear`, not `missing`

### 3.4 ⭐ Evidence verification (anti-hallucination guard)
The LLM must return evidence as `{chunk_id, quote}`. Backend code checks
the quote actually appears in that chunk (normalized / fuzzy match ≥ 0.9).
Fails → evidence dropped, finding downgraded to `unclear`, logged.
Deterministic code guarding generative output — strong interview point.

### 3.5 ⭐ Idempotency + caching via content hashes
- `document.content_hash` — same file uploaded twice is not re-processed
- finding cache key = `hash(requirement_text + evidence_chunk_ids + prompt_version + model)`
- re-analysis only calls the LLM for requirements whose inputs changed
→ makes re-analysis cheap and makes Celery retries safe.

### 3.6 Prompt-injection defence
Document text is untrusted data. Wrap it in delimiters, instruct the model
to never follow instructions inside it, validate all outputs by schema, and
the agent's tools are read-only. Include an injected document in the eval set.

### 3.7 Prompt versioning
Every prompt has a version string stored on each finding and in `llm_logs`,
so eval results are comparable across prompt changes.

---

## 4. Domain model

```text
Project(id, name, preset, created_at)
 ├─ Document(id, project_id, role[reference|existing], filename,
 │           content_hash, status, error, version)
 │    └─ Chunk(id, document_id, index, content, section, page,
 │             embedding vector(384), tsv tsvector)
 ├─ Requirement(id, project_id, code "REQ-014", text, source_chunk_id,
 │              status[draft|approved|deleted], content_hash)
 ├─ AnalysisRun(id, project_id, status, started_at, finished_at,
 │              prompt_version, model, stats_json)
 │    └─ Finding(id, run_id, requirement_id, status, confidence,
 │               explanation, suggested_action, cache_key)
 │         └─ Evidence(id, finding_id, chunk_id, quote, verified bool, score)
 ├─ AgentTrace(id, finding_id, steps_json, tool_calls, tokens, outcome)
 └─ LlmLog(id, provider, model, task, prompt_version, tokens_in,
           tokens_out, latency_ms, status)
```

Indexes: HNSW on `chunk.embedding`, GIN on `chunk.tsv`, FKs everywhere,
unique `(project_id, content_hash)` on documents.

---

## 5. Phase plan

Each phase ends with: tests passing, a "Done when" check, a short ADR if a
real decision was made, and interview Q&A.

### Phase 0 — Baseline & cleanup
- Tag current code `v1-final`, create branch `v2`
- Switch Postgres image to `pgvector/pgvector:pg16`
- Migrations: keep our custom system in `backend/migrations/` → **ADR-001**
- Remove/park v1-only code paths that V2 replaces (keep the graph UI)
- Real README describing current state

**Done when:** `docker compose up` works on `v2` branch, health check green, pgvector extension enabled.

### Phase 1 — Domain model + API
Project, Document (with role), Requirement, AnalysisRun, Finding, Evidence.
REST under `/api/v1`. Pydantic schemas, FK constraints, migration.

**Done when:** CRUD tests for projects/documents pass against real Postgres.
*Interview:* relational modelling, why Postgres + pgvector instead of a separate vector DB (ADR-002).

### Phase 2 — Ingestion pipeline with background jobs ⭐ (Celery moved earlier)
Upload validation (type, size, magic bytes), extraction (pdfplumber for
tables), normalization, chunking with page + section metadata,
document status lifecycle, content-hash dedupe, **Celery + Redis worker**.

Why earlier than the original roadmap: the status lifecycle
(uploaded → processing → indexed/failed) is part of the product from day
one; building it sync and migrating later is wasted work.

**Done when:** uploading a 50-page PDF returns immediately, status moves to `indexed`, a corrupt PDF ends in `failed` with a readable error, re-uploading the same file doesn't duplicate chunks.
*Interview:* queues, idempotency, at-least-once delivery, failure states.

### Phase 3 — Embeddings + pgvector retrieval
Embedding provider interface (local MiniLM default), vector column,
HNSW index, top-k search filtered by project + document role.

**Done when:** search query returns ranked chunks with scores from SQL, not numpy.
*Interview:* embeddings, cosine similarity, HNSW vs IVFFlat, why normalize vectors.

### Phase 4 — Requirement extraction + review UI ⭐
LLM extracts candidate requirements from reference docs (batched by
section, Pydantic-validated, each linked to its source chunk). UI to
edit / merge / delete / add / approve.

**Done when:** a real SRS produces a reviewable list; edits persist.

### Phase 5 — Gap analysis pipeline (core product)
Stage 1 + Stage 2 from §3.2, multi-query retrieval (§3.3), evidence
verification (§3.4), caching (§3.5), run progress, findings + evidence API,
findings table + evidence drawer UI.

**Done when:** a real SRS + SDD pair produces findings where every
non-missing finding has at least one verified evidence quote.
*Interview:* RAG, grounding, structured output, deterministic vs generative.

### Phase 6 — Evaluation harness ⭐ (do not skip)
Golden dataset: 3–5 hand-labelled document pairs (include one with a
prompt-injection attempt and one with tables). Script `make eval` reports:

| Metric | Meaning |
|---|---|
| Retrieval recall@5 | correct evidence chunk in top 5 |
| Status accuracy | predicted vs labelled status |
| False-missing rate | labelled covered, predicted missing (the trust killer) |
| Evidence validity | % of quotes that pass verification |
| Cost / latency | tokens + seconds per requirement |

Results saved per prompt_version + model so changes are compared.

**Done when:** baseline numbers recorded in `docs/EVAL_RESULTS.md`.

### Phase 7 — Retrieval improvements, proven by eval
Hybrid search (Postgres full-text + vector, combined with Reciprocal Rank
Fusion), query rewriting. Re-run eval; keep only what improves numbers.

**Done when:** before/after table in `EVAL_RESULTS.md`.
*This is your best resume line:* "improved recall@5 from X% to Y% with hybrid search" — with real measured numbers.

### Phase 8 — LLM reliability layer
Refactor `llm.py` into a provider interface (generate / generate_structured /
embed). Timeouts, retry with backoff only for idempotent calls, fallback
on 429/5xx, token + latency + cost logging per call, prompt versioning.
(Much of this exists already — this phase is cleanup + tests for failure paths.)

**Done when:** tests simulate timeout, 429, malformed JSON — each handled correctly.

### Phase 9 — Tool calling: "Ask your analysis" ⭐
Chat panel per project. The model can call **read-only** tools:

```text
search_documents(query, role?)        hybrid search over chunks
get_chunk(chunk_id)                   full chunk + neighbours
list_findings(status?, keyword?)      query findings table
get_requirement(code)                 requirement + its finding + evidence
```

Implementation: hand-written tool loop (≈100 lines) using provider-native
function calling (Groq / Gemini / Ollama llama3.1 all support tools).
Tool args validated by Pydantic, project_id injected server-side (the model
can never choose which project it reads → tenant safety), max 6 tool calls
per question, every answer cites chunk IDs.

**Done when:** "Which security requirements are missing?" answers correctly with citations; a question about another project's data is impossible by construction.
*Interview:* function calling, tool schemas, authorization in tools, loop limits.

### Phase 10 — Investigator agent ⭐ (agent only where it earns its place)
Triggered for findings that are `unclear`, `conflict`, or low confidence.
The agent plans its own searches (different phrasings, neighbouring chunks,
both documents), reasons over evidence, and returns a revised finding.

Guardrails:
- bounded: max 8 steps, token budget, timeout
- same read-only tools as Phase 9 + `compare_statements(a, b)`
- output passes the same Pydantic + evidence verification as Stage 2
- full trace stored in `AgentTrace` and shown in UI
- runs as a Celery task

Start with the hand-written loop; adopt LangGraph only if you need
checkpointing / resumable state → ADR-00X either way.

**Done when:** eval shows the agent resolves a measurable share of `unclear` findings correctly vs the Phase 5 pipeline alone (record the number, even if modest).
*Interview:* agents vs pipelines, state, bounded autonomy, evaluating agents.

### Phase 11 — Reports, re-analysis diff, coverage map
- Export traceability matrix: CSV, Markdown, PDF
- Re-analysis with new doc version → diff (newly missing / resolved / changed)
- Coverage map: v1 React Flow graph, requirements grouped by section,
  nodes coloured by status — click → evidence drawer

### Phase 12 — Security hardening
Upload checks (magic bytes, size, page limits), rate limiting, optional
JWT auth with per-user project isolation (off by default locally),
secrets only server-side, safe logging (no document text in logs).

### Phase 13 — CI/CD + production
GitHub Actions: lint, tests with a pgvector service container, eval smoke
test, Docker build. Deploy to Contabo via compose: health checks, restart
policies, nightly Postgres backup, reverse proxy + HTTPS.

### Phase 14 — Open-source + job-search polish
README with architecture diagram + GIF demo, `.env.example`, ADR folder,
`EVAL_RESULTS.md`, CONTRIBUTING, LICENSE, 2-minute demo video, live demo
link (resume vs JD preset, with sample docs so recruiters need no setup).

---

## 6. Dependencies

| Item | Needed | Cost | Notes |
|---|---|---|---|
| LLM: Groq key | one of these three | free tier | fast; needs a model with tool support for Phases 9–10 |
| LLM: Gemini key | one of these three | free tier | long context; free-tier data may be used by Google — not for confidential docs |
| LLM: Ollama | one of these three | free, local | private; 8B model needs ~8 GB RAM, slow on CPU |
| Embeddings | yes | free | local MiniLM (sentence-transformers) |
| Postgres + pgvector | yes | free | `pgvector/pgvector:pg16` image |
| Redis + Celery worker | yes (Phase 2+) | free | extra container |
| Contabo VPS | for live demo | existing | 8 GB RAM without Ollama, 16 GB with |
| Eval dataset | yes | your time | 3–5 labelled pairs |

---

## 7. Resume framing (fill numbers only after measuring)

> **Idea Atlas — Document Gap Analysis Platform** (FastAPI, PostgreSQL/pgvector, Celery, Redis, React, Docker)
> - Built an evidence-grounded RAG pipeline that maps requirement documents against technical documentation and produces a traceability matrix with verified source citations.
> - Designed hybrid retrieval (Postgres full-text + pgvector, RRF), improving recall@5 from __% to __% on a hand-labelled evaluation set.
> - Implemented a bounded tool-calling investigator agent for ambiguous findings, with full execution traces and schema-validated output.
> - Built async ingestion with Celery/Redis, content-hash idempotency and result caching, cutting re-analysis LLM calls by __%.
> - Multi-provider LLM layer (Groq / Gemini / Ollama) with fallback, retries, and per-call token/latency logging; deployed via Docker on a Linux VPS with CI.

Rule (from DEVELOPMENT_RULES §2): never write a number you didn't measure.
