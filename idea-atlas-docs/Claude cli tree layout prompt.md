We are upgrading the Idea Atlas graph layout from a radial floating node layout
to a top-down collapsible tree layout, and adding a Reading Mode that converts
the map into a clean linear document. This is a frontend-only change.

I am learning while building. Explain everything in simple English as you go.
One step at a time. Wait for my confirmation before moving to the next step.

---

CORE RULES:

1. Do not touch the backend folder
2. Do not change any API endpoint URLs or request shapes
3. Only change files inside frontend/src
4. Build one step at a time, wait for my "looks good, continue" each time
5. After each step explain what you built in 2-3 plain English sentences
6. If anything fails, explain why before fixing it
7. Give 2 interview questions with answers at the end of every major step

---

WHAT WE ARE BUILDING:

Two things:

THING 1 — Top-down collapsible tree layout
  The root node sits at the top center of the canvas.
  First level children appear in a row below the root.
  Clicking a child node expands it downward showing its own children.
  Only the active expanded branch is fully open at any time.
  Unexpanded siblings stay collapsed showing just their label.
  This replaces the current floating radial layout.

THING 2 — Reading Mode
  A toggle button top-right of the canvas switches between:
  - Tree View (the graph/node layout — default)
  - Reading Mode (same content as a clean text document)
  Reading Mode renders all concepts and their explanations
  as a structured article — like a Wikipedia page auto-generated
  from whatever is in the current map.
  Switching between modes is animated with Framer Motion.

---

DESIGN SYSTEM — same as before, no changes:

Background:    #FAFAFA
Surface:       #FFFFFF
Border:        #E4E4E7
Text:          #09090B
Text muted:    #71717A
Accent:        #7C3AED
Accent light:  #EDE9FE
Accent text:   #5B21B6
Font:          Plus Jakarta Sans
Shadow card:   0 1px 3px rgba(0,0,0,0.08)

---

STEP 1 — Update the graph layout utility
File: frontend/src/utils/layoutGraph.js

Replace the entire file with this top-down tree layout using dagre:

import dagre from 'dagre'

export function getLayoutedElements(nodes, edges, expandedNodeIds = new Set()) {
  /*
    Top-down hierarchical tree layout.
    Only renders nodes that are:
    - The root node
    - Direct children of the root
    - Children of expanded nodes (expandedNodeIds contains their parent id)
    Everything else is hidden until its parent is expanded.
  */

  // Step 1: figure out which nodes should be visible
  const visibleNodeIds = new Set()

  const rootNode = nodes.find(n => n.is_root)
  if (!rootNode) return { nodes: [], edges: [] }

  // root is always visible
  visibleNodeIds.add(rootNode.id)

  // first level children are always visible
  const firstLevelChildren = nodes.filter(n => n.parent_id === rootNode.id)
  firstLevelChildren.forEach(n => visibleNodeIds.add(n.id))

  // deeper children: only visible if their parent is in expandedNodeIds
  nodes.forEach(node => {
    if (node.parent_id && expandedNodeIds.has(node.parent_id)) {
      visibleNodeIds.add(node.id)
    }
  })

  const visibleNodes = nodes.filter(n => visibleNodeIds.has(n.id))
  const visibleEdges = edges.filter(
    e => visibleNodeIds.has(e.source_node_id) && visibleNodeIds.has(e.target_node_id)
  )

  // Step 2: run dagre layout on visible nodes only
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({
    rankdir: 'TB',      // top to bottom
    nodesep: 60,        // horizontal gap between siblings
    ranksep: 80,        // vertical gap between levels
    marginx: 40,
    marginy: 40,
  })

  visibleNodes.forEach(node => {
    g.setNode(node.id, {
      width: node.is_root ? 220 : 180,
      height: node.is_root ? 64 : 72,
    })
  })

  visibleEdges.forEach(edge => {
    g.setEdge(edge.source_node_id, edge.target_node_id)
  })

  dagre.layout(g)

  // Step 3: map positions back onto nodes
  const layoutedNodes = visibleNodes.map(node => {
    const pos = g.node(node.id)
    const width = node.is_root ? 220 : 180
    const height = node.is_root ? 64 : 72
    return {
      ...node,
      position: { x: pos.x - width / 2, y: pos.y - height / 2 },
    }
  })

  return { nodes: layoutedNodes, edges: visibleEdges }
}

After creating this file confirm no syntax errors.
Explain in simple English: what does dagre do and what does rankdir TB mean?
Then wait for my confirmation.

---

STEP 2 — Add expandedNodeIds to the Zustand store
File: frontend/src/store/atlasStore.js

Add these two new fields to the store (keep everything else exactly the same):

  expandedNodeIds: new Set(),

  toggleNodeExpanded: (nodeId) => set((state) => {
    /*
      If this node is already expanded, collapse it
      (and also collapse all its descendants).
      If it is not expanded, expand it.
    */
    const next = new Set(state.expandedNodeIds)
    if (next.has(nodeId)) {
      next.delete(nodeId)
    } else {
      next.add(nodeId)
    }
    return { expandedNodeIds: next }
  }),

  collapseAll: () => set({ expandedNodeIds: new Set() }),

After updating confirm the store has no errors.
Explain what a Set is in JavaScript and why we use it here instead of an array.
Then wait.

---

STEP 3 — Update CustomNode to show collapse/expand state
File: frontend/src/components/CustomNode.jsx

The node needs to show whether it is expanded or collapsed, and
whether it has children at all. Update the data shape it receives:

New data shape:
{
  label: string,
  summary: string,
  isRoot: boolean,
  isSelected: boolean,
  isExpanded: boolean,      // is this node currently expanded
  hasChildren: boolean,     // does this node have any children (from API data)
  childCount: number,       // how many children it has
  depth: number,            // 0 = root, 1 = first level, 2 = second level etc
}

ROOT NODE — no change to visual, keep exactly as before

CHILD NODE — update the bottom row:

  If hasChildren = false AND not yet expanded:
    Bottom right: nothing (leaf node, cannot expand)

  If hasChildren = false AND no children exist yet (unexpanded, could expand):
    Bottom right: a small button "+" styled as:
      width 20px height 20px, border-radius 50%
      border 1px solid #E4E4E7
      color #71717A font-size 12px
      display flex align-items center justify-content center
      cursor pointer
      Hover: border #7C3AED color #7C3AED background #EDE9FE
      This button triggers expand (calls the expand API)

  If isExpanded = true (node has been expanded and has visible children):
    Bottom right: a small "-" button with same style as "+" above
      Clicking this collapses the branch (calls toggleNodeExpanded)
    Left of it: "{childCount} concepts" in 11px #7C3AED

  Visual difference by depth level:
    depth 0 (root): as before, black background
    depth 1: full opacity, border #E4E4E7
    depth 2: slightly smaller font (13px label, 11px summary),
      border color #F4F4F5 (more subtle)
    depth 3+: even more muted, label 12px, summary hidden,
      background #FAFAFA

Framer Motion on expand/collapse of children:
  When a node is expanded, its children should animate in:
    initial={{ opacity: 0, y: -10 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.2, staggerChildren: 0.05 }}

After updating: render mock nodes at each depth level to confirm visual.
Explain what staggerChildren does in Framer Motion with a real example.
Then wait.

---

STEP 4 — Update AtlasGraph to use the new layout and expansion system
File: frontend/src/components/AtlasGraph.jsx

Changes needed:

1. Read expandedNodeIds and toggleNodeExpanded from the store

2. Pass expandedNodeIds into getLayoutedElements:
   const { nodes: layoutedNodes, edges: layoutedEdges } =
     useMemo(() =>
       getLayoutedElements(rawNodes, rawEdges, expandedNodeIds),
       [rawNodes, rawEdges, expandedNodeIds]
     )

3. Build React Flow node data correctly:
   For each visible node, compute:
     hasChildren: rawNodes.some(n => n.parent_id === node.id)
     isExpanded: expandedNodeIds.has(node.id)
     childCount: rawNodes.filter(n => n.parent_id === node.id).length
     depth: compute by walking parent_id chain up to root
       (depth 0 = root, depth 1 = root's children, etc)

4. Handle node click:
   When user clicks the "+" button on a node:
     First: call POST /maps/{mapId}/nodes/{nodeId}/expand
     This fetches sub-concepts from the LLM and saves to DB
     On success: update rawNodes and rawEdges in store
     Then: call toggleNodeExpanded(nodeId) to show them

   When user clicks "-" button on a node:
     Call toggleNodeExpanded(nodeId) to hide children
     (data stays in DB, just hidden in layout)

   When user clicks the node card itself (not + or -):
     setSelectedNode as before (opens detail panel)
     Do NOT expand/collapse on card click, only on + / - buttons

5. React Flow fitView:
   Call fitView() after expandedNodeIds changes so the tree
   re-centers itself after expanding/collapsing
   Use useReactFlow() hook to get the fitView function
   Wrap the component in ReactFlowProvider in App.jsx

After updating: test the full expand/collapse cycle:
  Generate a map → click "+" on a node → children appear below it
  Click "-" → children collapse
  Click a different node's "+" → it expands
  Confirm layout re-centers after each expand/collapse.
Explain what useMemo does and why we use it for the layout calculation.
Then wait.

---

STEP 5 — Add the view mode toggle button
File: frontend/src/components/ViewModeToggle.jsx (new file)

A small toggle button that sits in the top-right corner of the graph canvas.
Absolutely positioned, top 16px right 16px, z-index 10.

Visual design:
  Two segments in one pill container (like a segmented control):
    [ 🌿 Tree ] [ 📄 Read ]
  
  Container:
    background #FFFFFF
    border 1px solid #E4E4E7
    border-radius 8px
    padding 3px
    display flex
    box-shadow: 0 1px 3px rgba(0,0,0,0.08)

  Each segment:
    padding 6px 14px
    font 13px Plus Jakarta Sans weight 500
    border-radius 6px
    cursor pointer
    display flex align-items center gap 6px

  Active segment:
    background #7C3AED
    color #FFFFFF
    Framer Motion layoutId="view-mode-indicator" for smooth slide

  Inactive segment:
    background transparent
    color #71717A
    hover: color #09090B

Icons:
  Tree mode: a simple SVG network icon (3 connected nodes, 14px)
  Read mode: a simple SVG lines icon (3 horizontal lines, 14px)
  Draw these as inline SVG, not an icon library

Add viewMode state to the Zustand store:
  viewMode: 'tree',   // 'tree' or 'read'
  setViewMode: (mode) => set({ viewMode: mode }),

ViewModeToggle reads and writes viewMode from the store.

After building: confirm the toggle renders, clicking switches the active state.
Explain what layoutId does in Framer Motion — why does it create a smooth slide?
Then wait.

---

STEP 6 — Build Reading Mode view
File: frontend/src/components/ReadingMode.jsx

This replaces the graph canvas when viewMode = 'read'.
It renders all the concepts in the current map as a structured article.

Layout:
  Max-width 720px centered horizontally
  Padding 48px 24px
  Height 100% overflow-y auto
  Background #FAFAFA

ARTICLE STRUCTURE — auto-generated from the current map data:

  1. TITLE SECTION:
     The root node topic as an H1
     Font: 32px weight 700 #09090B line-height 1.2
     Below it: a muted subtitle:
       "An AI-generated concept map · {node count} concepts"
       14px #71717A

  2. TABLE OF CONTENTS (if map has more than 4 concepts):
     Heading: "In this map" 11px uppercase #71717A letter-spacing 0.08em
     Numbered list of first-level child concept names
     Each is an anchor link that scrolls to that section
     Font: 14px #5B21B6 (violet, looks like a link)
     Hover: underline

  3. CONCEPT SECTIONS (one per first-level child node):
     Each section:

       H2: concept label
         Font: 22px weight 700 #09090B
         Margin-top: 48px
         Padding-bottom: 12px
         Border-bottom: 1px solid #E4E4E7
         id attribute = slugified concept label for anchor links

       Standard explanation (depth = standard):
         Font: 15px #09090B line-height 1.8
         Margin-top: 16px
         If no explanation loaded yet: show a skeleton placeholder

       If this node has been expanded (has grandchildren in the map):
         Sub-sections below for each grandchild:

           H3: grandchild label
             Font: 17px weight 600 #09090B
             Margin-top: 28px
             Left border: 3px solid #EDE9FE

           Grandchild explanation paragraph:
             Font: 14px #09090B line-height 1.75
             Margin-top: 10px

  4. FOOTER:
     Border-top: 1px solid #E4E4E7
     Margin-top: 64px padding-top: 24px
     Text: "Generated by Idea Atlas · Powered by local AI"
     Font: 12px #A1A1AA text-center
     Below it: a "Back to tree view" link in violet
       onClick: setViewMode('tree')

READING MODE DATA:
  Read all nodes and their explanations from the store.
  For each node that has a node_explanation at 'standard' depth, use it.
  For nodes with no explanation loaded yet, show a skeleton line and
  trigger PATCH /maps/{mapId}/nodes/{nodeId}/depth for 'standard'
  to load it, then update when it returns.

Framer Motion on the article entering:
  The whole article div:
    initial={{ opacity: 0, y: 16 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.3, ease: 'easeOut' }}

  Each H2 section:
    initial={{ opacity: 0 }}
    whileInView={{ opacity: 1 }}
    viewport={{ once: true }}
    transition={{ duration: 0.4 }}
  This makes sections fade in as you scroll down — like Medium articles.

After building: generate a map, switch to Reading Mode, confirm article renders.
Scroll down and confirm sections fade in on scroll.
Explain what whileInView does and why it is useful for long documents.
Then wait.

---

STEP 7 — Wire view mode switching in AtlasGraph and App.jsx

In the graph canvas area (the div wrapping AtlasGraph):

  Read viewMode from store.

  If viewMode = 'tree':
    Show: <AtlasGraph />
    Show: <ViewModeToggle /> (absolute top-right)
    Show: <NodeDetailPanel /> if selectedNode exists

  If viewMode = 'read':
    Show: <ReadingMode />
    Show: <ViewModeToggle /> (absolute top-right, stays visible in both modes)
    Hide: <NodeDetailPanel /> (not relevant in reading mode)
    Set selectedNode to null when switching to read mode

Framer Motion between the two views:
  Wrap both in AnimatePresence with mode="wait"
  Tree view exits first (opacity 0, x: -20) then Reading Mode enters
  (opacity 0, x: 20 → opacity 1, x: 0)
  Duration: 0.25s

After wiring: test switching between tree and reading mode several times.
Confirm NodeDetailPanel closes when switching to reading mode.
Explain what AnimatePresence mode="wait" does vs the default mode.
Then wait.

---

STEP 8 — Add breadcrumb trail to the graph canvas (tree view only)

When a node is selected in tree view, show a breadcrumb trail
at the TOP of the graph canvas area, below the topbar.

File: frontend/src/components/GraphBreadcrumb.jsx (new file)

Position: absolute top 0 left 0 right 0
Height: 36px
Background: rgba(255,255,255,0.9)
Backdrop-filter: blur(8px)
Border-bottom: 1px solid #E4E4E7
Padding: 0 16px
Display: flex align-items center
z-index: 5

Content:
  Show the full path from root to the selected node:
  "Machine Learning > Neural Networks > Backpropagation"

  Each item: 14px
    Root: #71717A
    Intermediate: #71717A
    Current (last): #09090B weight 600

  Chevron "›" between items: 14px #E4E4E7

  Each item is clickable:
    Clicking an intermediate node: setSelectedNode to that node
    Clicking root: setSelectedNode to null (deselects, shows root node)

  Framer Motion: animate the breadcrumb in from top when selectedNode exists
    initial={{ y: -36, opacity: 0 }}
    animate={{ y: 0, opacity: 1 }}
    exit={{ y: -36, opacity: 0 }}
    transition: duration 0.15s

  When no node is selected: breadcrumb is not shown (AnimatePresence)

How to build the breadcrumb path:
  Starting from selectedNode, walk up parent_id chain until root
  Collect each node's label and id along the way
  Reverse the array so root is first

After building: select a deeply nested node, confirm breadcrumb shows full path.
Clicking an item in the breadcrumb changes the selected node.
Explain what backdrop-filter blur does visually and why it looks good on a canvas.
Then wait.

---

STEP 9 — Add keyboard navigation for the tree

Add these keyboard shortcuts throughout the app:

"/" key:
  Focus the topic input in TopBar (already exists, confirm it still works)

Arrow keys (when a node is selected):
  ArrowDown: select the next sibling node (same parent, next in order)
  ArrowUp: select the previous sibling node
  ArrowRight: if selected node is expanded, select its first child
              if not expanded, trigger expand (call + action)
  ArrowLeft: select the parent node of the currently selected node

"E" key (when a node is selected):
  Trigger expand on the selected node (same as clicking +)

"R" key:
  Toggle between Tree and Reading mode (same as clicking the toggle button)

Escape key:
  If node is selected: deselect (setSelectedNode null)
  If no node selected and input is focused: blur the input
  If in reading mode: switch back to tree mode

How to implement:
  A single useEffect in App.jsx with a keydown listener on window
  Read selectedNode, viewMode, expandedNodeIds from store
  Dispatch the right store action based on key pressed
  Be careful to not trigger shortcuts when user is typing in the input:
    Check if document.activeElement is the topic input before handling keys

After implementing: test all keyboard shortcuts work correctly.
Show me the complete list of shortcuts that work.
Explain why we check document.activeElement before handling keyboard events.
Then wait.

---

STEP 10 — Final polish and full end-to-end test

Do these small quality polish items:

1. Node count badge on the sidebar map list:
   Next to each map's topic name, show a small badge with how many
   nodes that map has: "12 concepts"
   Badge: background #F4F4F5, radius 99px, padding 2px 8px, 11px #71717A

2. Smooth canvas re-center after expand/collapse:
   After toggleNodeExpanded is called, wait 50ms then call fitView()
   with transition: { duration: 0.4 }
   This gives dagre time to recalculate before the camera moves

3. Empty expand result handling:
   If POST /maps/{id}/nodes/{nodeId}/expand returns 0 new concepts
   (the LLM returned nothing useful), show a toast:
   "Nothing new to expand here — try a different node"
   And do NOT call toggleNodeExpanded

4. Collapse All button:
   In the top-left of the graph canvas, a small text button:
   "Collapse all" in 12px #71717A
   Only visible when expandedNodeIds.size > 0
   Clicking calls collapseAll() from the store
   Framer Motion: animate opacity 0 to 1 when it appears

5. Node count display:
   Top-right of canvas, next to the ViewModeToggle:
   "{n} concepts" in 12px #71717A
   Updates live as nodes are expanded

FULL END-TO-END TEST — run through every scenario:

  SCENARIO 1 — Basic flow:
  [ ] Open app → EmptyState visible
  [ ] Click "Machine learning" example chip → map generates
  [ ] LoadingSkeleton shows during generation
  [ ] Tree renders top-down with root at top
  [ ] First level children appear as a row below root

  SCENARIO 2 — Expand/collapse:
  [ ] Click + on a child node → children animate in below it
  [ ] Breadcrumb updates to show path
  [ ] Click - on same node → children collapse
  [ ] Click + on different node → that one expands
  [ ] "Collapse all" button appears and works

  SCENARIO 3 — Node detail:
  [ ] Click a node card → side panel slides in from right
  [ ] Breadcrumb shows full path to this node
  [ ] Toggle depth Gist/Standard/Expert → explanation updates
  [ ] Click "Expand into sub-concepts" → new nodes appear below

  SCENARIO 4 — Reading mode:
  [ ] Click Read toggle → Reading Mode appears with animation
  [ ] Article shows root topic as H1
  [ ] All first-level concepts as H2 sections with explanations
  [ ] Sections fade in as you scroll
  [ ] Click "Back to tree view" → returns to tree
  [ ] Press R key → same toggle works

  SCENARIO 5 — Keyboard navigation:
  [ ] Press / → input focused
  [ ] Click a node, press ArrowDown → next sibling selected
  [ ] Press ArrowRight → expands or selects child
  [ ] Press Escape → node deselected

  SCENARIO 6 — Persistence:
  [ ] Reload the page
  [ ] Map appears in Recent Maps sidebar
  [ ] Click it → map loads with all saved nodes
  [ ] Previously expanded nodes: start collapsed (expansion state
      is UI-only, not persisted — this is correct behaviour)

Tell me the result of each checkbox above.
Fix anything that fails before declaring done.

---

INTERVIEW PREP — give this after Step 10 is fully done and tested:

INTERVIEW PREP — Tree Layout and Reading Mode

Q: Why did you switch from a radial layout to a top-down tree layout?
A: [answer]

Q: What is dagre and how does it compute node positions automatically?
A: [answer]

Q: How did you implement collapsible tree nodes without removing data from the database?
A: [answer]

Q: What is the difference between AnimatePresence mode="wait" and the default?
A: [answer]

Q: What is whileInView in Framer Motion and when is it useful?
A: [answer]

Q: Why does keyboard navigation need to check document.activeElement?
A: [answer]

---

START NOW with STEP 1 — update the layout utility file.
Show me the file content after creating it.
Explain what dagre does in simple English.
Then wait for my confirmation before Step 2.