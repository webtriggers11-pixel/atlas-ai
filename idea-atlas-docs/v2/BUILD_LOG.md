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
