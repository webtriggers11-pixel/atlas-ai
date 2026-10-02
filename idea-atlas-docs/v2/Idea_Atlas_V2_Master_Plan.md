# Idea Atlas V2 — Product, UI & Development Master Plan

> **Status:** Development source of truth  
> **Project:** Open-source Document Intelligence & Gap Analysis platform  
> **Goal:** Build a genuinely useful product while creating a strong Python Backend + AI Engineering portfolio project.

---

## 1. Product Vision

Idea Atlas should evolve from a topic-exploration / mind-map application into a **Document Intelligence and Gap Analysis platform**.

The core problem:

> People and teams often have documents describing what should exist and other documents describing what currently exists. Comparing them manually is slow, inconsistent, and difficult to audit.

Idea Atlas should help users:

1. Upload documents.
2. Understand their contents.
3. Compare expected/reference information with existing information.
4. Retrieve supporting evidence.
5. Identify:
   - covered items
   - partially covered items
   - missing items
   - conflicts
   - unclear items
6. Explain why a finding was produced.
7. Suggest an actionable next step.

The product should **not become another generic AI chatbot**.

The main differentiator is:

> **Evidence-backed document comparison and gap analysis.**

---

## 2. Example Use Cases

### Resume vs Job Description

Reference:
- Job Description

Existing:
- Resume

Output:
- Covered requirements
- Partially supported skills
- Missing requirements
- Evidence from resume
- Interview preparation areas

### Requirements vs Technical Documentation

Reference:
- BRD / SRS / requirements

Existing:
- SDD / API / technical documentation

Output:
- Requirement coverage
- Missing implementation/documentation
- Conflicting requirements
- Unclear requirements
- Evidence for important findings

### Expected Standards vs Existing Documentation

Reference:
- Checklist
- Standard
- Policy
- Expected architecture

Existing:
- Project documents
- Current implementation documentation

Output:
- Covered
- Partial
- Missing
- Conflicting
- Unclear

---

## 3. Product Principle

The system should answer:

> **"What is missing or different, and where is the evidence?"**

Not simply:

> "Here is an AI-generated summary."

Every important finding should be traceable to source evidence whenever possible.

---

## 4. Open-Source Strategy

Idea Atlas is an **open-source project**.

### Local / Self-Hosted

The open-source version should work without mandatory authentication by default.

A user should be able to clone the repository, configure environment variables, start the application, upload documents, and run analysis without being forced to create an online account.

### Public Hosted Instance

If a public hosted version is created later, authentication may be enabled for:

- user isolation
- private documents
- quotas
- rate limits
- usage tracking
- team features

The hosted version can have a free tier.

The open-source project should not depend on a paid hosted service.

### Rule

Do not add login merely because most SaaS products have login. Authentication should solve a real requirement.

---

## 5. Existing Infrastructure

The existing project is already running locally and has an existing deployment.

Current baseline:

- Linux-based Contabo server
- Docker-based deployment
- Frontend container
- Backend container

**Do not rebuild infrastructure unnecessarily.**

Kubernetes and AWS are preparation / possible future deployment targets, not requirements for the first MVP.

---

# 6. UI Direction

The current UI is centered around:

- Explore any topic
- Topic generation
- Tree view
- Read view
- Understand a document

The new product needs a UI centered around:

> **Create Analysis → Upload Documents → Analyze → Review Gaps → Inspect Evidence → Take Action**

## UI revamp is required

This is a **functional UX revamp**, not a complete visual redesign.

Keep the existing visual language where practical.

Do not spend early development time on:

- excessive animations
- glassmorphism
- complex marketing effects
- unnecessary dashboards
- decorative features

Focus on product workflow.

---

## 7. New Navigation

Recommended:

```text
Idea Atlas
├── Dashboard
├── Analyses
│   ├── Overview
│   ├── Findings
│   ├── Evidence
│   ├── Documents
│   └── Map
├── Documents
└── Settings
```

The existing Tree functionality should not be thrown away immediately. It can become:

> **Map**

inside an analysis.

---

## 8. New Dashboard

The dashboard should communicate the new product purpose immediately.

```text
Idea Atlas

Document Intelligence
Find gaps between what should exist and what currently exists.

[ + New Analysis ]

Recent Analyses

┌─────────────────────┐
│ Resume vs Python JD │
│ 18 covered          │
│ 4 partial           │
│ 3 missing           │
└─────────────────────┘

┌─────────────────────┐
│ SRS vs Technical    │
│ Documentation       │
│ 21 covered          │
│ 7 gaps              │
└─────────────────────┘
```

The old "Explore any topic..." search should no longer be the primary hero interaction.

---

## 9. New Analysis Flow

### Step 1 — Create Analysis

```text
What do you want to analyze?

○ Compare requirements
○ Find document gaps
○ Resume vs Job Description
○ Custom analysis
```

### Step 2 — Reference Documents

```text
What should exist?

[ Drop reference documents ]

SRS / JD / Requirements / Standards
```

### Step 3 — Existing Documents

```text
What currently exists?

[ Drop existing documents ]

Resume / SDD / Existing Documentation
```

### Step 4 — Start Analysis

```text
Reference Documents
        +
Existing Documents
        ↓
[ Start Analysis ]
```

---

## 10. Analysis Screen

The analysis screen is the core product UI.

```text
Resume vs Python Backend JD

18 Covered   4 Partial   3 Missing   1 Conflict

------------------------------------------------

All | Missing | Partial | Conflict

------------------------------------------------

FastAPI
✓ Covered

Evidence:
"Built REST APIs using FastAPI..."

Source:
Resume → Experience → Project X

------------------------------------------------

Kubernetes
! Missing

No supporting evidence found in the provided resume.

Suggested action:
Learn Kubernetes fundamentals.
```

---

## 11. Finding Model

Every finding should have:

- Requirement / Claim
- Status
- Evidence
- Source document
- Source location
- Explanation
- Suggested action
- Confidence / quality metadata where appropriate

Statuses:

```text
covered
partial
missing
conflict
unclear
```

---

## 12. Evidence-First Design

Example:

Requirement:

> System must support JWT authentication with refresh tokens.

Result:

```text
Status: PARTIAL

Evidence:
Authentication documentation mentions JWT access tokens.

Missing evidence:
No refresh-token flow is documented.

Suggested action:
Document or implement refresh-token handling.
```

The user should be able to open the source evidence.

The system must avoid presenting unsupported LLM claims as facts.

---

# 13. Product Architecture

```text
                    Web Frontend
                         |
                         | HTTP
                         v
                    FastAPI API
                         |
       +-----------------+------------------+
       |                 |                  |
       v                 v                  v
 Project/Document    Analysis Service    AI Service
       |                 |                  |
       |                 |          +-------+-------+
       |                 |          |               |
       v                 v          v               v
 PostgreSQL          Retrieval     LLM           Embedding
       |                 |        Provider        Provider
       |                 |
       +-------------> pgvector
                         |
                  Evidence Retrieval

             Redis + Workers when needed
```

Start as a modular monolith.

Do not introduce microservices unless there is a real requirement.

---

# 14. Core Data Model

Initial conceptual model:

```text
User (optional for local mode)
    |
    +-- Analysis / Project
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

The exact database schema must be reconciled with the existing repository before implementation.

Do not blindly replace existing models.

---

# 15. Technical Stack

Primary stack:

- Python
- FastAPI
- PostgreSQL
- pgvector
- SQLAlchemy
- Pydantic
- Redis
- Celery/background workers when justified
- Docker
- Linux
- LLM provider abstraction
- Embedding provider abstraction

Keep the existing frontend stack unless there is a concrete reason to change it.

---

# 16. Development Phases

## Phase 0 — Existing System Baseline

Goal: protect the existing working project.

Tasks:
- Verify repository state.
- Create/tag stable baseline.
- Understand current frontend.
- Understand current backend.
- Identify existing APIs/models.
- Identify existing LLM integration.
- Identify Docker setup.
- Identify deployment configuration.

Do not rewrite working code without understanding it.

Done when:
- Current application still runs.
- V2 work has a clear branch/workstream.
- Existing behavior is documented.

---

## Phase 1 — UI + Analysis Foundation

Goal: change the product workflow from topic exploration to document analysis.

### Frontend

Build:
- Dashboard
- Analyses list
- New Analysis flow
- Reference document area
- Existing document area
- Analysis overview
- Findings placeholder
- Evidence placeholder
- Documents section
- Map section

### Backend

Build/adapt:
- Analysis/Project model
- Document model
- document role
- processing status
- basic findings model

### Learning

- FastAPI
- Pydantic
- PostgreSQL
- relational modeling
- REST API design

---

## Phase 2 — Document Ingestion

Goal: reliably convert uploaded documents into usable text.

```text
Upload
  ↓
Validate
  ↓
Store metadata
  ↓
Extract text
  ↓
Normalize
  ↓
Chunk
  ↓
Store
```

Handle:
- invalid files
- unsupported formats
- large files
- extraction failures
- processing status

Learning:
- file handling
- validation
- background processing
- idempotency
- error handling

---

## Phase 3 — Embeddings + pgvector

Goal: enable semantic document retrieval.

```text
Chunk
  ↓
Embedding model
  ↓
Vector
  ↓
PostgreSQL + pgvector
```

Store useful metadata:
- document ID
- chunk ID
- chunk index
- page number where available
- section/title where available
- source location

Learning:
- embeddings
- vector representation
- cosine similarity
- semantic search
- pgvector
- vector indexing

---

## Phase 4 — Baseline RAG

Goal: answer questions using retrieved evidence.

```text
User query
    ↓
Query embedding
    ↓
Vector search
    ↓
Top relevant chunks
    ↓
Context construction
    ↓
LLM
    ↓
Structured response
```

Initial version:
- top-k retrieval
- metadata filtering
- source references
- context limits

Do not add advanced retrieval prematurely.

Learning:
- RAG
- context windows
- retrieval
- prompt construction
- hallucination
- grounding

---

## Phase 5 — Gap Analysis

Goal: make the product solve the core problem.

```text
Reference document
       +
Existing document
       ↓
Requirement extraction
       ↓
Evidence retrieval
       ↓
Comparison
       ↓
Classification
       ↓
Finding
```

Classification:

```text
covered
partial
missing
conflict
unclear
```

Use structured LLM output validated by Pydantic.

Learning:
- structured LLM output
- Pydantic validation
- grounding
- deterministic vs generative logic
- AI application architecture

---

## Phase 6 — Evaluation

Goal: measure whether the AI system actually works.

Create a fixed evaluation dataset containing:
- source documents
- expected requirements
- expected status
- expected evidence
- expected answer characteristics

Test:
- retrieval relevance
- evidence correctness
- classification correctness
- unsupported claims
- failure cases

Process:

```text
Implement
    ↓
Evaluate
    ↓
Inspect failures
    ↓
Improve
    ↓
Regression test
```

Learning:
- RAG evaluation
- retrieval quality
- precision/recall concepts
- hallucination
- regression testing

---

## Phase 7 — LLM Provider Fallback

Goal: improve reliability.

```text
Application
     ↓
LLM Interface
     ↓
Primary Provider
     ↓
Failure?
  /     \
Yes      No
 |        |
Fallback  Response
 |
Response
```

Implement:
- provider abstraction
- primary provider
- fallback provider
- timeout
- retry policy
- structured error handling

Do not retry blindly.

Learning:
- resilience
- timeout
- retries
- fallback
- abstraction
- distributed systems basics

---

## Phase 8 — Background Processing

Goal: move long-running operations outside normal HTTP requests.

Potential tasks:
- large document processing
- batch embeddings
- large analyses

Use:

```text
FastAPI
   ↓
Redis
   ↓
Celery Worker
   ↓
Processing
```

Tasks must be idempotent.

Learning:
- Redis
- Celery
- queues
- workers
- retry handling
- asynchronous processing

---

## Phase 9 — Tool Calling

Goal: allow controlled AI workflows to invoke application functions.

Potential tools:

```text
search_documents()
retrieve_evidence()
get_document_metadata()
compare_requirements()
generate_report()
```

Tools require:
- explicit schemas
- input validation
- authorization
- safe execution
- predictable results

Learning:
- function calling
- tool calling
- structured arguments
- tool security
- orchestration

---

## Phase 10 — Agent Workflow

Goal: use agentic behavior only where it genuinely improves the workflow.

Potential flow:

```text
Analyze request
      ↓
Determine information needed
      ↓
Retrieve documents
      ↓
Call tools
      ↓
Evaluate evidence
      ↓
Generate report
```

Do not turn a deterministic workflow into an agent unnecessarily.

LangGraph can be introduced only if stateful orchestration actually requires it.

Learning:
- agents
- state
- orchestration
- LangGraph
- failure handling

---

## Phase 11 — Security / Production Hardening

Implement:
- file validation
- upload size limits
- path traversal protection
- authorization
- document isolation
- rate limiting
- secret management
- safe logging
- prompt injection defenses
- resource limits

Uploaded documents are untrusted input.

---

## Phase 12 — Testing + CI

### Unit tests

- chunking
- parsing
- validation
- classification helpers
- retrieval utilities

### Integration tests

- PostgreSQL
- pgvector
- API/database interactions
- document processing

### AI tests

- retrieval
- evidence
- classification
- structured output
- known failure cases

### CI

```text
lint
→ unit tests
→ integration tests
→ build
```

---

## Phase 13 — Deployment Hardening

Current deployment:

```text
Linux
  ↓
Contabo
  ↓
Docker
  ├── Frontend
  └── Backend
```

Improve:
- health checks
- restart policies
- logs
- backups
- reverse proxy
- environment management
- deployment documentation

Do not add Kubernetes just to put Kubernetes on the resume.

Kubernetes should be learned separately and can become a future deployment experiment.

AWS can similarly be learned separately or used for a later deployment experiment.

---

## Phase 14 — Open Source Release Quality

Prepare:
- README
- installation guide
- architecture documentation
- `.env.example`
- contribution guide
- issue templates
- API documentation
- development guide
- security policy
- license

The project should be easy for another developer to clone and run.

---

## Phase 15 — Future Features

Only after the core system is stable:

- document version comparison
- recurring analysis
- team collaboration
- comments
- approval workflows
- hybrid search
- reranking
- cloud storage integrations
- scheduled analysis
- advanced analytics
- hosted SaaS
- usage quotas
- team workspaces

---

# 17. AI Pipeline

The core AI pipeline should eventually be:

```text
Documents
    ↓
Text Extraction
    ↓
Chunking
    ↓
Embeddings
    ↓
PostgreSQL / pgvector
    ↓
Requirement Extraction
    ↓
Evidence Retrieval
    ↓
Context Construction
    ↓
Structured LLM Output
    ↓
Validation
    ↓
Findings
    ↓
Evidence-backed Report
```

---

# 18. Deterministic vs LLM Responsibilities

## Prefer normal backend logic for:

- authentication
- authorization
- database operations
- file validation
- status management
- counting findings
- filtering
- pagination
- permissions
- deterministic rules

## Use LLMs for:

- semantic interpretation
- requirement extraction
- understanding natural language
- explaining evidence
- classification when rules are insufficient
- generating suggested actions

The LLM should not directly control arbitrary database operations.

---

# 19. Tool Security

Preferred:

```text
LLM
 ↓
Tool schema
 ↓
Validation
 ↓
Authorization
 ↓
Tool execution
 ↓
Validated result
 ↓
LLM
```

Never allow an LLM to directly execute arbitrary SQL, shell commands, or filesystem operations.

---

# 20. Definition of Done

A feature is not complete merely because it works once.

Where applicable:

- implementation complete
- API validated
- error handling added
- tests added
- documentation updated
- security reviewed
- Docker execution verified
- AI behavior evaluated
- failure path tested

For AI features:

```text
Works
+
Grounded
+
Evaluated
+
Regression tested
```

---

# 21. Development Rules

1. Existing working code is the starting point.
2. Do not rewrite code without understanding it.
3. Prefer a modular monolith.
4. Do not use an LLM where deterministic code is better.
5. Important AI findings should have evidence.
6. Validate all structured LLM output.
7. Keep provider-specific code isolated.
8. Background tasks must be safe to retry.
9. Uploaded documents are untrusted.
10. Measure AI quality instead of assuming it works.
11. Do not claim technologies the project does not actually use.
12. Document significant architectural decisions.

---

# 22. First Development Sprint

The repository and code are already set up. The next work is implementation, not project setup.

## Backend

1. Inspect existing models and APIs.
2. Identify reusable code.
3. Add/adapt Analysis/Project entity.
4. Add/adapt Document entity.
5. Add document role:
   - reference
   - existing
6. Add processing status.
7. Add required migrations.
8. Add required API endpoints.

## Frontend

1. Replace old home emphasis with Dashboard.
2. Add Analyses navigation.
3. Add New Analysis flow.
4. Add reference document upload UI.
5. Add existing document upload UI.
6. Add analysis detail shell.
7. Keep existing Map functionality available.

## Do not build yet

- agents
- LangGraph
- Kubernetes
- advanced retrieval
- complex evaluation dashboard
- billing
- team collaboration

---

# 23. First Vertical Slice

The first working slice should be:

```text
Create Analysis
      ↓
Upload Reference Document
      ↓
Upload Existing Document
      ↓
Store metadata
      ↓
Show Analysis page
      ↓
Show both documents
```

Once this works end-to-end, proceed to document processing.

---

# 24. Interview Value

The finished project should provide real discussion material around:

### Python
- async/await
- typing
- exceptions
- OOP
- decorators
- generators
- performance

### FastAPI
- dependency injection
- middleware
- validation
- authentication
- async APIs
- API architecture
- error handling

### PostgreSQL
- relationships
- indexes
- transactions
- query optimization
- pgvector

### Redis/Celery
- caching
- queues
- workers
- retries
- idempotency

### Docker
- images
- containers
- networking
- volumes
- environment configuration
- production deployment

### AI
- LLMs
- tokens
- embeddings
- vector search
- RAG
- structured output
- tool calling
- agents
- evaluation
- provider fallback

### System Design
- modular monolith
- scalability
- reliability
- failure handling
- observability
- security

---

# 25. Final Product Direction

The target is not:

> "I made an AI chatbot."

The target is:

> **"I built an open-source document intelligence platform that processes documents, creates semantic representations, retrieves evidence using PostgreSQL/pgvector, performs evidence-grounded gap analysis with structured LLM output, evaluates the quality of its AI pipeline, and runs as a Dockerized Python/FastAPI application."**

---

# 26. Instruction for Claude

Before implementing a feature:

1. Read this document.
2. Inspect the existing repository.
3. Identify what already exists.
4. Reuse working components where appropriate.
5. State the files that will be changed.
6. Implement the smallest coherent change.
7. Run relevant tests.
8. Report what changed.
9. Report architectural decisions or deviations.
10. Update this document when the agreed product direction changes.

**Do not redesign the architecture or add major technologies without a concrete requirement.**
