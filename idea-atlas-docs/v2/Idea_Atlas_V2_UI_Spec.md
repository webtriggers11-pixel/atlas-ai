# Idea Atlas V2 — UI/UX Development Specification

> **Purpose:** This document is the UI/UX source of truth for the Idea Atlas V2 redesign.
>
> **Important:** This is a product UI redesign, not a visual redesign only. The current UI is centered around topic exploration and mind maps. V2 should be centered around document analysis, gap detection, evidence, and actionable findings.

---

# 1. UI Goal

The new UI should communicate this workflow immediately:

```text
Create Analysis
      ↓
Upload Documents
      ↓
Analyze
      ↓
Find Gaps
      ↓
Review Evidence
      ↓
Take Action
```

The primary user should understand what Idea Atlas does within a few seconds.

Avoid making the product look like:

> "Another AI chatbot"

or:

> "Another topic/mind-map generator"

The UI should communicate:

> **Find what's missing, different, or unclear across documents — with evidence.**

---

# 2. Current UI vs V2

## Current UI

The current interface is focused on:

- Explore any topic
- Generate
- Topic maps
- Tree view
- Read view
- Understand a document

This came from the original topic-explorer concept.

## V2 UI

The primary experience should be:

- Dashboard
- Analyses
- New Analysis
- Reference Documents
- Existing Documents
- Findings
- Evidence
- Documents
- Map

The existing Tree/Map functionality should be preserved where useful, but it should become a secondary view inside an analysis.

---

# 3. Design Direction

The UI should feel:

- clean
- professional
- modern
- developer/productivity oriented
- trustworthy
- focused
- lightweight

Avoid:

- excessive gradients
- excessive glow
- glassmorphism
- unnecessary animation
- huge marketing-style hero sections
- decorative AI effects
- excessive rounded cards
- visual clutter

The existing visual language can be retained where it works.

The goal is a **functional product redesign**, not a Dribbble-style redesign.

---

# 4. Global Navigation

Recommended structure:

```text
┌──────────────────────────────────────────────────────────────┐
│ Idea Atlas                              + New Analysis        │
├───────────────┬──────────────────────────────────────────────┤
│               │                                              │
│ Dashboard     │                                              │
│               │                                              │
│ Analyses      │                Main Content                  │
│               │                                              │
│ Documents     │                                              │
│               │                                              │
│ Settings      │                                              │
│               │                                              │
└───────────────┴──────────────────────────────────────────────┘
```

## Sidebar

Items:

1. Dashboard
2. Analyses
3. Documents
4. Settings

Primary CTA:

> **+ New Analysis**

The CTA should always be easy to find.

---

# 5. Dashboard

## Purpose

The dashboard should immediately explain the product and provide access to recent analyses.

### Recommended layout

```text
Idea Atlas

Document Intelligence

Find gaps between what should exist and what currently exists.

[ + New Analysis ]


Recent Analyses

┌─────────────────────────┐
│ Resume vs Python JD     │
│                         │
│ 18 Covered              │
│ 4 Partial               │
│ 3 Missing               │
│                         │
│ Updated 2 hours ago     │
└─────────────────────────┘

┌─────────────────────────┐
│ SRS vs Technical Docs   │
│                         │
│ 21 Covered              │
│ 7 Gaps                  │
│                         │
│ Updated yesterday       │
└─────────────────────────┘
```

## Empty state

If there are no analyses:

```text
No analyses yet.

Compare two sets of documents and discover
what is covered, missing, conflicting, or unclear.

[ Create your first analysis ]
```

---

# 6. New Analysis Flow

The most important new UI flow.

## Step 1 — Analysis Type

```text
Create New Analysis

What do you want to analyze?

┌─────────────────────────────┐
│ Compare Requirements        │
│ Find gaps between documents │
└─────────────────────────────┘

┌─────────────────────────────┐
│ Resume vs Job Description   │
│ Find missing or weak areas  │
└─────────────────────────────┘

┌─────────────────────────────┐
│ Custom Analysis             │
│ Define your own comparison  │
└─────────────────────────────┘
```

Keep the first version simple.

Do not create too many configuration options.

---

# 7. Document Upload Screen

The user needs to understand the difference between the two document groups.

## Reference / Expected Documents

Heading:

> **What should exist?**

Description:

> Upload the documents that define the expected requirements, standards, or target state.

Examples:

- Job Description
- SRS
- BRD
- Requirements
- Standards
- Policies

Upload area:

```text
┌──────────────────────────────────────────────┐
│                                              │
│        Drop reference documents here         │
│                                              │
│          or [ Browse Files ]                 │
│                                              │
│        PDF · DOCX · TXT                      │
│                                              │
└──────────────────────────────────────────────┘
```

---

# 8. Existing Documents

Heading:

> **What currently exists?**

Description:

> Upload the documents that describe the current state.

Examples:

- Resume
- SDD
- API documentation
- Existing project documentation

Upload area:

```text
┌──────────────────────────────────────────────┐
│                                              │
│         Drop existing documents here         │
│                                              │
│          or [ Browse Files ]                 │
│                                              │
│        PDF · DOCX · TXT                      │
│                                              │
└──────────────────────────────────────────────┘
```

---

# 9. Upload State

After selecting files:

```text
Reference Documents

✓ job-description.pdf
  1.2 MB

✓ requirements.docx
  680 KB


Existing Documents

✓ resume.pdf
  420 KB

✓ technical-doc.docx
  950 KB


                         [ Start Analysis ]
```

Each file should have:

- filename
- file type
- size
- remove action
- processing state

---

# 10. Processing Screen

After starting analysis:

```text
Analyzing your documents

✓ Uploading documents
✓ Extracting text
✓ Processing document structure
● Preparing analysis
○ Finding relevant evidence
○ Generating findings
```

Avoid fake progress percentages.

Show real stages based on backend processing status.

---

# 11. Analysis Overview

After processing:

```text
Resume vs Python Backend JD

Last analyzed: 2 minutes ago

┌───────────┬───────────┬───────────┬───────────┐
│ Covered   │ Partial   │ Missing   │ Conflict  │
│    18     │     4     │     3     │     1     │
└───────────┴───────────┴───────────┴───────────┘

[ Findings ] [ Evidence ] [ Documents ] [ Map ]
```

The summary should be visual but not over-designed.

---

# 12. Findings Page

This is the most important UI screen.

## Header

```text
Resume vs Python Backend JD

18 Covered · 4 Partial · 3 Missing · 1 Conflict

[ Analyze Again ]
```

## Filters

```text
All | Covered | Partial | Missing | Conflict | Unclear
```

Optional:

```text
Search findings...
```

---

# 13. Finding Card

Each finding should be understandable without opening another page.

Example:

```text
┌──────────────────────────────────────────────────────────┐
│ FastAPI                                      ✓ Covered   │
│                                                          │
│ Requirement                                               │
│ Experience with FastAPI for backend API development.     │
│                                                          │
│ Evidence                                                   │
│ "Built REST APIs using FastAPI..."                       │
│                                                          │
│ Source: Resume → Experience → Project X                  │
│                                                          │
│                                    [ View Evidence ]      │
└──────────────────────────────────────────────────────────┘
```

---

# 14. Missing Finding

```text
┌──────────────────────────────────────────────────────────┐
│ Kubernetes                                  ! Missing    │
│                                                          │
│ No supporting evidence was found in the provided        │
│ existing documents.                                      │
│                                                          │
│ Suggested action                                         │
│ Learn Kubernetes fundamentals and add relevant          │
│ project experience if applicable.                        │
│                                                          │
│                         [ View Related Evidence ]         │
└──────────────────────────────────────────────────────────┘
```

Do not use language that implies certainty when the system only has incomplete evidence.

Prefer:

> "No supporting evidence found"

over:

> "You don't know Kubernetes."

---

# 15. Partial Finding

```text
┌──────────────────────────────────────────────────────────┐
│ Docker                                      ◐ Partial    │
│                                                          │
│ Evidence found for Docker-based deployment, but the      │
│ provided documents do not describe production           │
│ container orchestration.                                │
│                                                          │
│ Missing area                                              │
│ Production orchestration details                         │
│                                                          │
│                         [ View Evidence ]                 │
└──────────────────────────────────────────────────────────┘
```

---

# 16. Conflict Finding

```text
┌──────────────────────────────────────────────────────────┐
│ Authentication                            ! Conflict      │
│                                                          │
│ Reference document requires OAuth2.                       │
│ Existing documentation describes JWT-only authentication.│
│                                                          │
│ Reference source: requirements.pdf                        │
│ Existing source: architecture.docx                       │
│                                                          │
│                         [ Compare Evidence ]              │
└──────────────────────────────────────────────────────────┘
```

The UI should clearly distinguish conflicting source statements.

---

# 17. Evidence Drawer / Panel

Clicking:

> View Evidence

should open a side panel or detail view.

Example:

```text
Evidence

FastAPI

Requirement
Experience with FastAPI.

Source
resume.pdf

Location
Experience → RateBotAi

Matched text
────────────────────────────────────
"Developed backend APIs using
FastAPI and PostgreSQL..."
────────────────────────────────────

Why this evidence matters

The text directly mentions FastAPI
backend API development.

[ Open Document ]
```

Evidence should feel auditable.

---

# 18. Document Viewer

The user should eventually be able to inspect the original document.

Recommended layout:

```text
┌─────────────────────┬──────────────────────────────────────┐
│ Documents           │ Document Viewer                      │
│                     │                                      │
│ resume.pdf          │  Resume                              │
│ requirements.pdf    │                                      │
│ technical.docx      │  ...document content...              │
│                     │                                      │
│                     │  Highlighted evidence                │
└─────────────────────┴──────────────────────────────────────┘
```

If exact highlighting is technically difficult initially, start with:

- source document
- page number where available
- section
- chunk
- matched text

Add advanced highlighting later.

---

# 19. Documents Page

The global Documents page should show:

```text
Documents

[ Search documents... ]        [ Upload ]

┌────────────────────────────────────────────────────┐
│ resume.pdf                  Resume                 │
│ PDF · 420 KB              Updated today             │
│                                                    │
│ Used in: Resume vs Python JD                      │
└────────────────────────────────────────────────────┘
```

Information:

- filename
- type
- size
- processing state
- date
- associated analyses

---

# 20. Analysis Documents Tab

Inside an analysis:

```text
Documents

Reference
────────────────────────────
requirements.pdf
job-description.pdf

Existing
────────────────────────────
resume.pdf
technical-doc.pdf

[ + Add Documents ]
```

Clearly distinguish reference vs existing documents.

---

# 21. Map View

The current Tree functionality can remain.

But rename/reposition it as:

> **Map**

The map is a supporting visualization, not the primary product.

Example:

```text
Analysis
    │
    ├── Authentication
    │      ├── JWT
    │      ├── OAuth2
    │      └── Refresh Token
    │
    ├── Deployment
    │      ├── Docker
    │      ├── Linux
    │      └── Kubernetes
    │
    └── Database
           ├── PostgreSQL
           └── Redis
```

Clicking a node should open its related finding/evidence.

---

# 22. Read View

The existing Read view can remain as a secondary reading experience.

Possible use:

> Read the generated analysis as a structured report.

Sections:

```text
Executive Summary

Coverage Overview

Missing Areas

Partial Areas

Conflicts

Evidence

Recommended Actions
```

---

# 23. Settings

Keep settings simple initially.

Possible sections:

### General

- Theme
- Language (future)

### AI

- Provider configuration
- Model selection

### Storage

- Upload limits
- Storage configuration

### About

- Version
- GitHub repository
- Open-source license

For self-hosted deployments, provider keys should be configured through environment variables rather than exposed in the frontend.

---

# 24. Responsive Design

The UI should work on:

- desktop
- laptop
- tablet

Desktop is the primary target because document analysis is information-heavy.

On smaller screens:

- collapse sidebar
- stack document upload areas
- convert evidence drawer to full-screen panel
- make finding cards single-column

Do not attempt to replicate the entire desktop map experience on mobile in the first version.

---

# 25. Component Structure

Suggested frontend component organization:

```text
components/
├── layout/
│   ├── Sidebar
│   ├── Topbar
│   └── PageContainer
│
├── dashboard/
│   ├── AnalysisCard
│   ├── EmptyState
│   └── SummaryStats
│
├── analysis/
│   ├── AnalysisHeader
│   ├── AnalysisTabs
│   ├── FindingCard
│   ├── FindingFilters
│   ├── EvidencePanel
│   ├── EvidenceReference
│   └── AnalysisSummary
│
├── documents/
│   ├── DocumentUploader
│   ├── DocumentCard
│   ├── DocumentList
│   └── DocumentViewer
│
└── map/
    ├── AnalysisMap
    └── MapNode
```

Adapt this to the existing frontend architecture instead of creating duplicate patterns.

---

# 26. UI States

Every important screen must support:

### Loading

```text
Loading analyses...
```

### Empty

```text
No analyses yet.
Create your first analysis.
```

### Error

```text
Something went wrong.

[ Try Again ]
```

### Processing

Show real processing stages.

### Success

Clearly show completed state.

### Partial failure

For example:

```text
2 of 3 documents processed.

technical-doc.pdf failed to process.

[ Retry ]
```

Do not hide failures.

---

# 27. Status Visual Language

Use consistent visual indicators.

Suggested semantics:

- Covered → success indicator
- Partial → warning indicator
- Missing → neutral/error indicator
- Conflict → strong warning indicator
- Unclear → neutral indicator

Do not rely only on colors.

Use:

- icon
- label
- text

for accessibility.

---

# 28. UX Rules

1. The user should always know what the next action is.
2. Avoid unnecessary configuration.
3. Do not hide important evidence behind multiple clicks.
4. Never make AI-generated content look identical to source evidence.
5. Clearly distinguish:
   - source
   - AI interpretation
   - recommendation
6. Show processing state honestly.
7. Preserve user context when navigating between findings and evidence.
8. Keep the main workflow short.
9. Prefer progressive disclosure for advanced settings.
10. Avoid UI features that do not support the document-analysis workflow.

---

# 29. Visual Design Rules

Keep the existing brand identity where possible.

Recommended direction:

- clean white/light default UI
- restrained purple/indigo accent based on current interface
- dark text
- subtle borders
- moderate corner radius
- minimal shadows
- no excessive glow
- strong typography hierarchy
- consistent spacing

Do not introduce a completely different visual identity unless there is a clear reason.

---

# 30. First UI Sprint

Implement only the following first:

### Dashboard

- New product messaging
- Recent analyses
- New Analysis CTA
- Empty state

### Navigation

- Dashboard
- Analyses
- Documents
- Settings

### New Analysis

- Analysis type
- Reference documents
- Existing documents
- Upload
- Start Analysis

### Analysis shell

- Header
- Summary counts
- Findings tab
- Evidence tab
- Documents tab
- Map tab

### Existing functionality

- Preserve current Map/Tree functionality
- Do not remove working document/topic functionality until replacement is stable

---

# 31. UI Definition of Done

The UI phase is complete when a user can:

1. Open Idea Atlas.
2. Understand what the product does.
3. Create an analysis.
4. Select an analysis type.
5. Upload reference documents.
6. Upload existing documents.
7. Start processing.
8. See processing state.
9. Reach an analysis page.
10. See document groups.
11. See findings.
12. Open evidence.
13. Navigate back without losing context.
14. Open the existing Map view.

The UI does not need advanced AI functionality at this stage.

The goal is to establish the correct product workflow before deeper backend/RAG development.

---

# 32. Instruction for Claude

Before changing the frontend:

1. Inspect the existing frontend structure.
2. Reuse existing components where practical.
3. Do not rewrite the entire frontend.
4. Preserve working Map/Tree functionality.
5. Implement the new information architecture incrementally.
6. Keep the current visual identity unless a change is necessary.
7. Do not add unnecessary animation or decorative effects.
8. Make loading, empty, error, processing, and success states explicit.
9. Keep API calls separated from presentation components.
10. Do not invent backend endpoints. If an endpoint does not exist, use a clear temporary/mock state only where necessary and document it.
11. After each meaningful UI change, verify the application locally.
12. Report which files/components were changed.
13. Keep the UI aligned with this document.

## Immediate UI task

Start with:

> **Dashboard → New Analysis → Document Upload → Analysis Shell**

Do not implement advanced findings/evidence behavior until the corresponding backend contracts are available.

---

# 33. Product UI North Star

The user should enter Idea Atlas and immediately understand:

> **"I give Idea Atlas the documents that define what should exist and the documents that describe what currently exists. It shows me what is covered, missing, conflicting, or unclear — and lets me inspect the evidence."**
