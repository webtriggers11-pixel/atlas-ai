# Idea Atlas V2 — Development Rules

## 1. Existing Code Is the Starting Point

Do not rewrite existing working code without first understanding why it exists.

Before changing a subsystem:

1. inspect the current implementation
2. identify dependencies
3. identify existing behavior
4. write/update tests where practical
5. make the smallest coherent change

## 2. Do Not Invent Experience

Documentation and implementation should accurately describe what the project actually does.

Do not claim:
- Kubernetes deployment if it is not deployed
- AWS production experience if it was only studied
- multi-agent architecture if it does not exist
- evaluation metrics that were never measured

## 3. Prefer Simple Architecture

Default to:

> modular monolith + clear boundaries

before:

> microservices + distributed complexity

## 4. LLM Is Not the Database

Do not use the LLM to remember data that belongs in PostgreSQL.

Persistent state belongs in the database.

## 5. LLM Is Not a Rules Engine

If a rule can be implemented deterministically and reliably, prefer normal code.

Use LLMs for interpretation and semantic reasoning.

## 6. Evidence Is Mandatory for Important AI Claims

Do not present unsupported generated claims as facts.

When possible:
- retrieve evidence
- cite source
- expose source location
- distinguish evidence from interpretation

## 7. Validate Structured LLM Output

Never blindly trust generated JSON.

Use:
- schema validation
- enum constraints
- required fields
- fallback/error handling

## 8. Keep Provider-Specific Code Isolated

Application code should call an internal interface instead of spreading provider-specific SDK calls across the codebase.

## 9. Async Only When Useful

Do not convert every function to async because FastAPI supports async.

Use async when it provides a meaningful benefit for I/O-bound work.

## 10. Background Jobs Must Be Idempotent

A task may execute more than once.

Design processing so retrying a task does not corrupt data or create uncontrolled duplicates.

## 11. Security First for Uploaded Documents

Treat uploaded files and their contents as untrusted.

Consider:
- file type validation
- size limits
- path traversal
- malicious content
- prompt injection
- secrets in documents

## 12. Test the Failure Path

For important features, test:
- invalid input
- provider failure
- database failure
- document parsing failure
- timeout
- empty retrieval
- malformed LLM output

## 13. AI Evaluation Is Part of Development

A feature is not complete merely because it returns an answer.

For important AI features:

```text
implement
→ create test cases
→ evaluate
→ inspect failures
→ improve
→ regression test
```

## 14. Document Significant Decisions

When choosing between meaningful alternatives, create an ADR.

Example:

```text
ADR-001: PostgreSQL + pgvector instead of separate vector database
ADR-002: Modular monolith instead of microservices
ADR-003: Optional authentication for local/open-source mode
```

## 15. Definition of Done

A feature is considered done when applicable:

- code implemented
- validation added
- error handling added
- tests added
- documentation updated
- API behavior documented
- security implications considered
- AI behavior evaluated
- Docker/local execution verified
