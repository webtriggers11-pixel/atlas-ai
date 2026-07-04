We are rebuilding the entire frontend UI of Idea Atlas from scratch.
The current UI is outdated and not usable by end users. We are switching
to a clean, minimal, industry-standard 2026 design — white background,
strong typography, violet accent color — like Perplexity AI or Linear.

I am learning while building. After each component explain what you built
and why in simple English. Do not skip ahead. One component at a time.

---

RULES — follow these exactly:

1. Do not touch anything in the backend folder
2. Do not change any API endpoint URLs or request shapes
3. Only rebuild everything inside frontend/src
4. Build one component at a time, in the exact order listed below
5. After each component: run the dev server, confirm no console errors,
   then explain what you just built in 2-3 plain English sentences
6. If anything fails, explain what went wrong before fixing it
7. Every component file needs a one-line comment at the top explaining
   what it does
8. Wait for me to say "looks good, continue" before moving to next component

---

DESIGN SYSTEM — use these exact values everywhere, no exceptions:

Background:     #FAFAFA
Surface/cards:  #FFFFFF
Border:         #E4E4E7
Border hover:   #A1A1AA
Text:           #09090B
Text muted:     #71717A
Accent:         #7C3AED
Accent light:   #EDE9FE
Accent text:    #5B21B6
Root node bg:   #09090B
Root node text: #FAFAFA

Font: Plus Jakarta Sans
Base size: 15px
Line height: 1.6
Border radius: nodes 10px, buttons 8px, panels 14px
Box shadow: 0 1px 3px rgba(0,0,0,0.08) on cards only

---

STEP 1 — Install libraries first, confirm each installs with no errors:

npm install framer-motion
npm install react-hot-toast
npm install @xyflow/react
npm install dagre
npm install @fontsource/plus-jakarta-sans

After all install confirm: "All libraries installed successfully"
Then wait for me before continuing.

---

STEP 2 — Global styles in frontend/src/index.css

Replace entire file with:

@import '@fontsource/plus-jakarta-sans/400.css';
@import '@fontsource/plus-jakarta-sans/500.css';
@import '@fontsource/plus-jakarta-sans/600.css';
@import '@fontsource/plus-jakarta-sans/700.css';

:root {
  --bg: #FAFAFA;
  --surface: #FFFFFF;
  --border: #E4E4E7;
  --border-hover: #A1A1AA;
  --text: #09090B;
  --text-muted: #71717A;
  --accent: #7C3AED;
  --accent-light: #EDE9FE;
  --accent-text: #5B21B6;
  --radius-node: 10px;
  --radius-btn: 8px;
  --radius-panel: 14px;
  --shadow-card: 0 1px 3px rgba(0,0,0,0.08);
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 15px;
  line-height: 1.6;
  background: var(--bg);
  color: var(--text);
  -webkit-font-smoothing: antialiased;
}

html, body, #root {
  height: 100%;
  width: 100%;
  overflow: hidden;
}

Confirm this renders correctly. Then wait.

---

STEP 3 — Zustand store: frontend/src/store/atlasStore.js

import { create } from 'zustand'

const useAtlasStore = create((set) => ({
  currentMap: null,
  nodes: [],
  edges: [],
  selectedNode: null,
  depth: 'standard',
  sidebarOpen: true,
  isGenerating: false,
  isExpanding: false,
  recentMaps: [],

  setCurrentMap: (map) => set({ currentMap: map }),
  setNodes: (nodes) => set({ nodes }),
  setEdges: (edges) => set({ edges }),
  setSelectedNode: (node) => set({ selectedNode: node }),
  setDepth: (depth) => set({ depth }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setIsGenerating: (v) => set({ isGenerating: v }),
  setIsExpanding: (v) => set({ isExpanding: v }),
  setRecentMaps: (maps) => set({ recentMaps: maps }),
}))

export default useAtlasStore

Confirm file created. Then wait.

---

STEP 4 — TopBar component: frontend/src/components/TopBar.jsx

What it does: top navigation bar with logo, topic input, generate button

Exact layout left to right:
- Left: violet square (8x8px #7C3AED rounded 3px) + 
  "Idea Atlas" text 18px weight 600
- Center: input field 480px wide max
  placeholder "Explore any topic..."
  border 1px solid #E4E4E7, radius 8px, height 38px, font 14px
  left padding 36px (for search icon inside left)
  On focus: border #7C3AED, box-shadow 0 0 0 3px #EDE9FE
  Small search icon inside left (14px, color #71717A)
  When isGenerating=true: small violet spinner inside right
  Keyboard hint text inside right: "Press / to focus" 
  11px #71717A, hide when user is typing
- Right: Generate button
  background #7C3AED, text white, height 38px, padding 0 18px
  radius 8px, font 14px weight 500
  Hover: background #6D28D9
  Disabled when input empty: opacity 0.4 cursor not-allowed
  Framer Motion whileTap={{ scale: 0.97 }}

TopBar itself:
  height 56px, background #FFFFFF, 
  border-bottom 1px solid #E4E4E7
  padding 0 20px
  display flex align-items center gap between sections

Wire up:
- Input value controlled by local state (topic string)
- Pressing Enter OR clicking Generate: 
  call POST /maps with { topic, depth: 'standard' }
  set isGenerating true before call, false after
  on success: call setCurrentMap, setNodes, setEdges in store
  on error: show toast "Could not generate — try again"
- Press "/" anywhere on page focuses this input
  (use useEffect with keydown listener)
- Press Escape: blur input

After building: confirm it renders, input works, button disables when empty.
Explain what controlled input means in React.
Then wait.

---

STEP 5 — Sidebar component: frontend/src/components/Sidebar.jsx

What it does: left panel showing list of previously saved maps

Layout:
  width 260px when open, collapses to 40px when closed
  background #FFFFFF
  border-right 1px solid #E4E4E7
  height 100% (full height minus topbar)

When open:
  padding 16px

  Header row:
    "RECENT MAPS" text: 11px uppercase letter-spacing 0.08em 
    color #71717A weight 600
    Collapse arrow button far right: 
      chevron icon rotates 180deg on collapse
      Framer Motion animate rotation

  Map list:
    On mount: fetch GET /maps, store in recentMaps via setRecentMaps
    Each item: padding 10px 12px, radius 8px, cursor pointer
      Topic name: 14px #09090B weight 500, 
        truncate with ellipsis if long (max-width 180px)
      Timestamp: 12px #71717A below topic name
      Hover: background #F4F4F5
      Active map: background #EDE9FE, 
        border-left 3px solid #7C3AED,
        topic name color #5B21B6
      Delete X button: appears on item hover, far right
        small 16px X icon, color #71717A
        hover color #EF4444
        on click: DELETE /maps/{id}, remove from list, 
          show toast "Map deleted"
          if deleted map was currentMap: setCurrentMap(null)

    Clicking a map item:
      fetch GET /maps/{id}
      call setCurrentMap, setNodes, setEdges
      highlight that item as active

  Empty state (no maps yet):
    centered inside sidebar
    small compass icon (32px, #E4E4E7)
    "No maps yet" 14px #71717A
    "Generate your first topic above" 12px #A1A1AA

When collapsed (sidebarOpen=false):
  width 40px
  show only the collapse toggle button
  no content visible

Framer Motion:
  animate width: sidebarOpen ? 260 : 40
  transition duration 0.2s ease
  map list items stagger entrance: 
    each delays 0.05s more than previous

After building: test that recent maps load and clicking one loads the map.
Explain what useEffect is and when it runs.
Then wait.

---

STEP 6 — EmptyState component: frontend/src/components/EmptyState.jsx

What it does: shows in the graph canvas when no map is loaded

Centered in its container (flexbox center both axes):

  Large circle: 120px diameter, border 2px solid #E4E4E7, radius 50%
    Inside: a network icon (SVG, 40px, color #7C3AED)
    Use this SVG path for the icon (a simple nodes-and-lines icon):
    three circles connected by lines, draw it simply with SVG

  Heading: "Explore any idea"
    20px weight 700 #09090B margin-top 24px

  Subtext: "Type a topic above and press Generate"
    second line: "Click any concept to go deeper"
    14px #71717A text-center max-width 260px margin-top 8px

  Example chips row (margin-top 24px, gap 8px, flex wrap center):
    Three chips: "Quantum computing" | "Climate change" | "Machine learning"
    Each chip: 
      border 1px solid #E4E4E7, radius 99px
      padding 6px 14px, font 13px color #71717A
      cursor pointer
      Hover: border #7C3AED, color #5B21B6, background #EDE9FE
      Framer Motion whileHover whileTap scale 0.97
    Clicking a chip: 
      fills the topic input with that chip text
      AND immediately triggers map generation for it
      (call the same generate function from TopBar)

After building: confirm centered layout, chips are clickable.
Explain what Framer Motion whileHover does in one sentence.
Then wait.

---

STEP 7 — Custom node: frontend/src/components/CustomNode.jsx

What it does: the visual design of each node on the React Flow graph

This is a React Flow custom node — it receives data as props automatically
from React Flow. The prop shape is: { data: { label, summary, isRoot,
isSelected, isExpanded, childCount } }

ROOT NODE (data.isRoot = true):
  width 200px min-height 64px
  background #09090B, border-radius 10px
  padding 16px 20px
  Label text: white 15px weight 600
  Small violet dot bottom right: 6px circle background #7C3AED
  No React Flow handles (set in nodeTypes, handles hidden via CSS)

CHILD NODE (data.isRoot = false):
  width 180px auto height
  background #FFFFFF
  border 1px solid #E4E4E7
  border-radius 10px
  padding 14px 16px
  box-shadow var(--shadow-card)
  
  Label: 14px #09090B weight 600
  Summary: 12px #71717A margin-top 4px
    max 2 lines then overflow ellipsis
    display -webkit-box, -webkit-line-clamp 2

  Bottom row (flex space-between margin-top 10px):
    Left: if data.isExpanded show "{childCount} concepts" 
      12px #7C3AED weight 500
    Right: if not expanded show expand arrows icon 
      (⤢ or similar, 12px #A1A1AA)

  Hover state: border-color #7C3AED background #FAFAFA
  Selected state: border-color #7C3AED background #EDE9FE
    label color #5B21B6
  Expanded state border: 1px solid #A78BFA

Framer Motion on the node div:
  initial={{ opacity: 0, scale: 0.8 }}
  animate={{ opacity: 1, scale: 1 }}
  transition={{ duration: 0.2, ease: 'easeOut' }}

Hide all React Flow handles with CSS:
  .react-flow__handle { display: none !important; }

After building: render 2-3 mock nodes in isolation to confirm styles.
Explain what a React Flow custom node is in simple English.
Then wait.

---

STEP 8 — Graph layout helper: frontend/src/utils/layoutGraph.js

What it does: takes flat nodes and edges arrays and computes positions
using dagre so nodes don't overlap

import dagre from 'dagre'

export function getLayoutedElements(nodes, edges) {
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'TB', nodesep: 80, ranksep: 100 })

  nodes.forEach((node) => {
    g.setNode(node.id, { 
      width: node.data?.isRoot ? 200 : 180, 
      height: node.data?.isRoot ? 64 : 80 
    })
  })
  edges.forEach((edge) => {
    g.setEdge(edge.source, edge.target)
  })

  dagre.layout(g)

  return {
    nodes: nodes.map((node) => {
      const { x, y } = g.node(node.id)
      return { ...node, position: { x: x - 90, y: y - 40 } }
    }),
    edges,
  }
}

After building: no visual yet, just confirm file created no syntax errors.
Then wait.

---

STEP 9 — AtlasGraph component: frontend/src/components/AtlasGraph.jsx

What it does: the main React Flow canvas that renders the concept map

Import ReactFlow, Background, Controls from @xyflow/react
Import CustomNode from ./CustomNode
Import getLayoutedElements from ../utils/layoutGraph
Import useAtlasStore

Setup:
  const nodeTypes = useMemo(() => ({ custom: CustomNode }), [])

  Read nodes, edges, selectedNode, setSelectedNode from store

  Before passing to ReactFlow, run nodes+edges through getLayoutedElements

  Map API nodes to React Flow nodes:
    each node gets type: 'custom'
    data: {
      label: node.label,
      summary: node.summary (from node_explanations where depth=standard),
      isRoot: node.is_root,
      isSelected: node.id === selectedNode?.id,
      isExpanded: node has children in the nodes array,
      childCount: count of nodes where parent_id = this node id
    }

  Map API edges to React Flow edges:
    each edge: { 
      id, 
      source: source_node_id, 
      target: target_node_id,
      style: { 
        stroke: selectedNode and (edge.source===selectedNode.id 
          or edge.target===selectedNode.id) 
          ? '#A78BFA' : '#E4E4E7',
        strokeWidth: 1.5
      },
      type: 'smoothstep'
    }

ReactFlow component props:
  nodes={layoutedNodes}
  edges={layoutedEdges}
  nodeTypes={nodeTypes}
  nodesConnectable={false}
  nodesDraggable={true}
  fitView={true}
  fitViewOptions={{ padding: 0.3 }}
  minZoom={0.3}
  maxZoom={1.5}
  onNodeClick={(event, node) => setSelectedNode(node)}
  onPaneClick={() => setSelectedNode(null)}

Background component:
  variant="dots" color="#E4E4E7" gap={24} size={1}

Controls component:
  showInteractive={false}
  style custom: white bg, violet hover, radius 8px

Show LoadingSkeleton when isGenerating=true
Show EmptyState when no currentMap and not generating

After building: test that generating a map shows nodes on the canvas.
Explain what fitView does in React Flow.
Then wait.

---

STEP 10 — LoadingSkeleton: frontend/src/components/LoadingSkeleton.jsx

What it does: animated placeholder shown while map is generating

Centered absolutely in the graph canvas

One large skeleton (200x64px, radius 10px, background #E4E4E7)
in the center

6 smaller skeletons (180x60px, radius 10px, background #F4F4F5)
arranged in a rough circle around center using absolute positioning:
  top, top-right, right, bottom-right, bottom, left

Thin lines from center to each child:
  use SVG absolutely positioned behind the nodes
  lines from center point to each child center point
  stroke #E4E4E7 strokeWidth 1

Framer Motion on every skeleton rectangle:
  animate={{ opacity: [0.4, 0.8, 0.4] }}
  transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
  each child staggered by 0.15s using delay

After building: trigger it by setting isGenerating=true in store temporarily.
Confirm animation runs smoothly.
Then wait.

---

STEP 11 — NodeDetailPanel: frontend/src/components/NodeDetailPanel.jsx

What it does: right-side panel showing details of the clicked node

Position: fixed, right 0, top 56px (below topbar), bottom 0
Width: 360px
Background: #FFFFFF
Border-left: 1px solid #E4E4E7
Padding: 24px
z-index: 10
overflow-y: auto

Framer Motion wrapper (AnimatePresence in App.jsx):
  initial={{ x: 360 }}
  animate={{ x: 0 }}
  exit={{ x: 360 }}
  transition={{ duration: 0.2, ease: 'easeOut' }}

HEADER:
  Close button: top-right, X icon 20px
    background none, border none, cursor pointer
    hover background #F4F4F5, radius 6px, padding 4px
    onClick: setSelectedNode(null)
  
  Breadcrumb (below close button, margin-top 4px):
    Build path from root to current node by walking parent_id chain
    Format: "Root Topic > Parent > Current"
    Font: 12px #71717A, chevrons between items
    Each item clickable: sets that node as selected

  Node label: 20px weight 700 #09090B margin-top 12px

DEPTH TOGGLE (margin-top 20px):
  Label above: "EXPLANATION" 10px uppercase letter-spacing 0.08em #71717A

  Toggle container: 
    background #F4F4F5, radius 8px, padding 3px
    display flex, width 100%

  Three segments: Gist | Standard | Expert
    Each: flex 1, text-align center, height 32px
    line-height 32px, font 13px, cursor pointer
    
    Active segment:
      background #FFFFFF, color #5B21B6, weight 600, radius 6px
      Use Framer Motion layoutId="active-depth" for smooth sliding
    Inactive: color #71717A weight 400

  On segment click:
    setDepth in store
    call PATCH /maps/{mapId}/nodes/{nodeId}/depth with { depth }
    show loading state inside panel (not full screen)
    on success: update explanation text

EXPLANATION TEXT (margin-top 16px):
  When loading: show 3 skeleton lines
    height 16px, radius 4px, background #F4F4F5
    Framer Motion pulse animation
    widths: 100%, 85%, 60%
  
  When loaded: 
    15px #09090B line-height 1.7
    Framer Motion: animate opacity 0 to 1 on text change

RELATED CONCEPTS (margin-top 24px):
  Label: "IN THIS MAP" 10px uppercase #71717A letter-spacing 0.08em
  Chips row (margin-top 8px, flex wrap, gap 8px):
    Show sibling nodes (same parent_id as current node, max 5)
    Each chip: background #F4F4F5, radius 99px, 
      padding 4px 12px, font 12px #71717A
      Hover: border 1px solid #7C3AED, color #5B21B6
      Click: setSelectedNode(that node)

EXPAND BUTTON (margin-top auto, padding-top 24px, border-top 1px solid #E4E4E7):
  Full width height 40px
  border 1.5px solid #7C3AED
  background transparent
  color #7C3AED font 14px weight 500
  radius 8px cursor pointer
  
  Left: + circle icon (16px)
  Text: "Expand into sub-concepts"
  
  Hover: background #EDE9FE
  
  On click:
    set isExpanding true
    show spinner + "Generating..." text inside button
    call POST /maps/{mapId}/nodes/{nodeId}/expand
    on success: 
      update nodes and edges in store
      re-run layout
      set isExpanding false
      show "✓ {count} concepts added" in green for 2 seconds
      then revert button text
    on error: show toast "Could not expand — try again"

  Do not show this button if selectedNode.isRoot is true

After building: click a node, confirm panel slides in.
Click depth toggle, confirm it calls the API.
Click expand, confirm new nodes appear on canvas.
Explain what AnimatePresence does in one sentence.
Then wait.

---

STEP 12 — Wire everything in App.jsx

import TopBar from './components/TopBar'
import Sidebar from './components/Sidebar'
import AtlasGraph from './components/AtlasGraph'
import NodeDetailPanel from './components/NodeDetailPanel'
import { AnimatePresence } from 'framer-motion'
import { Toaster } from 'react-hot-toast'
import useAtlasStore from './store/atlasStore'

Layout (full height, no scroll):

  <div style={{ display:'flex', flexDirection:'column', height:'100vh' }}>
    
    <TopBar />
    
    <div style={{ display:'flex', flex:1, overflow:'hidden' }}>
      
      <Sidebar />
      
      <div style={{ flex:1, position:'relative', overflow:'hidden' }}>
        <AtlasGraph />
        
        <AnimatePresence>
          {selectedNode && <NodeDetailPanel key="panel" />}
        </AnimatePresence>
      </div>
      
    </div>
    
    <Toaster
      position="bottom-right"
      toastOptions={{
        style: {
          background: '#09090B',
          color: '#FAFAFA',
          borderRadius: '8px',
          fontSize: '14px',
          border: '1px solid #27272A',
          fontFamily: 'Plus Jakarta Sans, sans-serif',
        },
      }}
    />
  </div>

After wiring: do a full end-to-end test:
  1. Open the app — confirm EmptyState shows
  2. Type "machine learning" — confirm LoadingSkeleton shows
  3. Map generates — confirm nodes appear correctly
  4. Click a node — confirm panel slides in from right
  5. Toggle depth — confirm text updates
  6. Click Expand — confirm new nodes animate in
  7. Reload page — confirm map reloads from Recent Maps
  8. Delete a map — confirm it removes from list

Show me the result of each test step.
Then give me the final interview prep section.

---

INTERVIEW PREP — give this after Step 12 is complete:

Format exactly like this:

INTERVIEW PREP — UI Rebuild

Q: What is Framer Motion and why did you use it instead of CSS animations?
A: [answer]

Q: What is Zustand and how is it different from useState?
A: [answer]

Q: What is React Flow and what problem does it solve?
A: [answer]

Q: What does AnimatePresence do and why is it needed for the side panel?
A: [answer]

Q: What is dagre and why do you need it for the graph layout?
A: [answer]

---

START NOW with STEP 1 — install the libraries.
Do not proceed past any step without my confirmation.
