# PRD — Idea Atlas

## 1. Summary

Idea Atlas is a single-user, open-source web app that turns any topic into an
explorable map of understanding: a central concept, branching sub-concepts,
click-to-expand explanations, and a depth control (gist / standard / expert).
It runs entirely on the user's own machine using a local, open-weight AI
model — no accounts, no cloud costs, no API keys.

## 2. Problem statement

Understanding a new idea is bottlenecked by format, not availability. The
information already exists — in an article, a paper, a topic you could
search — but it arrives as a wall of text at one fixed depth, with no
visible structure. You can't see how the pieces relate before reading
everything, and you can't control how deep an explanation goes. Most
"summarizer" tools just produce a shorter wall of text, which doesn't solve
the structural problem.

## 3. Goal

Give one person a tool where typing a topic produces a navigable map of that
topic's sub-concepts and their relationships, where any node can be expanded
further or re-explained at a different depth, on demand.

## 4. Target user

A single user (you, and anyone who clones the repo) learning something new
and wanting to see its shape before reading deeply. Not built for teams,
multiple accounts, or public hosting in v1.

## 5. Success criteria for v1

- Typing a topic produces a center node plus 6-8 connected sub-concept nodes within a few seconds
- Any node can be clicked to expand into its own sub-concepts
- Any node's explanation can be toggled between gist / standard / expert depth without losing the rest of the map
- A generated map can be saved and reopened later (Postgres-backed)
- The whole thing runs offline once the local model is downloaded — no paid API required

## 6. In scope (v1)

- Typed-topic input (a word, phrase, or pasted paragraph)
- Interactive node-graph rendering and click-to-expand
- Depth toggle per node (gist / standard / expert)
- Save / reopen previously generated maps
- Single local Postgres database, single user, no auth

## 7. Out of scope (v1) — explicitly deferred

- Document upload (PDF parsing)
- URL / article scraping
- Video transcript ingestion
- Multi-user accounts, sharing, public hosting
- Mobile-optimized layout

These are natural v2 additions once the core loop works, listed in
`IMPLEMENTATION_PLAN.md` as a later phase — don't build them now.

## 8. Core user story

> As a learner, I want to type a topic I don't fully understand and see it
> broken into its component ideas with how they relate, so that I can decide
> what to dig into first and at what depth, instead of reading a wall of
> text top to bottom.

Supporting stories:

- As a user, I want to click any sub-concept and have it expand into its own
  sub-concepts, so I can drill down arbitrarily deep into whatever I don't
  understand.
- As a user, I want to switch a node's explanation between a one-line gist,
  a standard paragraph, and an expert-level explanation, so the depth
  matches what I already know.
- As a user, I want my generated maps saved automatically, so I can come
  back to something I was exploring yesterday without regenerating it.

## 9. Non-functional requirements

- Free and open source end to end — no paid services required to run it
- Runs fully locally (backend, frontend, database, AI model all on one machine)
- Reasonable response time: under ~8 seconds to generate the first map on
  modest consumer hardware (no GPU assumed)
- Codebase should be approachable enough for a contributor to read and
  extend without deep ML background — the AI piece is a black box behind a
  clean interface (see TRD.md)

## 10. Open questions to settle during build (not blockers)

- Exact node-count range per expansion (6-8 is a starting guess — tune once you see real output)
- Whether expert-depth explanations should pull in more structured detail (e.g. lists of sub-points) or stay prose-only
- Graph layout: auto-layout (radial/tree) vs. user-draggable persisted positions
