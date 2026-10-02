# Idea Atlas V2 — Development Documentation

## Purpose

Idea Atlas V2 is an open-source Document Intelligence and Gap Analysis platform.

The core problem:

> Users often have multiple documents that describe what should exist and what currently exists. Comparing those documents manually is slow, inconsistent, and difficult to audit.

Idea Atlas helps users upload documents, retrieve evidence, compare requirements, identify gaps/conflicts/uncertainties, and produce an actionable analysis with source evidence.

## Product Direction

Idea Atlas is **not primarily another AI chatbot**.

The core workflow is:

Reference / Expected Document(s)
+
Existing / Actual Document(s)
→ document processing
→ semantic retrieval
→ evidence extraction
→ comparison
→ gap analysis
→ actionable report

## Open Source / Access Model

Idea Atlas is being developed as an open-source project.

### Local/self-hosted usage

- No mandatory login should be required for a local/self-hosted installation by default.
- A user should be able to run the project and use the core workflow immediately.
- Authentication can remain available as an optional deployment feature.

### Public hosted instance

If a public hosted instance is created later:

- Authentication may be required to protect user documents and resources.
- Public hosted access can still offer a free tier.
- Usage limits can be introduced later based on infrastructure cost.
- The open-source repository should not depend on a paid hosted service.

### Product principle

Do not add login merely to create friction.

Authentication should exist when it solves a real requirement such as:
- multi-user data isolation
- private documents
- quotas
- team collaboration
- public deployment security

## Primary MVP

The first complete product loop should support:

1. Create an analysis/project.
2. Upload reference and existing documents.
3. Extract text.
4. Chunk documents.
5. Generate embeddings.
6. Store embeddings in PostgreSQL + pgvector.
7. Retrieve relevant evidence.
8. Compare requirements/evidence.
9. Classify findings:
   - covered
   - partially covered
   - missing
   - conflict
   - unclear
10. Generate structured analysis.
11. Show source evidence.
12. Produce an actionable report.

## Non-goals for the first MVP

Do not start with:

- complex autonomous agents
- Kubernetes deployment
- multi-agent architecture
- unnecessary microservices
- complicated billing
- social/community features
- generic chatbot features
- dozens of LLM providers

These can be considered later when justified by a real requirement.

## Development Rule

Every major feature should satisfy at least one of:

1. It solves a real product problem.
2. It improves reliability/quality.
3. It improves security.
4. It improves performance/scale.
5. It demonstrates a meaningful engineering capability.

## Source of Truth

The following documents define the current V2 direction:

- `PRD.md` — product requirements
- `TRD.md` — technical requirements/design
- `ROADMAP.md` — implementation phases
- `ARCHITECTURE.md` — architecture and data flow
- `DEVELOPMENT_RULES.md` — development conventions and decision rules

When implementation conflicts with these documents, update the documentation and record the architectural decision rather than silently changing direction.
