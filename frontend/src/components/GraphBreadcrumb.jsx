// Breadcrumb trail shown at the top of the canvas when a node is selected
import { motion } from 'framer-motion'
import useAtlasStore from '../store/atlasStore'

export default function GraphBreadcrumb() {
  const selectedNode    = useAtlasStore(s => s.selectedNode)
  const storeNodes      = useAtlasStore(s => s.nodes)
  const setSelectedNode = useAtlasStore(s => s.setSelectedNode)

  if (!selectedNode) return null

  // Walk parent_id chain from selectedNode up to root, then reverse
  function buildPath() {
    const path = []
    let cur = storeNodes.find(n => n.id === selectedNode.id)
    while (cur) {
      path.unshift(cur)
      if (!cur.parent_id) break
      cur = storeNodes.find(n => n.id === cur.parent_id)
    }
    return path
  }

  const path = buildPath()

  return (
    <motion.div
      initial={{ y: -36, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      exit={{ y: -36, opacity: 0 }}
      transition={{ duration: 0.15 }}
      style={{
        position: 'absolute', top: 0, left: 0, right: 0, zIndex: 5,
        height: 36,
        background: 'rgba(255,255,255,0.9)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
        borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center',
        padding: '0 16px', gap: 4,
      }}
    >
      {path.map((node, i) => {
        const isLast = i === path.length - 1
        return (
          <span key={node.id} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            {i > 0 && (
              <span style={{ color: '#E4E4E7', fontSize: 14, userSelect: 'none' }}>›</span>
            )}
            <button
              onClick={() => setSelectedNode(isLast ? null : node)}
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                fontSize: 14, fontFamily: 'inherit', padding: 0,
                fontWeight: isLast ? 600 : 400,
                color: isLast ? 'var(--text)' : 'var(--text-muted)',
              }}
            >
              {node.label}
            </button>
          </span>
        )
      })}
    </motion.div>
  )
}
