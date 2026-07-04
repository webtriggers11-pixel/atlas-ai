/**
 * Compute (x, y) positions for a concept map using a radial tree layout.
 * Root is placed at (0, 0); children fan out in a full circle; each
 * expanded subtree gets its own arc sector, pointing away from the root.
 *
 * Returns a plain object: { [nodeId]: { x, y } }
 */
export function computeLayout(nodes, edges) {
  if (!nodes || nodes.length === 0) return {}

  // Build parent → children adjacency
  const children = {}
  for (const node of nodes) children[node.id] = []
  for (const edge of edges) {
    if (children[edge.source_node_id] !== undefined) {
      children[edge.source_node_id].push(edge.target_node_id)
    }
  }

  const root = nodes.find(n => n.is_root)
  if (!root) return {}

  const positions = {}
  const RADII = [0, 280, 200, 160]   // distance from parent per depth level

  function place(nodeId, cx, cy, arcStart, arcEnd, depth) {
    positions[nodeId] = { x: cx, y: cy }
    const kids = children[nodeId] || []
    if (kids.length === 0) return

    const radius = RADII[depth] ?? 140
    const arc    = arcEnd - arcStart
    const step   = arc / kids.length

    kids.forEach((kidId, i) => {
      const angle = arcStart + step * i + step / 2
      place(
        kidId,
        cx + Math.cos(angle) * radius,
        cy + Math.sin(angle) * radius,
        angle - step / 2,
        angle + step / 2,
        depth + 1,
      )
    })
  }

  place(root.id, 0, 0, -Math.PI, Math.PI, 0)
  return positions
}
