// Dagre layout — computes (x, y) positions for a collapsible top-down tree
import dagre from 'dagre'

/**
 * Returns only the nodes and edges that should be visible right now,
 * then runs dagre to assign x/y positions to them.
 *
 * expandedNodeIds — a Set of node IDs whose children should be shown.
 * Nodes NOT in this set keep their children hidden (collapsed).
 */
export function getLayoutedElements(nodes, edges, expandedNodeIds = new Set()) {
  // ── Step 1: decide which nodes are visible ─────────────────────────────

  const visibleNodeIds = new Set()

  const rootNode = nodes.find(n => n.is_root)
  if (!rootNode) return { nodes: [], edges: [] }

  // Root is always visible
  visibleNodeIds.add(rootNode.id)

  // First-level children (direct children of root) are always visible
  nodes
    .filter(n => n.parent_id === rootNode.id)
    .forEach(n => visibleNodeIds.add(n.id))

  // Deeper nodes are only visible if their parent has been expanded
  nodes.forEach(node => {
    if (node.parent_id && expandedNodeIds.has(node.parent_id)) {
      visibleNodeIds.add(node.id)
    }
  })

  const visibleNodes = nodes.filter(n => visibleNodeIds.has(n.id))
  const visibleEdges = edges.filter(
    e => visibleNodeIds.has(e.source_node_id) && visibleNodeIds.has(e.target_node_id)
  )

  // ── Step 2: run dagre on the visible subset ────────────────────────────

  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({
    rankdir: 'TB',    // TB = top to bottom (root at top, children below)
    nodesep: 60,      // horizontal gap between sibling nodes
    ranksep: 80,      // vertical gap between levels
    marginx: 40,
    marginy: 40,
  })

  visibleNodes.forEach(node => {
    g.setNode(node.id, {
      width:  node.is_root ? 220 : 180,
      height: node.is_root ? 64  : 72,
    })
  })

  visibleEdges.forEach(edge => {
    g.setEdge(edge.source_node_id, edge.target_node_id)
  })

  dagre.layout(g)

  // ── Step 3: map dagre's center-point positions back to React Flow ──────
  // Dagre gives us the center (x, y) of each node.
  // React Flow wants the top-left corner, so we subtract half the size.

  const layoutedNodes = visibleNodes.map(node => {
    const { x, y } = g.node(node.id)
    const width  = node.is_root ? 220 : 180
    const height = node.is_root ? 64  : 72
    return {
      ...node,
      position: { x: x - width / 2, y: y - height / 2 },
    }
  })

  return { nodes: layoutedNodes, edges: visibleEdges }
}
