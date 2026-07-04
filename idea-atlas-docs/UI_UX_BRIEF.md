# UI/UX design brief — Idea Atlas

Companion to `APP_FLOW.md`. This sets the visual and interaction direction
so the build doesn't default to generic AI-dashboard styling.

## 1. Design principle

The graph is the product. Every other UI element (input box, side panel,
depth toggle) should feel like it's in service of keeping the graph
uncluttered and readable — not competing with it for attention. When in
doubt, simplify the chrome around the graph, not the graph itself.

## 2. Visual direction

- **Background:** plain, calm, near-white or near-black (support both light
  and dark mode — this is a tool people will stare at while thinking, dark
  mode matters more here than in a typical dashboard)
- **Center node (the topic):** visually distinct from sub-concept nodes —
  larger, bolder border or fill, so the eye knows where the "center of
  gravity" is at a glance
- **Sub-concept nodes:** consistent size, rounded rectangles, enough
  internal padding that text never touches the edge
- **Edges (connecting lines):** thin, low-contrast by default; only the
  edges connected to the currently-selected node should highlight, so
  clicking a node visually traces its relationships instead of leaving the
  whole graph equally busy
- **Typography:** one clear sans-serif for node labels (legible at small
  sizes since nodes are small), a second face (can be the same family,
  different weight) for the side-panel explanation text, which will be
  read more slowly and benefits from slightly more generous line-height
- **Color use:** color should mean something, not decorate. Suggest: the
  center node and its direct children share one color family; each
  subsequent expansion level shifts slightly (e.g. a touch lighter or a
  neighboring hue) so depth in the tree is visually readable without
  reading any text at all

## 3. Layout

- **Default view:** full-screen graph canvas, pannable and zoomable (React
  Flow gives you this for free)
- **Input:** a single search-bar-style input, persistent at the top, so
  starting a new map never requires navigating away from wherever you are
- **Side panel (node detail):** slides in from the right when a node is
  selected, doesn't cover the graph, dismissible by clicking elsewhere on
  the canvas or pressing Escape
- **Recent maps:** a collapsible panel (left side or a simple dropdown from
  the input) — this is secondary navigation, shouldn't compete visually
  with the graph

## 4. Key interactions

- **Click a node:** opens the side panel with its explanation — instant,
  no loading state needed (already in memory from generation)
- **Click "Expand":** new nodes animate in from the parent node's position
  (a brief, subtle transition — under 300ms — communicates "these came from
  here" without feeling slow)
- **Depth toggle:** a simple 3-position control (gist / standard / expert)
  inside the side panel — switching shows a brief loading state only within
  the panel, the graph itself never blocks
- **Drag nodes:** users should be able to manually reposition nodes if the
  auto-layout overlaps or feels wrong; positions persist when the map is saved
- **Keyboard:** Escape closes the side panel, Enter submits the topic input
  — minimum keyboard support, not a full keyboard-nav system for v1

## 5. Loading and empty states

- **Initial map generation:** show a skeleton — a faint center node pulsing
  while sub-nodes "pop in" once ready — communicates "something structural
  is being built," not a generic spinner
- **Empty Recent maps:** a short, plain-language empty state ("Your
  generated maps will show up here") — not a blank gap that looks broken
- **Node expand loading:** a small loading dot directly on the node being
  expanded, not a full-screen overlay — the rest of the graph stays usable

## 6. Accessibility baseline (don't skip this)

- Color is never the only signal — depth/level differences should also be
  readable via node size or border weight, not hue alone
- All interactive elements (nodes, buttons, toggle) need visible keyboard
  focus states
- Side panel text needs sufficient contrast in both light and dark mode
- Respect `prefers-reduced-motion` for the node-expand animation

## 7. What to explicitly avoid

- Generic "AI chatbot" styling — no message bubbles, no chat-style
  scrollback; this is a spatial tool, not a conversation
- Overloading the graph with controls (zoom buttons, minimap, legend, etc.
  all visible at once) — start minimal, add chrome only if real usage shows
  it's needed
- A loading spinner that gives no sense of progress on something that can
  take several seconds — always prefer a skeleton or partial-content state
