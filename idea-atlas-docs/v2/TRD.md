# Idea Atlas V2 — Technical Requirements Document

## 1. Technical Direction

Target stack:

- Python
- FastAPI
- PostgreSQL
- pgvector
- SQLAlchemy
- Pydantic
- Redis
- Celery/background processing where justified
- Docker
- Linux deployment
- LLM provider abstraction
- Embedding provider abstraction

Existing frontend/backend repositories and deployment should be preserved as the starting point.

## 2. Architecture Principles

### Principle 1 — Modular monolith first

Do not split the system into microservices unless there is a demonstrated reason.

Initial architecture:

```text
Frontend
   |
FastAPI application
   |
------------------------------------------------
| Auth | Projects | Documents | Retrieval | AI |
------------------------------------------------
   |
PostgreSQL + pgvector
   |
Redis / background workers
```

### Principle 2 — Deterministic before generative

Use normal backend/database logic where deterministic logic is sufficient.

Use an LLM for tasks such as:

- semantic interpretation
- requirement extraction
- classification where rules are insufficient
- explanation
- structured analysis

### Principle 3 — Evidence before conclusions

LLM findings should be grounded in retrieved document evidence.

### Principle 4 — Provider abstraction

Application business logic should not be tightly coupled to one LLM provider.

### Principle 5 — Testability

Core services should be independently testable.

## 3. Proposed Domain Model

Initial entities:

```text
User (optional for local/single-user mode)
  |
  +-- Project / Analysis
         |
         +-- Documents
                |
                +-- DocumentChunks
                       |
                       +-- Embeddings

Analysis
  |
  +-- Requirements / Claims
  |
  +-- Findings
         |
         +-- EvidenceReferences
```

The exact schema should be finalized against the existing codebase before migration work.

## 4. Document Lifecycle

```text
UPLOADED
   |
   v
PROCESSING
   |
   +----> FAILED
   |
   v
PROCESSED
   |
   v
INDEXED
```

Processing should be idempotent where practical.

## 5. RAG Pipeline

```text
Document
  |
Text extraction
  |
Normalization
  |
Chunking
  |
Embedding
  |
PostgreSQL + pgvector
  |
Query
  |
Query embedding
  |
Similarity search
  |
Metadata filtering
  |
Evidence selection
  |
Prompt construction
  |
Structured LLM output
  |
Validation
  |
Finding
```

## 6. Chunking

The first implementation should use a simple, deterministic chunking strategy.

Do not prematurely optimize chunking.

Capture metadata such as:

- document ID
- chunk ID
- chunk index
- section/title when available
- page number when available
- source location

Chunking can later be evaluated and improved.

## 7. Retrieval

Initial retrieval:

- vector similarity
- top-k retrieval
- metadata filters

Later:

- hybrid keyword + vector retrieval
- reranking
- query rewriting

Do not add these until baseline retrieval quality can be measured.

## 8. Structured LLM Output

LLM output should be validated using Pydantic schemas.

Example conceptual schema:

```python
class Finding(BaseModel):
    requirement: str
    status: Literal[
        "covered",
        "partial",
        "missing",
        "conflict",
        "unclear",
    ]
    evidence: list[str]
    explanation: str
    suggested_action: str
```

The actual schema may evolve based on implementation.

## 9. LLM Provider Layer

Use an internal interface so application services can request:

- text generation
- structured output
- embeddings

without knowing provider-specific implementation details.

Example conceptual flow:

```text
Application Service
        |
    LLM Interface
        |
  +-----+-----+
  |           |
Provider A  Provider B
```

Provider fallback should be added after the baseline provider flow is stable.

## 10. Authentication

Authentication is not mandatory for local/self-hosted single-user mode.

If authentication already exists in the repository, keep it modular.

For hosted mode:

- user identity
- authorization
- project ownership
- document isolation
- rate limits/quotas

must be enforced.

## 11. Background Processing

Use background workers when work is:

- CPU-intensive
- network-heavy
- long-running
- unsuitable for request/response latency

Examples:

- document extraction for large files
- embedding batches
- bulk indexing
- large analysis jobs

Redis/Celery should be introduced where the workload justifies it.

## 12. API Design

Prefer resource-oriented REST endpoints.

Conceptual examples:

```text
POST   /api/v1/projects
GET    /api/v1/projects/{project_id}

POST   /api/v1/projects/{project_id}/documents
GET    /api/v1/documents/{document_id}

POST   /api/v1/projects/{project_id}/process
POST   /api/v1/projects/{project_id}/analyze

GET    /api/v1/projects/{project_id}/findings
GET    /api/v1/findings/{finding_id}
```

Actual routes should be reconciled with the existing API structure rather than blindly replacing it.

## 13. Database

PostgreSQL is the primary relational database.

Use:

- foreign keys
- constraints
- appropriate indexes
- transactions
- migrations

pgvector stores embeddings alongside relational metadata.

## 14. Deployment

Current baseline:

- Linux server
- Contabo
- Docker
- frontend container
- backend container

Do not introduce Kubernetes into the production architecture merely for learning.

Kubernetes can be covered separately as interview preparation and considered for a future deployment experiment.

## 15. Observability

Minimum:

- structured application logs
- request/error logging
- background task logging
- LLM failure logging
- processing status
- latency measurement

Later:

- tracing
- metrics dashboard
- token/cost tracking

## 16. Testing Strategy

### Unit tests

- chunking
- parsers
- validation
- classification helpers
- retrieval utilities

### Integration tests

- PostgreSQL
- pgvector
- API/database interactions
- document processing

### AI evaluation

Maintain a fixed evaluation dataset containing:

- source documents
- expected requirements
- expected status
- expected evidence
- expected answer characteristics

## 17. Security

Treat uploaded documents as untrusted input.

Consider:

- file validation
- file size limits
- path traversal
- prompt injection
- malicious document content
- secret management
- authorization
- tenant isolation for hosted mode
- rate limiting
- safe logging

## 18. Production Constraint

Avoid premature complexity.

The first target is:

> One well-engineered modular backend that works reliably.

Not:

> Many services that are difficult to maintain.
