# Idea Atlas V2 — Product Requirements Document

## 1. Product Summary

Idea Atlas is an open-source document intelligence platform focused on comparing expected/reference information with existing information and identifying gaps using retrieval, evidence, and LLM-assisted analysis.

## 2. Problem

People and teams frequently maintain multiple documents containing overlapping requirements, specifications, plans, implementation details, resumes, policies, or technical documentation.

Manual comparison creates problems:

- important requirements can be missed
- evidence is difficult to locate
- similar wording can hide semantic differences
- conflicting statements are difficult to detect
- analysis takes time
- conclusions are difficult to audit

## 3. Product Goal

Turn a set of documents into an evidence-backed analysis of:

- what is covered
- what is partially covered
- what is missing
- what conflicts
- what is unclear
- what action should be taken

## 4. Primary User

The first product should support a broad document-analysis workflow rather than locking the product to one industry.

Initial useful scenarios:

### A. Resume vs Job Description

Reference:
- job description

Existing:
- resume

Output:
- matched requirements
- missing requirements
- weak evidence
- interview preparation areas

### B. Requirements vs Technical Documentation

Reference:
- SRS/BRD/requirements

Existing:
- SDD/API/technical documentation

Output:
- requirement coverage
- missing implementation/documentation
- conflicts
- unclear requirements

### C. Expected vs Existing Project Documentation

Reference:
- expected standards/checklist

Existing:
- project documents

Output:
- coverage and gaps
- evidence
- recommended actions

## 5. Core User Journey

1. User opens Idea Atlas.
2. User creates an analysis/project.
3. User selects the analysis purpose.
4. User uploads reference/expected documents.
5. User uploads existing/actual documents.
6. System processes documents.
7. System extracts and indexes content.
8. System analyzes requirements.
9. System retrieves supporting evidence.
10. System generates structured findings.
11. User reviews findings and evidence.
12. User exports or shares the analysis later.

## 6. Finding Types

Each finding should use a controlled status:

- `covered`
- `partial`
- `missing`
- `conflict`
- `unclear`

The system must not silently invent evidence.

## 7. Evidence-First Principle

Every important AI-generated finding should be traceable to source content whenever possible.

A finding should contain:

- requirement/claim
- status
- evidence
- source document
- source location/chunk
- explanation
- suggested action
- confidence/quality metadata where appropriate

## 8. Example Finding

Requirement:

> System must support refresh-token authentication.

Result:

- Status: `partial`
- Evidence: authentication document section discussing JWT access tokens
- Missing evidence: refresh-token flow is not documented
- Suggested action: document or implement refresh-token handling

The UI should allow the user to inspect the supporting source.

## 9. MVP Functional Requirements

### Project/Analysis

- Create analysis
- Rename analysis
- View analysis
- Delete analysis
- Track processing status

### Documents

- Upload supported files
- Store document metadata
- Associate documents with an analysis
- Identify reference vs existing document
- Track processing state
- Handle failed processing

### Processing

- Extract text
- Normalize text
- Chunk text
- Store chunks
- Generate embeddings
- Store embeddings

### Retrieval

- Semantic search
- Metadata filtering
- Retrieve top relevant evidence
- Return source references

### Analysis

- Extract requirements/claims
- Compare against evidence
- Generate structured findings
- Explain findings
- Recommend actions

### Reporting

- Summary counts
- Finding list
- Evidence/source references
- Export capability can be added after core analysis works

## 10. Non-Functional Requirements

### Reliability

- Failed document processing must be visible.
- LLM failures must not corrupt analysis state.
- Partial processing should be recoverable.

### Security

- Uploaded documents must not be exposed between users when authentication is enabled.
- Secrets must remain server-side.
- Prompt injection from uploaded documents must be treated as untrusted input.
- File types and upload sizes must be validated.

### Performance

- Document processing should be asynchronous for large files.
- Retrieval should avoid sending unnecessary documents to the LLM.
- Database queries should be indexed appropriately.

### Explainability

The system should distinguish:

- source evidence
- deterministic backend results
- LLM-generated interpretation

## 11. Access Model

### Open-source/local

Default:
- no forced login
- single-user/local deployment
- all core functionality available

### Hosted multi-user

Optional:
- authentication
- user isolation
- quotas/rate limits
- private document storage

The architecture should support authentication without making the core open-source workflow dependent on it.

## 12. Future Features

Only after the MVP is stable:

- document version comparison
- recurring analysis
- team collaboration
- comments
- approval workflow
- advanced hybrid retrieval
- reranking
- tool calling
- agent workflows
- scheduled analysis
- integrations
- cloud storage integrations
- evaluation dashboard
- hosted SaaS features

## 13. Success Criteria

The MVP is successful when a user can:

1. Upload two sets of documents.
2. Process them successfully.
3. Ask the system to analyze coverage/gaps.
4. Receive structured findings.
5. Inspect evidence for each important finding.
6. Understand why a finding was classified.
7. Repeat the analysis after changing documents.
