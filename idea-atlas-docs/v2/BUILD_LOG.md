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
