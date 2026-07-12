// Reading Mode — renders the current map as a structured article
import { useEffect } from 'react'
import { motion } from 'framer-motion'
import useAtlasStore from '../store/atlasStore'
import { TextReveal } from '@/components/ui/text-reveal'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function slugify(label) {
  return label.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '')
}

function SkeletonLine({ width = '100%' }) {
  return (
    <motion.div
      animate={{ opacity: [0.4, 0.8, 0.4] }}
      transition={{ duration: 1.2, repeat: Infinity }}
      style={{ height: 16, width, borderRadius: 4, background: '#F4F4F5', marginBottom: 8 }}
    />
  )
}

function ConceptSection({ node, grandchildren, onViewInTree }) {
  const explanation = node.explanations?.find(e => e.depth === 'standard')

  return (
    <motion.section
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true }}
      transition={{ duration: 0.4 }}
      id={slugify(node.label)}
      className="reading-section"
    >
      <div style={{
        display: 'flex', alignItems: 'baseline', gap: 8,
        marginTop: 48, paddingBottom: 12, borderBottom: '1px solid var(--border)',
      }}>
        <TextReveal
          as="h2"
          text={node.label}
          style={{ fontSize: 22, fontWeight: 700, color: 'var(--text)', flex: 1 }}
        />
        <button
          onClick={() => onViewInTree(node)}
          className="view-in-tree-btn"
          title="View in tree"
          style={{
            background: 'none', border: 'none', cursor: 'pointer',
            color: 'var(--accent-text)', fontSize: 12, fontFamily: 'inherit',
            display: 'flex', alignItems: 'center', gap: 4, opacity: 0,
            transition: 'opacity 0.12s', flexShrink: 0, paddingBottom: 4,
          }}
        >
          View in tree
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M15 3h6v6" /><path d="M10 14 21 3" />
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
          </svg>
        </button>
      </div>

      <div style={{ marginTop: 16 }}>
        {explanation ? (
          <p style={{ fontSize: 15, color: 'var(--text)', lineHeight: 1.8 }}>
            {explanation.content}
          </p>
        ) : (
          <>
            <SkeletonLine width="100%" />
            <SkeletonLine width="88%" />
            <SkeletonLine width="65%" />
          </>
        )}
      </div>

      {grandchildren.map(gc => {
        const gcExp = gc.explanations?.find(e => e.depth === 'standard')
        return (
          <div key={gc.id} style={{ marginTop: 28, paddingLeft: 16,
            borderLeft: '3px solid var(--accent-light)' }}>
            <h3 style={{ fontSize: 17, fontWeight: 600, color: 'var(--text)' }}>
              {gc.label}
            </h3>
            <div style={{ marginTop: 10 }}>
              {gcExp ? (
                <p style={{ fontSize: 14, color: 'var(--text)', lineHeight: 1.75 }}>
                  {gcExp.content}
                </p>
              ) : (
                <>
                  <SkeletonLine width="100%" />
                  <SkeletonLine width="70%" />
                </>
              )}
            </div>
          </div>
        )
      })}
    </motion.section>
  )
}

export default function ReadingMode() {
  const storeNodes  = useAtlasStore(s => s.nodes)
  const currentMap  = useAtlasStore(s => s.currentMap)
  const setViewMode = useAtlasStore(s => s.setViewMode)
  const setNodes    = useAtlasStore(s => s.setNodes)
  const setSelectedNode = useAtlasStore(s => s.setSelectedNode)
  const focusNode        = useAtlasStore(s => s.focusNode)

  function viewInTree(node) {
    setSelectedNode(node)
    setViewMode('tree')
    requestAnimationFrame(() => focusNode(node.id))
  }

  const rootNode    = storeNodes.find(n => n.is_root)
  const firstLevel  = storeNodes.filter(n => n.parent_id === rootNode?.id)

  // Auto-fetch standard explanation for any node that's missing one
  useEffect(() => {
    if (!currentMap) return
    const missing = storeNodes.filter(
      n => !n.is_root && !n.explanations?.some(e => e.depth === 'standard')
    )
    missing.forEach(async node => {
      try {
        const res = await fetch(
          `${API}/maps/${currentMap.id}/nodes/${node.id}/depth`,
          { method: 'PATCH', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ depth: 'standard' }) }
        )
        if (!res.ok) return
        const newExp = await res.json()
        setNodes(
          useAtlasStore.getState().nodes.map(n =>
            n.id === node.id
              ? { ...n, explanations: [...(n.explanations ?? []), newExp] }
              : n
          )
        )
      } catch { /* silent — skeleton stays visible */ }
    })
  }, [currentMap?.id])

  if (!rootNode) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 16 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      style={{
        flex: 1, height: '100%', overflowY: 'auto',
        background: 'var(--bg)',
      }}
    >
      <div style={{ maxWidth: 720, margin: '0 auto', padding: '48px 24px' }}>

        {/* Title */}
        <TextReveal
          as="h1"
          text={rootNode.label}
          style={{ fontSize: 32, fontWeight: 700, color: 'var(--text)', lineHeight: 1.2 }}
        />
        <p style={{ fontSize: 14, color: 'var(--text-muted)', marginTop: 8 }}>
          An AI-generated concept map · {storeNodes.length} concepts
        </p>

        {/* Table of contents */}
        {firstLevel.length > 4 && (
          <div style={{
            marginTop: 32, padding: '20px 24px',
            background: 'var(--surface)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius-panel)',
          }}>
            <p style={{
              fontSize: 11, fontWeight: 600, letterSpacing: '0.08em',
              textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 12,
            }}>
              In this map
            </p>
            <ol style={{ listStyle: 'decimal', paddingLeft: 20, display: 'flex', flexDirection: 'column', gap: 6 }}>
              {firstLevel.map(n => (
                <li key={n.id}>
                  <a
                    href={`#${slugify(n.label)}`}
                    style={{ fontSize: 14, color: 'var(--accent-text)', textDecoration: 'none' }}
                    onMouseEnter={e => e.currentTarget.style.textDecoration = 'underline'}
                    onMouseLeave={e => e.currentTarget.style.textDecoration = 'none'}
                  >
                    {n.label}
                  </a>
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* Concept sections */}
        {firstLevel.map(node => {
          const grandchildren = storeNodes.filter(n => n.parent_id === node.id)
          return (
            <ConceptSection key={node.id} node={node} grandchildren={grandchildren} onViewInTree={viewInTree} />
          )
        })}

        {/* Footer */}
        <div style={{
          borderTop: '1px solid var(--border)', marginTop: 64, paddingTop: 24,
          textAlign: 'center',
        }}>
          <p style={{ fontSize: 12, color: '#A1A1AA' }}>
            Generated by Idea Atlas · Powered by local AI
          </p>
          <button
            onClick={() => setViewMode('tree')}
            style={{
              marginTop: 12, background: 'none', border: 'none',
              color: 'var(--accent-text)', fontSize: 14,
              cursor: 'pointer', fontFamily: 'inherit', textDecoration: 'underline',
            }}
          >
            ← Back to tree view
          </button>
        </div>
      </div>

      <style>{`.reading-section:hover .view-in-tree-btn { opacity: 1 !important; }`}</style>
    </motion.div>
  )
}
