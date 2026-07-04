# App flow — Idea Atlas

Companion to `PRD.md` and `UI_UX_BRIEF.md`. This walks through every screen
state a user moves through, plus what the frontend and backend are doing at
each step.

## 1. First-time open

**Screen:** empty state. A centered input box with placeholder text like
"Type a topic to explore..." and, below it, an empty "Recent maps" panel
(empty because nothing's been saved yet).

**What's happening:** `GET /maps` runs on load to populate "Recent maps" —
returns an empty list, panel shows a small empty-state message instead of a
blank gap.

## 2. Typing a topic

User types "transformers in AI" and presses enter (or clicks a Generate
button).

**Screen:** input box transitions to a loading state — a subtle pulse or
skeleton graph, not a generic spinner, since the wait can be a few seconds.

**What's happening:** frontend sends `POST /maps` with `{ topic, depth:
"standard" }`. Backend builds the prompt, calls Ollama, validates the JSON,
saves a new map + root node + sub-concept nodes + edges to Postgres, returns
the full map.

## 3. Map rendered

**Screen:** the center node (the topic, visually distinct — larger or
differently colored) with 6-8 sub-concept nodes arranged around it,
connected by lines. Each node shows its label; hovering shows the one-line
summary as a tooltip.

**What's happening:** frontend feeds the returned JSON into React Flow,
which lays out and renders the graph. Map is now in the URL (e.g.
`/maps/{id}`) so it's reloadable/bookmarkable within the local app.

## 4. Selecting a node

User clicks "Attention mechanism."

**Screen:** a side panel slides in showing the node's label, its current
explanation at the active depth, and the depth toggle (gist / standard /
expert). An "Expand this" button sits below the explanation.

**What's happening:** no network call yet — the explanation at the current
depth was already returned when the map was generated, so this is instant
and purely client-side.

## 5. Changing depth on a node

User clicks "expert" in the depth toggle.

**Screen:** explanation text updates in place; a small loading indicator
shows only inside that panel (rest of the graph stays interactive).

**What's happening:** frontend sends `PATCH
/maps/{map_id}/nodes/{node_id}/depth` with `{ depth: "expert" }`. Backend
checks if an expert-depth explanation is already cached for this node — if
yes, returns it immediately; if no, calls the LLM, persists it, returns it.

## 6. Expanding a node

User clicks "Expand this" on the Attention mechanism panel.

**Screen:** 4-6 new nodes appear branching out from "Attention mechanism,"
connected to it (not to the original center node). Graph auto-adjusts
layout so nothing overlaps; user can still drag nodes manually afterward.

**What's happening:** frontend sends `POST
/maps/{map_id}/nodes/{node_id}/expand`. Backend builds a prompt that
includes the parent node's context (so sub-concepts are relevant to
"Attention mechanism specifically," not generic AI sub-topics), calls the
LLM, persists new nodes/edges, returns them.

## 7. Returning to a previous map

User opens the app later, sees "transformers in AI" in the Recent maps
panel, clicks it.

**Screen:** the exact graph as last left it, including any expansions and
depth changes made previously, fully reconstructed.

**What's happening:** `GET /maps/{map_id}` loads all persisted nodes, edges,
and cached explanations from Postgres — no LLM calls needed at all to
reopen a map.

## 8. Error states (must be designed, not an afterthought)

- **Topic generation fails (LLM returns invalid JSON after retries):** input
  box shows an inline error — "Couldn't generate a map for that topic, try
  rephrasing it or try again" — input stays editable, no dead end.
- **Ollama isn't running:** a clear, specific message — "Local AI model
  isn't running. Start Ollama and try again." — not a generic 500 error.
- **Expand fails on an existing node:** the node itself shows a small retry
  affordance, rest of the graph remains usable.

## 9. Empty / edge cases to handle

- Topic input is empty or whitespace-only — disable the generate action,
  don't send a request
- Topic is extremely long (user pastes a paragraph instead of a phrase) —
  still works, just treat it as richer context for the same prompt
- Deleting the currently-open map — redirect back to the empty state, not a
  broken page referencing a map that no longer exists
