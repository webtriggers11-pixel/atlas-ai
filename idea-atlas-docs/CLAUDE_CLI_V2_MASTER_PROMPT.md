# MASTER BUILD PROMPT — Idea Atlas v2: Document Intelligence Upgrade

Paste this entire file into Claude Code as your first message.

---

You are the lead developer and mentor on Idea Atlas. We are upgrading it
from a topic explorer into a document intelligence tool. This build has
5 phases. Build them IN ORDER. Do not skip ahead.

I am learning while building. After every step explain what you built in
2-3 plain English sentences. Wait for my "continue" before the next step.
Give 2 interview questions with answers at the end of every phase.

Read all files in docs/ before starting. The existing app (topic input →
tree → expand → depth toggle → reading mode) must keep working exactly
as it does now. We are ADDING, not replacing.

---

# PHASE A — MULTI-PROVIDER AI (Gemini + Groq + fallback routing)

Why: Groq's free tier has small token-per-minute limits that choke on
documents. Gemini Flash free tier has a 1M token context window and
1,500 requests/day — perfect for document work. We route each task to
the right provider automatically.

## A1 — Add Gemini provider to backend/app/llm.py

- New env variables in .env.example:
    GEMINI_API_KEY=your-key-here
    GEMINI_MODEL=gemini-2.5-flash
- LLM_PROVIDER now supports: ollama | groq | gemini
- Gemini call: POST to
  https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}
  Body format:
    { "contents": [{ "parts": [{ "text": prompt }] }] }
  Response text is at: response.candidates[0].content.parts[0].text
- Keep the exact same JSON validation + retry logic for all providers.
- Never hardcode model names outside env variables.

## A2 — Smart routing in the service layer

Add a function pick_provider(task_type, has_document_context):
- task_type "map_generation" or has_document_context=True → "gemini"
- task_type "gist" or "expand_small" → "groq"
- If the chosen provider is not configured (missing key) → use whichever
  IS configured, log a warning.

## A3 — Automatic fallback on rate limits

Wrap every LLM call: if the response is HTTP 429 (rate limited),
retry ONCE with the other provider. Log which provider actually served
each request into the llm_logs table (add provider column if missing).

## A4 — Test Phase A

Write a small script scripts/test_providers.py that:
- Sends one small prompt through groq, one through gemini
- Prints provider name, response time, and first 100 chars of response
- Simulates a 429 by temporarily using a bad model name and confirms
  fallback triggers

Show me the output. Then wait for confirmation before Phase B.

INTERVIEW PREP — Phase A: 2 Q&As about multi-provider routing and
why rate-limit fallback matters in production systems.

---

# PHASE B — DOCUMENT UPLOAD + RAG (the core of this whole upgrade)

Why: users need to upload an SDD/PDF/text and get a map built from THAT
document only — with the AI forbidden from guessing beyond it.

## B1 — Dependencies

pip install python-docx pypdf sentence-transformers pgvector
Confirm all install. sentence-transformers downloads the
all-MiniLM-L6-v2 model (~80MB) on first use — that is expected.

## B2 — Database: new tables via Alembic migration

documents:
  id UUID pk, map_id UUID fk→maps (nullable until map created),
  filename text, source_type text (docx|pdf|pasted),
  full_text text, created_at timestamptz

document_chunks:
  id UUID pk, document_id UUID fk→documents cascade delete,
  chunk_index int, content text,
  embedding vector(384),        -- pgvector, MiniLM output size
  section_hint text nullable,   -- nearest heading found above the chunk
  created_at timestamptz

Enable pgvector extension in the migration:
  CREATE EXTENSION IF NOT EXISTS vector;
Index: ivfflat or hnsw index on document_chunks.embedding
(use hnsw if the installed pgvector version supports it).

Also add to nodes table: source_type text default 'topic'
('topic' = generated from typed topic, 'document' = grounded in a doc).

## B3 — Text extraction: backend/app/services/document_service.py

- extract_text(file, source_type):
    docx → python-docx, join paragraphs, keep heading text
    pdf → pypdf page-by-page
    pasted → use as-is
- Reject files over 10MB with a clear error.

## B4 — Chunking

- chunk_text(full_text): split into chunks of ~500 words with 50-word
  overlap between consecutive chunks.
- Track the nearest heading above each chunk into section_hint
  (for docx use real heading styles; for pdf/pasted use lines that are
  short + title-cased as a heuristic — imperfect is fine).
- IMPORTANT: after building chunking, print the first 3 chunks of a real
  test document to the console so I can eyeball them. Bad chunking is
  the number one silent RAG failure.

## B5 — Embeddings

- backend/app/services/embedding_service.py
- Load all-MiniLM-L6-v2 once at startup (module-level, lazy).
- embed_texts(list[str]) → list of 384-dim vectors,
  normalize_embeddings=True.
- This runs locally and fast even on CPU — it is NOT the slow-LLM
  problem. Explain to me why embedding models are small and fast while
  generation models are big and slow.

## B6 — Upload endpoint

POST /documents  (multipart file OR json {text, filename})
Flow: extract → chunk → embed all chunks → store document + chunks →
then generate the map:
  - Send the document's headings + first chunk of each section to
    GEMINI with the prompt: "Build a concept hierarchy of THIS document.
    Return only JSON: {concepts:[{label, summary, parent_label|null}]}.
    Base it ONLY on the document content provided."
  - Create the map, nodes (source_type='document'), edges as usual.
Return the full map. Show a clear multi-step progress in the response
timing logs: extracted → chunked (n) → embedded → map built.

## B7 — Grounded retrieval for explanations

New function retrieve_chunks(document_id, query, k=4):
  embed the query → pgvector cosine similarity search → top k chunks
  with their similarity scores and section_hints.

Update the depth-explanation flow: when a node's map is document-based,
build the prompt as:

  "You are explaining a concept from a specific document.
   DOCUMENT EXCERPTS:
   {chunks with section hints}
   RULES:
   - Answer ONLY from the excerpts above.
   - If the excerpts do not contain the answer, reply exactly:
     'The document does not cover this.'
   - Never use outside knowledge. Never guess.
   Explain '{node label}' at {depth} depth."

Store with each explanation: the chunk ids used and their best
similarity score (add columns source_chunk_ids jsonb, confidence float
to node_explanations via migration).

## B8 — Test Phase B end to end

Upload a real docx (I will provide one). Then:
- Show me the extracted chunk count
- Show me the generated map JSON
- Click-equivalent: call the depth endpoint for 2 nodes, show me the
  explanation AND the retrieved chunks it was grounded on
- Ask about something NOT in the document and confirm the response is
  "The document does not cover this."

Wait for my confirmation before Phase C.

INTERVIEW PREP — Phase B: 2 Q&As covering what RAG is and why
grounding prevents hallucination.

---

# PHASE C — GAP CHECK (the money feature)

Why: when a document under-specifies something, we surface it BEFORE a
developer builds against it.

## C1 — Gap detection logic

New endpoint POST /maps/{map_id}/gap-check (document maps only):
For each node:
  1. retrieve_chunks(document_id, node.label, k=4)
  2. If best similarity < threshold (start at 0.35, make it an env var
     GAP_THRESHOLD) → mark node as under-documented.
  3. For flagged nodes, ONE Gemini call:
     "A developer must implement '{label}'. Here is everything the
      document says about it: {chunks}. List 2-4 specific questions a
      developer would need answered that this text does NOT answer.
      Return only JSON: {questions:[string]}"

## C2 — Storage

New table node_gaps (Alembic migration):
  id, node_id fk, question text, status text default 'open'
  (open|answered), answer text nullable, created_at.
Add to nodes: gap_status text default 'none' (none|flagged).

## C3 — Endpoints

GET  /maps/{map_id}/gaps            → all gap questions grouped by node
PATCH /gaps/{gap_id}                → save an answer, set status answered
When a gap is answered: append the answer text as a new document chunk
(embed it, store it) so future explanations can use it. Explain to me
why this "answers become part of the document" loop is powerful.

## C4 — Test: run gap-check on the uploaded doc, show me flagged nodes
and their generated questions. Wait for confirmation.

INTERVIEW PREP — Phase C: 2 Q&As about similarity thresholds and
shift-left defect detection.

---

# PHASE D — FRONTEND: FILL THE 7 UX GAPS

Keep the existing design system (white bg #FAFAFA, violet #7C3AED,
Plus Jakarta Sans, Framer Motion). All animations under 250ms.

## D1 — Dual entry point (Gap 1)

Replace EmptyState with two side-by-side cards:
  Card 1 "Explore a topic" — the existing input flow
  Card 2 "Understand a document" — drag-drop zone + browse button
    (.docx, .pdf) + a "paste text instead" link that opens a textarea
Upload shows step progress: "Reading document → Breaking into
concepts → Building your map" with a violet progress line, each step
label lighting up as backend timing allows (poll or just sequential
optimistic steps).

## D2 — Node weight signals (Gap 2)

On each node: small "{n} sub-concepts" count when it has children
available. Content-heavy nodes (more/longer chunks behind them —
backend returns a weight score per node) get font-weight 700 label;
light nodes stay 500.

## D3 — Read tracking + progress (Gap 3)

Zustand: readNodeIds Set, mark read when a node's panel is opened.
Unread nodes show a small violet dot top-right (like unread email).
Top of canvas: slim progress text "Explored 5 of 9 concepts" with a
thin violet progress bar. Persist read state per map in localStorage
is NOT allowed in our stack docs — persist via a PATCH to a new
nodes.is_read boolean column instead (add migration).

## D4 — Gap markers on the tree (Gap 4)

Flagged nodes (gap_status='flagged'): amber (#F59E0B) left border +
small amber triangle-! badge. A "Gaps" button in the top bar of the
canvas with a count badge, opening a right panel listing open questions
grouped by node. Each question has an answer textarea + Save (calls
PATCH /gaps/{id}). Answered questions turn the marker from amber to a
subtle green check. First discovery: markers pulse ONCE then stay still.

## D5 — Source trust line (Gap 7)

In the NodeDetailPanel for document maps, under every explanation:
  "From your document · {section_hint}" in 12px muted with a small
  document icon. If the explanation is "The document does not cover
  this" → render it in amber italic with the triangle icon instead of
  normal text, plus a button "Add to gap questions".

## D6 — Shared position Tree ↔ Reading mode (Gap 5)

NodeDetailPanel gets a "Read this section" link → switches to Reading
Mode scrolled to that node's H2 (scrollIntoView smooth). Every Reading
Mode H2 gets a hover icon "View in tree" → switches back with that node
selected and fitView centered on it. Store lastFocusedNodeId in Zustand
to make both directions work.

## D7 — Plain depth labels (Gap 6)

Depth toggle: keep Gist/Standard/Expert labels but add title tooltips:
"One line" / "A short paragraph" / "Full detail". Default remains
standard.

Test each of D1-D7 in the browser as you build it. Wait for my
confirmation between each D step.

INTERVIEW PREP — Phase D: 2 Q&As about progressive disclosure and
trust signals in AI UIs.

---

# PHASE E — FULL END-TO-END TEST + POLISH

Run and show me results for every scenario:

1. Topic flow still works exactly as before (regression check)
2. Upload the docx → progress steps → map renders with weights
3. Open 3 nodes → progress bar says "3 of N" → reload page → still 3
4. Run Gap Check → amber markers appear → open Gaps panel →
   answer one question → marker turns green → ask that node's
   explanation again → the answer content is now included
5. Explanation shows source line; unanswerable question shows amber
   "document does not cover this"
6. Tree → "Read this section" → lands on right H2 → "View in tree" →
   back with node selected
7. Force a Groq 429 (bad key temporarily) → fallback to Gemini works,
   llm_logs shows provider used
8. All existing keyboard shortcuts still work

Fix anything that fails. Then give me a final consolidated
INTERVIEW PREP section: 8 Q&As covering RAG, chunking, embeddings,
pgvector, grounding, gap detection, provider routing, and one system
design question: "Walk me through what happens end to end when a user
uploads a document."

---

START NOW with PHASE A, step A1. Show me the updated llm.py plan first,
then implement. Wait for my confirmation after every step.
