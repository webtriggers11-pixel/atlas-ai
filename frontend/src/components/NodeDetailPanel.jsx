// Right-side panel that slides in when a node is clicked
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import useAtlasStore from '../store/atlasStore'

const API    = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const DEPTHS = ['gist', 'standard', 'expert']

// ── Small reusable pieces ──────────────────────────────────────────────────

function CloseButton({ onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        position: 'absolute', top: 20, right: 20,
        background: 'none', border: 'none', cursor: 'pointer',
        color: 'var(--text-muted)', padding: 4, borderRadius: 6,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        transition: 'background 0.12s',
      }}
      onMouseEnter={e => e.currentTarget.style.background = '#F4F4F5'}
      onMouseLeave={e => e.currentTarget.style.background = 'none'}
      title="Close (Esc)"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" strokeWidth="2" strokeLinecap="round">
        <line x1="18" y1="6" x2="6" y2="18" />
        <line x1="6" y1="6" x2="18" y2="18" />
      </svg>
    </button>
  )
}

function SkeletonLines() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 16 }}>
      {['100%', '85%', '60%'].map((w, i) => (
        <motion.div
          key={i}
          animate={{ opacity: [0.4, 0.8, 0.4] }}
          transition={{ duration: 1.2, repeat: Infinity, delay: i * 0.1 }}
          style={{ height: 16, width: w, borderRadius: 4, background: '#F4F4F5' }}
        />
      ))}
    </div>
  )
}

// ── Main component ─────────────────────────────────────────────────────────

export default function NodeDetailPanel() {
  const storeNodes    = useAtlasStore(s => s.nodes)
  const storeEdges    = useAtlasStore(s => s.edges)
  const selectedNode  = useAtlasStore(s => s.selectedNode)
  const currentMap    = useAtlasStore(s => s.currentMap)
  const depth         = useAtlasStore(s => s.depth)
  const setDepth      = useAtlasStore(s => s.setDepth)
  const setSelectedNode = useAtlasStore(s => s.setSelectedNode)
  const setNodes      = useAtlasStore(s => s.setNodes)
  const setEdges      = useAtlasStore(s => s.setEdges)
  const isExpanding   = useAtlasStore(s => s.isExpanding)
  const setIsExpanding = useAtlasStore(s => s.setIsExpanding)

  const [depthLoading, setDepthLoading] = useState(false)
  const [expandDone, setExpandDone]     = useState(false)

  if (!selectedNode || !currentMap) return null

  // Always read the freshest version of this node from the store
  const node = storeNodes.find(n => n.id === selectedNode.id) ?? selectedNode

  // Current explanation for the active depth
  const explanation = node.explanations?.find(e => e.depth === depth)

  // Breadcrumb: walk parent_id chain from node up to root
  function buildBreadcrumb() {
    const crumbs = []
    let current = node
    while (current) {
      crumbs.unshift(current)
      if (!current.parent_id) break
      current = storeNodes.find(n => n.id === current.parent_id)
    }
    return crumbs
  }

  // Siblings: nodes that share the same parent (excluding self), max 5
  const siblings = storeNodes
    .filter(n => n.parent_id === node.parent_id && n.id !== node.id)
    .slice(0, 5)

  // ── Depth toggle ────────────────────────────────────────────────────────

  async function handleDepthChange(newDepth) {
    if (newDepth === depth) return
    setDepth(newDepth)

    // Client-side cache hit
    if (node.explanations?.some(e => e.depth === newDepth)) return

    setDepthLoading(true)
    try {
      const res = await fetch(
        `${API}/maps/${currentMap.id}/nodes/${node.id}/depth`,
        { method: 'PATCH', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ depth: newDepth }) }
      )
      if (!res.ok) throw new Error()
      const newExp = await res.json()
      // Merge new explanation into this node's explanations array in the store
      setNodes(storeNodes.map(n =>
        n.id === node.id
          ? { ...n, explanations: [...(n.explanations ?? []), newExp] }
          : n
      ))
    } catch {
      toast.error('Could not load explanation')
    } finally {
      setDepthLoading(false)
    }
  }

  // ── Expand ──────────────────────────────────────────────────────────────

  async function handleExpand() {
    if (isExpanding) return
    setIsExpanding(true)
    try {
      const res = await fetch(
        `${API}/maps/${currentMap.id}/nodes/${node.id}/expand`,
        { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ depth }) }
      )
      if (!res.ok) throw new Error()
      const { new_nodes, new_edges } = await res.json()
      setNodes([...storeNodes, ...new_nodes])
      setEdges([...storeEdges, ...new_edges])
      setExpandDone(true)
      setTimeout(() => setExpandDone(false), 2500)
    } catch {
      toast.error('Could not expand — try again')
    } finally {
      setIsExpanding(false)
    }
  }

  const breadcrumb = buildBreadcrumb()

  return (
    <motion.div
      initial={{ x: 360 }}
      animate={{ x: 0 }}
      exit={{ x: 360 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      style={{
        position: 'absolute', right: 0, top: 0, bottom: 0,
        width: 360,
        background: 'var(--surface)',
        borderLeft: '1px solid var(--border)',
        padding: 24,
        zIndex: 10,
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: 0,
      }}
    >
      <CloseButton onClick={() => setSelectedNode(null)} />

      {/* Breadcrumb */}
      <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 4, paddingRight: 32 }}>
        {breadcrumb.map((crumb, i) => (
          <span key={crumb.id} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            {i > 0 && <span style={{ color: 'var(--border-hover)', fontSize: 12 }}>›</span>}
            <button
              onClick={() => setSelectedNode(crumb)}
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                fontSize: 12, color: 'var(--text-muted)',
                fontFamily: 'inherit', padding: 0,
              }}
            >
              {crumb.label}
            </button>
          </span>
        ))}
      </div>

      {/* Node label */}
      <h2 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text)', marginTop: 12, lineHeight: 1.3 }}>
        {node.label}
      </h2>

      {/* Depth toggle */}
      <div style={{ marginTop: 20 }}>
        <p style={{
          fontSize: 10, fontWeight: 600, letterSpacing: '0.08em',
          textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8,
        }}>
          Explanation
        </p>
        <div style={{
          display: 'flex', background: '#F4F4F5',
          borderRadius: 'var(--radius-btn)', padding: 3,
        }}>
          {DEPTHS.map(d => (
            <button
              key={d}
              onClick={() => handleDepthChange(d)}
              style={{
                flex: 1, height: 32, border: 'none', cursor: 'pointer',
                fontSize: 13, fontFamily: 'inherit',
                fontWeight: depth === d ? 600 : 400,
                color: depth === d ? 'var(--accent-text)' : 'var(--text-muted)',
                background: 'transparent',
                borderRadius: 6, position: 'relative', zIndex: 1,
                transition: 'color 0.15s',
                textTransform: 'capitalize',
              }}
            >
              {depth === d && (
                <motion.div
                  layoutId="active-depth"
                  style={{
                    position: 'absolute', inset: 0,
                    background: 'var(--surface)',
                    borderRadius: 6,
                    boxShadow: '0 1px 2px rgba(0,0,0,0.08)',
                    zIndex: -1,
                  }}
                  transition={{ duration: 0.18, ease: 'easeOut' }}
                />
              )}
              {d}
            </button>
          ))}
        </div>
      </div>

      {/* Explanation text */}
      <div style={{ marginTop: 16, flex: 1 }}>
        {depthLoading ? (
          <SkeletonLines />
        ) : (
          <AnimatePresence mode="wait">
            <motion.p
              key={`${node.id}-${depth}`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              style={{ fontSize: 15, color: 'var(--text)', lineHeight: 1.7 }}
            >
              {explanation?.content ?? (
                <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
                  No {depth} explanation yet — click the depth button above to generate one.
                </span>
              )}
            </motion.p>
          </AnimatePresence>
        )}
      </div>

      {/* Related concepts (siblings) */}
      {siblings.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <p style={{
            fontSize: 10, fontWeight: 600, letterSpacing: '0.08em',
            textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 8,
          }}>
            In this map
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {siblings.map(s => (
              <button
                key={s.id}
                onClick={() => setSelectedNode(s)}
                style={{
                  background: '#F4F4F5', border: '1px solid transparent',
                  borderRadius: 99, padding: '4px 12px',
                  fontSize: 12, color: 'var(--text-muted)',
                  cursor: 'pointer', fontFamily: 'inherit',
                  transition: 'border-color 0.12s, color 0.12s',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.borderColor = 'var(--accent)'
                  e.currentTarget.style.color = 'var(--accent-text)'
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.borderColor = 'transparent'
                  e.currentTarget.style.color = 'var(--text-muted)'
                }}
              >
                {s.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Expand button — hidden for root node */}
      {!node.is_root && (
        <div style={{ marginTop: 'auto', paddingTop: 24, borderTop: '1px solid var(--border)' }}>
          <motion.button
            whileTap={{ scale: 0.98 }}
            onClick={handleExpand}
            disabled={isExpanding}
            style={{
              width: '100%', height: 40,
              border: `1.5px solid ${expandDone ? '#16A34A' : 'var(--accent)'}`,
              background: expandDone ? '#F0FDF4' : 'transparent',
              color: expandDone ? '#16A34A' : 'var(--accent)',
              borderRadius: 'var(--radius-btn)',
              fontSize: 14, fontWeight: 500, fontFamily: 'inherit',
              cursor: isExpanding ? 'not-allowed' : 'pointer',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
              transition: 'background 0.15s, border-color 0.15s, color 0.15s',
            }}
            onMouseEnter={e => { if (!isExpanding && !expandDone) e.currentTarget.style.background = 'var(--accent-light)' }}
            onMouseLeave={e => { if (!isExpanding && !expandDone) e.currentTarget.style.background = 'transparent' }}
          >
            {isExpanding ? (
              <>
                <span style={{
                  width: 14, height: 14, border: '2px solid var(--accent-light)',
                  borderTopColor: 'var(--accent)', borderRadius: '50%',
                  animation: 'spin 0.7s linear infinite', display: 'inline-block',
                }} />
                Generating…
              </>
            ) : expandDone ? (
              '✓ Concepts added'
            ) : (
              <>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                  <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="16" />
                  <line x1="8" y1="12" x2="16" y2="12" />
                </svg>
                Expand into sub-concepts
              </>
            )}
          </motion.button>
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </motion.div>
  )
}
