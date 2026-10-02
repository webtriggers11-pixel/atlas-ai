# Idea Atlas V2 — Architecture

## 1. High-Level Architecture

```text
                 ┌─────────────────────┐
                 │    Web Frontend     │
                 └──────────┬──────────┘
                            │ HTTP
                            ▼
                 ┌─────────────────────┐
                 │       FastAPI       │
                 │     API Layer       │
                 └──────────┬──────────┘
                            │
          ┌─────────────────┼──────────────────┐
          │                 │                  │
          ▼                 ▼                  ▼
     Project/Doc       Analysis Service    AI Service
       Services                              │
          │                 │          ┌─────┴─────┐
          │                 │          │           │
          ▼                 ▼          ▼           ▼
     PostgreSQL        Retrieval     LLM       Embedding
          │                 │        Provider    Provider
          │                 ▼
          │            pgvector
          │
          ▼
      Document
       Storage

          ┌──────────────────────────────┐
          │ Redis + Worker (when needed) │
          └──────────────────────────────┘
```

## 2. Core Request Flow

### Document ingestion

```text
Upload
→ validate
→ store metadata
→ extract text
→ normalize
→ chunk
→ embed
→ store vectors
→ indexed
```

### Gap analysis

```text
Analysis request
→ identify requirements
→ retrieve relevant evidence
→ construct grounded context
→ LLM structured analysis
→ validate output
→ persist findings
→ display evidence
```

## 3. Separation of Responsibilities

### FastAPI/API layer

Responsible for:
- authentication/authorization
- request validation
- HTTP response
- routing
- dependency injection

### Domain/application layer

Responsible for:
- analysis workflow
- document lifecycle
- finding creation
- orchestration

### Infrastructure layer

Responsible for:
- PostgreSQL
- vector storage
- file storage
- Redis
- LLM providers
- embedding providers

### AI layer

Responsible for:
- prompt construction
- structured generation
- embeddings
- retrieval orchestration
- provider fallback
- AI evaluation hooks

## 4. AI Boundary

The system should not allow the LLM to directly mutate arbitrary database state.

Preferred:

```text
LLM
 ↓
validated structured output
 ↓
application service
 ↓
database
```

For tools:

```text
LLM
 ↓
tool schema
 ↓
authorization
 ↓
tool execution
 ↓
validated result
 ↓
LLM
```

## 5. Evidence Model

Every finding should maintain a relationship to source evidence.

Conceptually:

```text
Finding
  |
  +-- EvidenceReference
          |
          +-- Document
          +-- Chunk
          +-- location metadata
```

This makes results auditable.

## 6. Open Source Deployment Modes

### Mode A — Local/self-hosted

```text
Browser
  ↓
Frontend
  ↓
FastAPI
  ↓
PostgreSQL + pgvector
```

No login required by default.

### Mode B — Public hosted

```text
Browser
  ↓
Frontend
  ↓
Authentication
  ↓
FastAPI
  ↓
User-owned resources
```

Authentication and quotas can be enabled.

## 7. Current Infrastructure

Current deployment baseline:

- Contabo Linux server
- Docker
- frontend container
- backend container

Do not replace this architecture without a demonstrated requirement.

## 8. Future Scale Path

If usage grows:

```text
Load Balancer
      |
API replicas
      |
PostgreSQL
      |
Redis
      |
Worker replicas
      |
Object storage
```

Kubernetes can become a later orchestration layer if operational complexity justifies it.

## 9. Architecture Decisions to Record

For significant decisions, document:

- problem
- options considered
- chosen approach
- reason
- tradeoffs
- consequences

Use a lightweight ADR format when a decision affects system architecture.
