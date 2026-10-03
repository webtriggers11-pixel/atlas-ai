# V2 Build Log — what was built, why, and interview prep

One section per phase. Each has: what was built, key decisions, how it was
verified (real test output), and interview questions to study.

---

## Phase 0 — Baseline

**Built:** tag `v1-final`, branch `v2`, pgvector Postgres image for local
compose, `GET /health/ready` (DB + pgvector check), V2 docs + ADR-001
(keep our own migration system), README, `.env.example`.

**Verified:** `tests/test_health.py` — 4 passed (DB mocked).

**Interview**

Q: Liveness vs readiness check?
A: Liveness = "is the process alive" (restart it if not). Readiness = "can it serve traffic right now" — dependencies such as the DB and the pgvector extension are available (stop routing traffic if not). `/health` vs `/health/ready`.

Q: Why pgvector instead of Pinecone/Weaviate?
A: Embeddings live next to the relational data they describe (projects, documents, findings), so one query can join, filter and rank, with transactions. At our scale an HNSW index in Postgres is fast enough and it's one less service to run and secure.

---

## Phase 1 — Domain model + API

**Built**
- **Migration system extended** (`backend/migrations/`):
  - foreign keys are now created (`REFERENCES … ON DELETE CASCADE`) — before
    this the production DB had **zero** FK constraints;
  - new tables are created parent-first (`metadata.sorted_tables`) so FKs resolve;
  - indexes of new tables are created in the same migration (previously they
    were only created on the *next* startup);
  - `UNIQUE`, `USING hnsw|gin`, operator classes (`vector_cosine_ops`);
  - `CREATE EXTENSION` driven by `Base.metadata.info["required_extensions"]`;
  - `VECTOR(n)` type and `GENERATED ALWAYS AS (...) STORED` columns;
  - `DROP COLUMN` is no longer generated unless `MIGRATIONS_ALLOW_DROPS=true`;
  - **bug fix:** reflected `TIMESTAMPTZ` columns compared as `TIMESTAMP`, so every
    run generated an ALTER for every timestamp column (production has 6 such
    auto-migrations). Now a second run reports "No schema changes detected";
  - `migrations/migrate.py` CLI fixed (it imported modules that don't exist).
- **New tables** (V2 only adds tables; v1 tables untouched so the live v1 app
  with `AUTO_MIGRATE=true` can't fight over them):
  `projects`, `project_documents`, `doc_chunks`, `requirements`,
  `analysis_runs`, `findings`, `evidence`.
- **API** under `/api/v1`: projects CRUD with counts; documents list/get/chunks/
  delete; requirements list/create/edit/approve-all/merge; runs and findings
  with evidence.
- **Test safety:** `tests/conftest.py` points all tests at `atlas-ai-test` and
  aborts if the DB name doesn't end in `-test`. Each test runs inside a
  transaction that is rolled back (`join_transaction_mode="create_savepoint"`),
  even when the code under test calls `commit()`.

**Key decisions**
- Status columns are `TEXT` + `CHECK` constraint (same pattern as v1), not
  Postgres ENUM types — adding a value to a CHECK is one statement; changing a
  PG enum is awkward in migrations.
- Files are stored at `<project_id>/<document_id>.<ext>` — the user's filename
  is never part of a path (path-traversal safe).
- Requirement `content_hash` = sha256 of normalized text, so cosmetic edits
  (spacing/case) don't invalidate cached analysis later.

**Verified:** 27 passed (migrator unit tests, projects API, health, v1 API).

**Interview**

Q: Why put foreign keys in the database when the ORM already has relationships?
A: ORM cascades only run when deletes go through the ORM. A database FK is enforced for every writer — raw SQL, scripts, another service — and `ON DELETE CASCADE` happens atomically in the DB. We found the existing DB had no FKs at all, so orphan rows were possible.

Q: How do you test code that commits without leaving data behind?
A: Open a connection, begin an outer transaction, bind the session with `join_transaction_mode="create_savepoint"` so the code's `commit()` only releases a savepoint, then roll back the outer transaction after the test. Each test sees a clean database and nothing persists.

Q: How does a schema-diff migration system work and what's dangerous about it?
A: It reflects the live schema (information_schema), compares it with the model metadata, and generates DDL for the differences in a safe order (extensions → tables parent-first → columns → indexes). The danger is that a rename looks like "drop + add", which deletes data — so drops must be opt-in and reviewed.

---

## Phase 2 — Ingestion pipeline with background jobs

**Built**
- `POST /api/v1/projects/{id}/documents` (file or pasted text, `role` = reference|existing),
  `POST /api/v1/documents/{id}/reprocess`.
- **Validation** (`services/extraction.py`): extension allow-list + **magic bytes**
  (`%PDF-`, `PK\x03\x04`), UTF-8 check, size limit, PDF page limit.
- **Extraction**: PDF via pdfplumber — body text *outside* tables plus tables
  rendered as `a | b | c` rows, page numbers kept; DOCX walked in body order
  (headings → `## `, tables → rows); TXT/MD.
- **Normalization**: NFKC, de-hyphenation across line breaks, and removal of
  running headers/footers (lines repeated on > half the pages, digits
  normalized so "Page 3 of 10" is caught).
- **Chunking** (`services/chunking.py`): sentence-aware, ~180 words, whole-sentence
  overlap, a new chunk at every section change, page range per chunk.
- **Celery** (`app/worker.py`, `app/tasks.py`): `acks_late`, `reject_on_worker_lost`,
  prefetch 1, retry with backoff only for transient DB errors.
- **Idempotency**: sha256 content hash → same file twice returns the existing
  document (HTTP 200); processing deletes-then-inserts chunks so a redelivered
  task never duplicates them; an already-indexed document is skipped.
- Compose: `worker` service; prod gets an `uploads_data` volume shared by API + worker.
- **v1 bug found by the new FKs**: deleting a map deleted nodes before the edges
  pointing at them. Fixed with Edge→Node relationships (ORM orders the deletes)
  plus `ON DELETE CASCADE` for fresh installs.

**Key decisions**
- *Why ~180-word chunks?* all-MiniLM-L6-v2 truncates input at 256 tokens. v1
  used 500-word chunks, so roughly the last 60% of every chunk was never embedded
  and could never be found by search.
- *Why status in Postgres instead of a Celery result backend?* The UI needs
  document status anyway, it survives Redis restarts, and it's queryable.
- *What if Redis is down at upload time?* The upload still succeeds; the
  document stays `uploaded` with a message and can be re-queued with Reprocess.

**Verified:** 47 passed (20 new ingestion tests: validation matrix, real PDF/DOCX
built in memory, header/footer removal, tables, chunk sizes/sections/pages,
duplicate upload, corrupt PDF → failed, reprocess idempotency).

**Interview**

Q: What does "at-least-once delivery" mean and how did you design for it?
A: With `acks_late`, a task is acknowledged only after it finishes, so if a worker dies mid-task the broker redelivers it — a task can run twice. So processing is idempotent: it skips already-indexed documents and replaces chunks (delete + insert in one transaction) instead of appending.

Q: Why check magic bytes and not just the file extension?
A: The extension is user-controlled; anyone can rename an executable to `.pdf`. Checking the first bytes (`%PDF-`, the ZIP header for DOCX) makes sure we only hand real PDFs/DOCX files to the parsers, which reduces parser-exploit risk and gives clear errors.

Q: How did you choose a chunk size?
A: From the embedding model's limit: MiniLM reads 256 tokens, about 190 words, and silently truncates the rest. So chunks are ~180 words, split on sentence boundaries so quotes stay intact, with a small sentence overlap and a hard break at section changes so each chunk's section label is accurate.

---

## Phase 3 — Embeddings + pgvector retrieval

**Built**
- pgvector 0.6.0 installed on the server and enabled in `atlas-ai` and
  `atlas-ai-test`; `/health/ready` → `{"status": "ready", "pgvector": "0.6.0"}`.
- `Base.metadata.info["required_extensions"] = ["vector"]` — our migrator now
  creates the extension itself on a fresh database.
- `doc_chunks.embedding VECTOR(384)` + **HNSW index** with `vector_cosine_ops`.
- **Embedding provider interface** (`services/embedding_service.py`):
  `local` = all-MiniLM-L6-v2 on CPU, `fake` = deterministic hashed bag-of-words
  for tests. v1 callers (`embed_text/embed_texts`) work unchanged.
- Chunks are embedded during ingestion with the section title prepended
  (`"Authentication: Access tokens are…"`) so a chunk carries its context.
- `services/retrieval.py`: `vector_search()` — `ORDER BY embedding <=> :q LIMIT k`
  in SQL, filtered by project, role, indexed status; `SET LOCAL hnsw.ef_search`.
- `POST /api/v1/projects/{id}/search` — also a retrieval-debugging tool.

**Key decisions**
- *Cosine distance with normalized vectors* — for unit vectors cosine and dot
  product rank identically; cosine ops make the intent explicit.
- *HNSW over IVFFlat* — HNSW needs no training step (IVFFlat must be built after
  data exists to pick its lists), gives better recall/speed, and handles inserts
  well. Trade-off: slower to build and more memory.
- *Filtered ANN caveat* — HNSW finds `ef_search` candidates and THEN applies the
  WHERE filter, so a selective filter can return fewer than k rows. We raise
  `ef_search` to 100 per query.

**Verified:** 54 passed — embeddings stored (384 dims, none NULL), ranking,
role/project isolation, HNSW index used in the query plan, migrator idempotent
with the vector column. Manual check with the real MiniLM model: the query "How
long is a session credential valid?" ranks "Access tokens … expire after fifteen
minutes" first (0.477 vs 0.335/0.305) with no shared keywords.

**Interview**

Q: What is an embedding and why does semantic search beat keyword search here?
A: An embedding is a vector where texts with similar meaning land close together. "Session credential validity" and "access tokens expire after 15 minutes" share no words, so keyword search misses it, but their vectors are close. Requirements and design docs routinely describe the same thing in different words.

Q: HNSW vs IVFFlat?
A: Both are approximate nearest-neighbour indexes. IVFFlat clusters vectors into lists and only searches the nearest lists — fast to build but it needs data to train on and recall depends on `probes`. HNSW builds a layered proximity graph — better speed/recall and no training, at the cost of build time and memory. I chose HNSW because documents arrive incrementally.

Q: Any gotcha with filtering + vector indexes?
A: Yes — the index returns its top candidates first and the WHERE clause filters afterwards, so a selective filter (one project out of many) can leave fewer than k results. Mitigations: raise `hnsw.ef_search`, partition/partial indexes per tenant, or iterative index scans (pgvector 0.8+).

---

## Phase 4 — Requirement extraction + review

**Built**
- `llm.py` (still the only file that talks to LLMs):
  - provider calls accept `max_tokens` and **JSON mode** (`response_format`
    json_object on Groq, `responseMimeType` on Gemini, `format: json` on Ollama);
    `reasoning_effort=low` for gpt-oss models (reasoning tokens count against max_tokens);
  - `_structured_call()` — JSON mode → `_extract_json` → Pydantic validation →
    one retry that tells the model the *exact* validation error → `LLMOutputError`;
  - `extract_requirements()` with preset-specific rules (spec vs job description),
    a few-shot example, and the untrusted-data note against prompt injection;
  - `PROMPT_VERSIONS` so results/evals are tied to the prompt that produced them.
- `services/extraction_job.py`: chunks → overlap removed → ~1200-word batches
  with `<section title=…>` tags → LLM per batch → dedupe (normalized-text hash +
  cosine ≥ 0.93) → each requirement linked to its most similar source chunk →
  drafts `REQ-001…`. Partial failure (some batches bad) still completes with a
  warning; total failure ends `failed` with a readable message.
- Re-running replaces only unreviewed extracted drafts; approved, rejected and
  manual requirements are kept and new extractions are deduplicated against them.
- `POST /api/v1/projects/{id}/requirements/extract` (202, Celery task) +
  `extraction_status / extraction_error / extracted_at` on the project.

**Verified:** 62 passed (mocked LLM: batching, overlap removal, dedupe, source
linking, re-run safety, failure path, retry-with-feedback, prompt-injection note).
Live run against the real model on a sample spec: 6 atomic requirements, every
number preserved, background text skipped, an embedded "Ignore all previous
instructions…" line ignored; Gemini was rate-limited and the call fell back to
Groq automatically.

**Interview**

Q: Why do small/free models need JSON mode, validation AND a retry?
A: They often wrap JSON in prose, truncate it, or drift from the schema. JSON mode constrains decoding, Pydantic catches schema errors (wrong keys, too-short text), and one retry that quotes the exact error usually fixes it. After two failures we raise a typed error so the job degrades (partial results + a warning) instead of crashing.

Q: How do you defend against prompt injection in uploaded documents?
A: Layers: document text is wrapped in tags and the system prompt says it's untrusted data; outputs must match a strict schema so an injected instruction can't make the model do anything but fill fields; the model has no write access (code decides what's stored); and an injected document is part of the evaluation set. No single layer is perfect, so it's defence in depth.

Q: Why a human review step instead of trusting extraction?
A: Extraction is the step where model errors compound — a missed requirement can never be reported as missing. Letting the user edit/merge/approve the list is cheap and makes every later number trustworthy. Reviewed items are never overwritten by a re-run.

---

## Phase 5 — Gap analysis pipeline (core product)

**Built**
- `POST /api/v1/projects/{id}/analyze` → queued `AnalysisRun` → Celery task.
- `services/analysis_service.py`:
  1. **Retrieval** — top-k (`EVIDENCE_K=4`) chunks from *existing* documents per requirement.
  2. **Cache** — key = sha256(requirement hash + evidence chunk ids + prompt version
     + model + preset). Same key in an earlier completed run → finding copied
     (`source="cache"`), no LLM call.
  3. **Classification** — `llm.classify_requirements`, `ANALYSIS_BATCH_SIZE=4`
     requirements per call sharing a de-duplicated excerpt list `[C1]…`, strict
     schema (status enum, confidence 0–1, evidence = `{chunk, quote}`).
  4. **Guardrails** (deterministic):
     - every quote is checked against its chunk by `services/evidence_verifier.py`
       (exact after normalization, else ≥ 90 % fuzzy over word windows); the stored
       quote is the *source* span, never the model's wording;
     - covered/partial/conflict with no verified evidence → `unclear`;
     - `missing` while retrieval found similar text (≥ `MISSING_GUARD_SCORE`) → `unclear`.
  5. Progress committed after every batch (`processed / total`), stats stored
     on the run (counts, cache hits, LLM calls, dropped evidence, errors, duration).
- Failure handling: a bad batch turns only its requirements into `unclear` with
  the reason; if *every* requirement fails the run is `failed` with a message;
  a redelivered task clears partial findings and restarts (idempotent).

**Verified:** 71 passed — verifier (exact, normalized, fuzzy, inventions rejected),
guardrails (invented quote → dropped + downgraded), missing-guard, cache (2nd run
0 LLM calls; editing 1 requirement → exactly 1 re-classification), partial and
total LLM failure, preconditions, prompt contents.

*Incident during this phase:* one full test run hung on a stale DB lock left by an
interrupted run. The test engine now sets `lock_timeout=30s` and
`statement_timeout=120s` so a blocked test fails fast with an error.

**Interview**

Q: How do you stop the LLM from hallucinating evidence?
A: The model must cite an excerpt label and quote it verbatim; code then searches that chunk for the quote (exact, then 90 % fuzzy). Unverifiable quotes are dropped, and a "covered" verdict with no surviving evidence is downgraded to "unclear". The UI only ever shows text copied from the source document.

Q: Why batch several requirements per LLM call?
A: Fewer calls (free-tier request limits), and requirements in the same area share excerpts, so the de-duplicated excerpt list costs fewer tokens than separate calls. Trade-off: a bad response affects the whole batch, so failures are isolated per batch and recorded per requirement.

Q: How does the cache stay correct?
A: The key hashes every input that can change the answer — normalized requirement text, the exact evidence chunks, prompt version, model and preset. Change any of them and the key changes, so stale results are never reused; nothing else needs invalidation logic.

---

## Phase 6 — Evaluation harness

**Built**
- `backend/eval/datasets/` — 3 hand-labelled pairs, 32 requirements: payments API spec vs
  design doc, clinic portal spec vs design, job description vs resume. Built to be hard:
  paraphrases and unit conversion (900 seconds = 15 minutes), evidence inside a table, exact
  identifiers (PF-1042), conflicts, "missing" requirements sitting next to related text
  (TLS vs at-rest encryption, uploads without malware scanning), abbreviations (B.E.), and a
  prompt-injection line.
- `python -m eval.run_eval --label <name> [--retrieval-only]` — runs the real pipeline (real
  embeddings, real LLM) in the TEST database, deletes its projects afterwards, saves full JSON to
  `eval/results/` and appends a row to `idea-atlas-docs/v2/EVAL_RESULTS.md`.
- Metrics: recall@1, recall@k, MRR, status accuracy, confusion matrix, false-missing rate,
  false-covered rate, unclear rate, evidence validity, evidence location, LLM calls, seconds/requirement.

**Results (baseline):** recall@1 92%, status accuracy 72% (88% on the requirements not hit by
rate limits), false-missing 8%, false-covered 0%, evidence validity 100%. See EVAL_RESULTS.md.

**What the eval taught us (→ next phases):** most errors were HTTP 429 from both free tiers (→
backoff/retry in Phase 8); the model says "missing" when related-but-incomplete or contradicting
text exists (→ prompt rule in Phase 8).

**Interview**

Q: How do you evaluate a RAG system?
A: Separately for each stage. Retrieval: is the labelled evidence in the top-k (recall@k, MRR)? Generation: is the verdict right (accuracy, confusion matrix) and is it grounded (are quotes real, do they point at the right passage)? Plus the business metric that matters most — here the false-missing rate — and cost/latency. Keep a fixed labelled set and compare every change against it.

Q: Your accuracy was 72% — is that bad?
A: Breaking errors down mattered more than the headline: 6 of 9 were rate-limit failures, not wrong answers. Without per-error analysis I'd have tuned prompts to fix an infrastructure problem.

---

## Phase 7 — Hybrid retrieval + query rewriting (measured, not adopted by default)

**Built**
- `doc_chunks.tsv` — `TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', section || content)) STORED`
  + GIN index (our migrator now emits generated columns).
- `keyword_search()` — `plainto_tsquery` with `&` rewritten to `|` (OR), ranked by `ts_rank_cd`.
- `hybrid_search()` — Reciprocal Rank Fusion of vector and keyword lists for one or more phrasings;
  `score` stays cosine similarity so the missing-guard threshold keeps its meaning.
- `llm.rewrite_queries()` — batched alternative phrasings, only for requirements whose best
  similarity is below `REWRITE_BELOW_SCORE`.
- `retrieve_for_requirements()` — one retrieval function shared by the pipeline and the eval.
- Search API `mode: vector | hybrid`.

**Result:** neither beat plain vector search on our set (recall@1 92% → 88% → 85%). Defaults stay
vector / no rewriting; the code stays, switchable by config, with the evidence documented.

**Also in this phase:** DB connection safety after an orphaned "idle in transaction" session
(left by a killed test process) blocked a migration: app connections now use
`idle_in_transaction_session_timeout=10min` + TCP keepalives + `pool_pre_ping`; migrations use
`lock_timeout=10s`; test connections have short lock/statement/idle timeouts.

**Verified:** 78 passed (tsvector generated + GIN index, keyword search on identifiers, RRF
ordering and score scale, extra phrasings changing the ranking, rewriting only for weak matches,
vector mode unchanged, API mode switch).

**Interview**

Q: You built hybrid search and then didn't use it — why?
A: Because the evaluation said so. On my labelled set hybrid lowered recall@1 from 92% to 88% and rewriting lowered it further. I kept it behind a config flag and documented why. I deliberately didn't tune weights on the same small set I report on — that would overfit to the test set and the numbers would stop meaning anything.

Q: What is Reciprocal Rank Fusion and why use it?
A: Each ranked list gives a document 1/(k + rank) and the scores are summed (k ≈ 60). It uses only ranks, so you can fuse BM25-style scores and cosine similarities without calibrating them against each other, and documents that rank well in several lists rise to the top.

Q: Why can a waiting ALTER TABLE take down an app?
A: It needs an exclusive lock, and while it waits in the lock queue every later query on that table queues behind it — reads included. A `lock_timeout` makes the migration fail fast instead; plus `idle_in_transaction_session_timeout` so dead clients can't hold locks for hours.

---

## Phase 8 — LLM reliability (+ fixes found by testing a real CV)

**Built**
- **Typed provider errors** (`llm.py`): `RateLimited` (429/503, carries the provider's
  `retry-after` / Gemini `retryDelay`), `ProviderUnavailable` (timeouts, connection errors,
  5xx), and everything else (400/401) raised immediately — retrying can't fix a bad request.
- **Cooldown per provider** (a small circuit breaker): a provider that says 429 is skipped
  until its retry-after passes; the other provider is tried at once; when *all* are cooling,
  wait (with jitter, capped) inside a **retry budget** — 20 s for interactive requests,
  150 s for background jobs — then a clear 429/503.
- **Structured-output fallback**: invalid JSON → retry with the exact validation error →
  then a fresh attempt on the *other* provider → `LLMOutputError`. Every invalid output is
  logged with its raw text (`llm_calls.status = invalid_output`) so failures can be diagnosed.
- **`llm_calls` table** — provider, model, task, prompt version, status, attempt, latency,
  prompt/completion tokens, error, and a job tag (`run:<id>`, `extract:<id>`) set with a
  `contextvar`; each analysis run's stats now include its tokens and provider attempts.
- **Classification prompt v2** — an ordered decision list (conflict → covered → partial →
  missing → unclear) and an explicit "never answer missing when an excerpt discusses the same
  feature" rule. Written from the error analysis, kept generic (no examples copied from the
  eval set). v1 stays selectable (`CLASSIFY_PROMPT`) for comparison.
- **Ingestion fixes found by an end-to-end run on a real CV PDF** (`eval/smoke_run.py`):
  - the heading heuristic treated a wrapped line ("Vercel, Apache Kafka (Basic)") as a title,
    and heading lines were dropped from content → "Kafka" vanished from the document.
    Heading text is now *also kept as content* (a misfire can't lose text) and comma-lists,
    bullets and `;` clauses are never headings;
  - pdfplumber's `(cid:127)` bullet placeholders are stripped.
- Tried and rejected by measurement: stripping requirement boilerplate from search queries
  ("Candidate has experience with …") lowered recall@1 92% → 88% → off by default.

**How the numbers moved** (32 labelled requirements, same datasets):

| Change | Status acc. | False-missing | Unclear | Recall@4 |
|---|---|---|---|---|
| Phase 6 baseline | 72% | 8%* | 19% | 96% |
| + backoff/cooldowns (prompt v1) | 78% | 23% | 0% | 96% |
| + prompt v2 | 72% | 12% | 12.5% (one bad-JSON batch) | 96% |
| + provider fallback on invalid output | 84% | 12% | 0% | 96% |

\* low only because 6 requirements were never classified (rate-limited) in the baseline.

**Interview**

Q: How do you handle LLM provider rate limits?
A: Treat them as typed, retryable errors that carry the provider's retry-after. Put that provider on a cooldown (a tiny circuit breaker) so we stop hammering it, fail over to the other provider immediately, and only sleep when every provider is cooling — with jitter and inside a time budget that differs for interactive vs background work. Non-transient errors (400/401) are never retried.

Q: Your prompt change made accuracy go DOWN (78% → 72%) — why keep it?
A: Because the drop wasn't the prompt: one batch returned malformed JSON, which made 4 requirements "unclear". Separating "wrong answer" from "no answer" showed v2 halved the false-missing rate. The real fix was in the reliability layer (retry on the other provider), after which accuracy reached 84%. Breaking errors down by cause beats reading the headline number.

Q: What did testing on a real document teach you that the synthetic eval didn't?
A: Synthetic markdown never exercised PDF layout. A real CV showed that a heuristic (heading detection) could silently delete content, so the design changed from "decide and discard" to "decide but never discard". Real inputs belong in testing even when they can't go into the committed dataset.

**Phase 8 — later runs and two more structured-output failure modes**

| Run | Status acc. | False-missing | Unclear | Recall@4 |
|---|---|---|---|---|
| + heading fix (recall@4 96% → 100%, MRR 0.94 → 0.95) — run "phase8-final" | 78% | 8% | 12.5% | 100% |

That run lost a batch to two failure modes not seen before, both now handled:
- Groq's JSON mode itself rejected a generation (HTTP 400 `json_validate_failed`). It was
  treated as a non-retryable bad request; it is now a `BadGeneration` → no cooldown, but the
  other provider is preferred for the rest of that call.
- Gemini returned a `results` list with one non-object item, which invalidated all 4 results.
  Results are now validated item by item; requirements without a valid result are recorded
  individually as "no result".

**Variance:** the same configuration scored 84% and 78% on consecutive runs (different LLM
output and rate-limit paths each time). On 32 requirements a ±6-point swing is noise —
compare configurations over several runs before claiming a difference.

**Real CV end-to-end (local only, not committed):** 15 requirements extracted from a job
description, all quotes verified, 72 s. After the fixes: Kafka found (listed under "Additional"),
"Feature Lead" counted for leadership, AWS → partial (S3 only), pytest → missing (true — the CV
doesn't mention testing). Remaining limitation: the explanation *prose* is not verified (one run
said "including OpenAI" next to a correct, verified quote) — guardrails cover quotes, not prose.

**Verified:** 93 passed.

**Phase 8 confirmation run** (after the BadGeneration + item-level parsing fixes): status accuracy
78%, false-missing 8%, false-covered 0%, unclear 3% (was 12.5%), recall@4 100%.

---

## UI revamp (V2 frontend) — first version

**Built** (React 18 + Vite, no Next.js; design language ported from the WebTriggers 2.0 site):
- Tailwind v4 (`@tailwindcss/vite`), theme tokens in `src/config/theme.js` (NeoPOP palette,
  light/dark, sharp shape) injected as CSS variables; plunk buttons, grid/glow backgrounds,
  Geist / Geist Mono / Instrument Serif.
- React Router pages: Projects (`/`), Project workspace (`/projects/:id?step=`), Explore (`/explore`,
  the v1 topic explorer, lazy-loaded and kept working).
- TanStack Query for server state with **conditional polling** (only while a document is
  processing, extraction is running or a run is active).
- Workspace steps: ① Documents (drag-drop / paste, live status, reprocess, chunk viewer)
  ② Requirements (AI extract, inline edit, approve/reject, approve-all, merge, add)
  ③ Analysis (run + progress, run history, coverage bar + status tiles as filters, search,
  CSV export, evidence drawer with verified quotes) and a Search tab (retrieval inspector).

**Verified in the browser** against a local API on the test DB: create project → upload →
chunks viewer → AI extraction (12 requirements) → approve all → analysis (5 covered, 1 partial,
3 missing, 3 conflict) → evidence drawer → light mode → Explore page. Bug found and fixed:
with inline (eager) jobs the extract request returns after extraction finished, so the
"running → finished" refresh never fired — the list is now also refreshed on return.

**Open:** `idea-atlas-docs/v2/Idea_Atlas_V2_UI_Spec.md` (added later) asks for a sidebar layout,
global Documents and Settings pages, analysis tabs (Findings / Evidence / Documents / Map), and a
light, purple-accent, low-animation style — which differs from the WebTriggers style requested
in chat. Direction to be confirmed before the next UI iteration.

---

## UI iteration 2 — UI spec layout + WebTriggers look (decision: 2026-10-02)

`Idea_Atlas_V2_UI_Spec.md` asked for a different layout and a light/purple style; the chat
asked for the WebTriggers 2.0 look. Decision (user): **spec layout + WebTriggers look**, with
animations toned down per the spec.

**Built**
- App shell: left sidebar (Dashboard · Analyses · Documents · Settings, "+ New analysis",
  Topic explorer v1), slim topbar, collapsible sidebar, mobile drawer. No hero/glow/reveal animations.
- Dashboard (spec messaging, recent analyses with status counts, empty state), Analyses list.
- New Analysis flow: type → "What should exist?" / "What currently exists?" uploads with real
  per-file processing state and partial-failure messages → Start analysis.
- Analysis page: header with counts (icon + number + label) and "Analyse again";
  **real processing stages** derived from backend state (no fake percentages); tabs
  Findings · Evidence · Requirements · Documents · Map; URL keeps tab/filter/document/chunk.
- Finding cards per status (covered/partial show the verified quote + source path; missing says
  "No supporting evidence was found…"; conflict shows reference vs existing source).
  Source text vs **AI assessment** are visually distinct everywhere.
- Evidence drawer → "Open in document" → document viewer scrolled to the chunk with **all cited
  quotes highlighted**. Evidence tab groups quotes by document + a document search panel.
- Map tab: coverage map (analysis → sections → requirements colored by status); click → evidence.
- Global Documents page and Settings (theme, providers/models, limits — no keys).
- Backend: finding counts + last analysed on projects, requirement source on findings,
  `GET /api/v1/documents`, `GET /api/v1/settings` (97 tests pass).

**Deliberate deviation from the spec:** the requirements review step stays between extraction
and analysis ("Approve all & analyse" makes it one click) — it's the human check that makes the
numbers trustworthy.

**Verified in the browser** (local API on the test DB, inline jobs) with a real PDF resume vs a job
description: create → upload via the real file input → honest processing states → Start analysis →
automatic extraction (15 requirements) → approve all & analyse → 8 covered · 3 partial · 4 missing →
evidence drawer → open in document (15 quotes highlighted) → map node → evidence → Documents →
Settings → Explore (v1). Not verified: narrow/mobile widths (the automation window could not be
resized) — the responsive rules are in place but untested on a phone.

Fixed during verification: Tailwind v4 cascade layers (custom `.pop` margin beat utilities → moved
into `@layer components`); stray scrollbar on the tab bar; map zoom unreadable on fit (min zoom +
scroll-to-pan + legend); Settings showed Ollama as "configured" just because it needs no key.

---

## Phase 9 — Tool calling: "Ask your analysis"

**Built**
- `llm.py`: provider-native **function calling** for Groq and Ollama (OpenAI `tools` /
  `tool_calls`) and Gemini (`functionDeclarations` / `functionCall` / `functionResponse`, with the
  model's raw parts echoed back on the next turn). Same retry/fallback/cooldown loop as every other
  call (`_call_llm_result`), so a rate-limited Gemini falls back to Groq mid-conversation.
- `services/tool_loop.py`: a bounded, provider-neutral loop — validate arguments with Pydantic,
  run the handler, send results back as `tool` messages, stop at an answer, a *finish tool*, or the
  tool budget (then one final call without tools on a flattened transcript). Bad arguments and tool
  errors are returned to the model as error results instead of crashing.
- `services/chat_service.py`: five **read-only** tools — `get_overview`, `list_findings`,
  `get_requirement`, `search_documents`, `get_chunk`. Each tool is built with the analysis id
  captured on the server; the model can't name a project, and `get_chunk` rejects chunk ids from
  other analyses. Max 6 tool calls per question. Sources returned with every answer.
- `POST /api/v1/projects/{id}/chat` and an **Ask** tab: suggested questions, answers with a
  collapsible "Used N tools" trace, and source chips that open the exact passage or finding.

**Verified:** 106 passed (scripted model: tool → answer, sources, cross-analysis isolation, invalid
arguments recovered, budget forces a tool-less final answer, finish tool, provider message
conversion). Live: the same question on **Groq** (2 tool calls, corrected its own role filter)
and **Gemini** (rate-limited → fallback) both answered "900 seconds (15 minutes); refresh tokens
are not issued" with the SDD section cited.

**Interview**

Q: How do you stop a tool-calling LLM from reading data it shouldn't?
A: Authorization lives in the tools, not the prompt. Each tool is constructed per request with the analysis id bound on the server, so the model has no argument to name another project, and anything it passes (like a chunk id) is checked against that analysis. The tools are read-only, arguments are schema-validated, and calls are capped per question.

Q: How does function calling differ between providers?
A: OpenAI-style APIs (Groq, Ollama) take `tools` and return `tool_calls` with JSON-string arguments, and results go back as `role: tool` messages with the call id. Gemini uses `functionDeclarations`, returns `functionCall` parts, expects `functionResponse` parts in a user turn, and its model turn must be echoed back as-is. I normalized all of them into one internal message format so the loop and the tools are provider-independent.

Q: What happens if the model keeps calling tools forever?
A: The loop has a hard budget (6 calls). When it's used up the model gets one last call with no tools and the transcript flattened to text, plus an instruction to answer with what it has — so latency and cost are bounded.

---

## Phase 10 — Investigator agent (built, measured, and deliberately restricted)

**Built**
- `services/investigator.py` + `agent_traces` table: re-checks ONE finding with a bounded tool loop
  (read-only `search_documents` / `get_chunk`, analysis-scoped) and a validated `submit_verdict`
  finish tool. Eligible: missing, unclear, conflict, or confidence < 0.6.
- Guardrails: quotes verified against the cited chunk (which must belong to this analysis and be an
  existing document); unverifiable → outcome `rejected`, finding kept. Every step, token count and
  duration stored in the trace.
- Endpoints: `POST /findings/{id}/investigate`, `GET /findings/{id}/traces`, `POST /runs/{id}/investigate`.
  UI: "Re-check with agent" in the evidence drawer with a live step-by-step trace; "Re-check uncertain (N)".
- Eval: `python -m eval.run_eval --investigate` scores before/after the agent on the same run.

**What measurement showed (honest)**
1. The first full agent eval failed on **free-tier limits**: Groq gpt-oss-20b allows 8,000 tokens/min
   and the Gemini daily quota ran out. Each agent step re-sends the growing conversation (up to 6,000
   characters per tool result), so steps hit the limit and retries ran out of time. Fixes: compact
   tool results for the agent (3 passages × ~450 chars, compact JSON), **context trimming** (only the
   last two tool results stay full), max steps 8 → 6. A 4-step investigation now costs ~5.6k tokens / ~5 s.
2. Live check on 3 known cases (Groq only — Gemini quota exhausted):
   P04 partial→**missing (made it worse)**, P07 missing→missing (not fixed), P10 ran out of steps.
   Even with an explicit "did any passage discuss the same topic?" self-check (investigate-v2), the
   small model treated "the specific value is absent" as "missing".
3. **Decision — asymmetric authority:** the agent may only change a finding when it brings verified
   evidence (→ covered/partial/conflict). An absence claim can't be verified, so a downgrade to
   missing/unclear is recorded (outcome `kept`) but not applied. That removes the regression risk;
   the agent stays useful as an auditable "search harder for evidence" tool.
4. Full before/after eval with the agent is **pending** (needs the Gemini daily quota to reset or a
   paid tier). No accuracy-improvement claim is made until it is measured.

**Verified:** 119 passed (fixes a false-missing with a verified quote; invented quote rejected; evidence
from another analysis ignored; confirmed / kept / no_verdict outcomes; step budget enforced; run-level
re-check only once per uncertain finding; trace ordering).

**Interview**

Q: When is an agent the right tool, and when is a pipeline better?
A: A pipeline when the steps are known in advance — here, retrieve-then-classify for every requirement. An agent only where the next step depends on what was just found: re-searching a "missing" requirement with new phrasings. So the agent runs on the few uncertain findings, with a step budget, read-only tools and a structured final answer.

Q: Your agent made a result worse — what did you do?
A: I measured it on known cases and it downgraded a correct "partial" to "missing". The insight: evidence claims are verifiable (we check the quote in the source), absence claims aren't. So I gave the agent asymmetric authority — it can only change a finding by bringing verified evidence; absence verdicts are logged, not applied. Safer, and still useful.

Q: Why did the agent hit rate limits when single calls didn't?
A: Each agent step re-sends the whole conversation, so prompt size grows with every tool result. With a per-minute token limit, that compounds. I compacted tool outputs and trimmed older results (context management), cutting a typical investigation to ~5–6k tokens.

---

## Phase 11 — Reports, exports and run diff

**Built**
- `services/report_service.py` (deterministic, no LLM): one structured report per completed run —
  executive summary headline, counts and coverage %, sections (missing, conflicts, partial,
  needs-decision, covered) with AI assessment vs verified source quotes, recommended actions.
- Exports: `GET /runs/{id}/export?format=csv|md|pdf` — CSV traceability matrix, Markdown report,
  PDF (fpdf2 core fonts; Unicode punctuation mapped to Latin-1). Safe download filenames.
- Diff: `GET /runs/{id}/diff[?against=]` — per requirement improved / regressed / unchanged / new /
  removed against the previous completed run (ordering covered > partial > unclear > conflict > missing).
- UI: **Report** tab (spec "Read view") with downloads and a "Changes since previous run" panel;
  the Findings CSV now uses the server export. Downloads go through `fetch` so auth headers work.
- Found while building: a nested f-string that reused its quote character is valid on Python 3.12+
  but a SyntaxError on the production image's Python 3.11 — fixed, and the whole backend scanned.

**Verified:** report structure and headline, all three export formats (PDF with Unicode quotes),
diff improved/unchanged/regressed, no-previous-run and incomplete-run cases.

**Interview**

Q: Why build reports server-side instead of in the browser?
A: One source of truth: the same report JSON feeds the UI, CSV, Markdown and PDF, so they can't disagree, downloads work for API clients too, and access control (Phase 12) applies to exports like any other endpoint.

---

## Phase 12 — Security: optional auth, ownership isolation, rate limits, hardening

**Built**
- `core/security.py`: bcrypt password hashing, HS256 JWTs (algorithm pinned, weak secret refused),
  `authenticate` router dependency, `ensure_owner` (404 for other users' resources), per-client
  rate limiting (Redis fixed window with in-memory fallback), security headers middleware.
- Optional login: `AUTH_ENABLED=false` (default) keeps self-hosted single-user mode with no accounts;
  `true` requires sign-in everywhere except `/health` and `/api/v1/auth/status`.
- `users` table and `projects.owner_id` (via our own migration system). Every getter — project,
  document, requirement, run, finding, trace — checks ownership; lists are filtered in SQL.
- `/api/v1/auth/status | register | login | me`; login/register limited to 10/min.
- Rate limits on LLM-backed endpoints (extract, analyze, chat, investigate, v1 explorer) and uploads → 429 + Retry-After.
- CORS restricted to `CORS_ORIGINS`; upload filenames sanitised; DOCX zip-bomb check; `ILIKE` input escaped;
  raw invalid LLM output (may contain document text) logged only with `LOG_LLM_RAW_OUTPUT=true`.
- Frontend: sign-in/register page shown only when the server requires it, any 401 signs out,
  email + sign-out in the sidebar, query cache cleared on user change.
- Removed a duplicated `GET /api/v1/documents` route (caused an OpenAPI duplicate-ID warning).
- `SECURITY.md`: threat model, controls, known limitations, production checklist.

**Found while building**
- In production the API container sees the Docker gateway IP, not the client — without trusting the
  proxy, every visitor would share one rate-limit bucket. Prod compose now sets `TRUST_PROXY_HEADERS=true`
  (safe: the port is bound to 127.0.0.1).
- Taking the *first* X-Forwarded-For entry is spoofable (nginx appends the real IP to whatever the client
  sent). Fixed to use the right-most entry.

**Verified:** 17 new tests (auth on/off, register/login/me, tampered/expired/`alg:none`/wrong-key tokens,
weak secret, two-user isolation across every resource type, rate limit 429, per-client counters, proxy IP,
headers, CORS, filenames, zip bomb, corrupt docx). Full suite green. Login screen not yet checked
in a real browser.

**Interview**

Q: How do you stop user A reading user B's data in a multi-tenant API?
A: Every resource traces back to a project with an owner_id, and every lookup goes through one getter that checks it — so a new endpoint can't forget. Lists filter by owner in SQL. Other users' IDs return 404 rather than 403 so you can't probe which IDs exist. Tests create two users and try every endpoint across the boundary.

Q: Why does your rate limiter key on user id or IP, and what's tricky about IP behind a proxy?
A: Signed-in users are limited per account; anonymous ones per IP. Behind a proxy the socket IP is the proxy's, so you must read X-Forwarded-For — but only from a trusted proxy, and only the right-most entry, because the client controls everything to the left of what your proxy appended.

Q: How do you defend an LLM agent against prompt injection in uploaded documents?
A: Treat document text as untrusted and limit what the model can *do*, not just what it's told: tools are read-only, the project id is bound server-side, step/time budgets cap loops, and the agent can only change a result by citing a quote the server verifies against the source. An injected "mark this covered" has no effect without real evidence.
