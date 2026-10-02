# Idea Atlas V2 — Development Roadmap

## Phase 0 — Baseline and Safety

Goal: preserve the existing working project before changing behavior.

Tasks:
- Verify current repository state.
- Create/tag a stable baseline.
- Document current architecture.
- Identify existing APIs and models.
- Identify existing LLM/provider code.
- Identify current Docker/deployment setup.
- Avoid unnecessary rewrites.

Done when:
- Existing application can still be run.
- V2 work has a dedicated branch/workstream.
- Current behavior is documented.

---

## Phase 1 — Product Core / Analysis Model

Goal: establish the core document comparison domain.

Build:
- Project/Analysis
- Document
- document role: reference vs existing
- processing status
- basic findings model

Do not add advanced AI yet.

Interview topics:
- API design
- relational modeling
- PostgreSQL
- FastAPI
- Pydantic
- validation

---

## Phase 2 — Document Ingestion

Goal: reliably turn uploaded files into usable text.

Build:
- upload validation
- file metadata
- text extraction
- normalization
- chunking
- processing status
- failure handling

Interview topics:
- file handling
- background jobs
- idempotency
- error handling
- storage

---

## Phase 3 — Embeddings + pgvector

Goal: enable semantic retrieval.

Build:
- embedding service
- embedding abstraction
- vector storage
- similarity search
- source metadata

Interview topics:
- embeddings
- vector databases
- cosine similarity
- indexing
- pgvector
- semantic search

---

## Phase 4 — Baseline RAG

Goal: answer questions using retrieved evidence.

Build:

```text
query
→ embedding
→ retrieval
→ context
→ LLM
→ structured response
```

Add:
- top-k retrieval
- source references
- context limits
- basic prompt templates

Interview topics:
- RAG
- context windows
- retrieval
- hallucination
- prompt construction

---

## Phase 5 — Gap Analysis

Goal: make the product solve its core problem.

Build:
- requirement/claim extraction
- evidence matching
- status classification
- gap explanations
- suggested actions
- source evidence

Statuses:

```text
covered
partial
missing
conflict
unclear
```

Interview topics:
- structured LLM output
- deterministic vs generative logic
- AI system design
- grounding

---

## Phase 6 — Evaluation

Goal: measure whether the system works.

Build:
- evaluation dataset
- retrieval evaluation
- finding classification evaluation
- evidence correctness checks
- regression tests

Track:
- relevant retrieval
- evidence quality
- classification correctness
- unsupported claims
- failure cases

Interview topics:
- RAG evaluation
- precision/recall concepts
- hallucination
- regression testing
- AI quality

---

## Phase 7 — Reliability / Provider Fallback

Goal: make the AI layer resilient.

Build:
- provider interface
- primary provider
- fallback provider
- timeout handling
- retry policy
- structured error handling

Do not blindly retry expensive/non-idempotent operations.

Interview topics:
- resilience
- retries
- timeouts
- fallbacks
- abstraction
- distributed systems basics

---

## Phase 8 — Background Processing

Goal: move long-running work out of API requests.

Build where justified:
- Celery
- Redis
- job status
- retry handling
- task idempotency

Candidates:
- large document processing
- embedding batches
- large analysis jobs

Interview topics:
- queues
- workers
- Redis
- Celery
- asynchronous processing

---

## Phase 9 — Tool Calling

Goal: allow the AI workflow to invoke controlled application functions.

Possible tools:

```text
search_documents
retrieve_evidence
get_document_metadata
compare_requirements
generate_report
```

Tools should have:
- explicit schemas
- authorization checks
- safe inputs
- deterministic outputs where possible

Interview topics:
- function/tool calling
- structured arguments
- tool security
- orchestration

---

## Phase 10 — Agent Workflow

Goal: introduce agentic behavior only where orchestration provides real value.

Potential workflow:

```text
Analyze request
    ↓
Identify required information
    ↓
Retrieve documents
    ↓
Call analysis tools
    ↓
Evaluate evidence
    ↓
Produce final report
```

Do not use an agent for workflows that can be represented as a deterministic pipeline.

Interview topics:
- agents
- state
- orchestration
- LangGraph if justified
- failure handling

---

## Phase 11 — Security / Production Hardening

Build:
- file security
- authorization
- rate limiting
- prompt injection defenses
- secret handling
- safe logs
- resource limits
- tenant isolation for hosted mode

---

## Phase 12 — Testing / CI

Build:
- unit tests
- integration tests
- API tests
- database tests
- AI evaluation tests
- CI pipeline

---

## Phase 13 — Deployment Improvements

Current deployment:
- Linux
- Contabo
- Docker
- frontend + backend

Improve:
- health checks
- restart policies
- logs
- backups
- reverse proxy configuration
- environment management
- deployment documentation

Kubernetes/AWS:
- learn separately
- create an optional future deployment experiment
- do not force them into the MVP

---

## Phase 14 — Open Source Release Quality

Build:
- README
- architecture diagram
- setup guide
- `.env.example`
- contribution guide
- issue templates
- API documentation
- development guide
- security policy
- license

---

## Phase 15 — Future Product Features

Only after the core system is stable:

- document version comparison
- scheduled analysis
- collaboration
- comments
- approval workflow
- cloud storage integrations
- hybrid retrieval
- reranking
- advanced analytics
- hosted SaaS features
