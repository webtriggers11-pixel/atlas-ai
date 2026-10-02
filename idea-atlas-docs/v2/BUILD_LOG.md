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
