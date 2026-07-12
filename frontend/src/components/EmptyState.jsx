// Centered empty state shown on the canvas when no map is loaded — dual entry point
import { motion } from 'framer-motion'
import useAtlasStore from '../store/atlasStore'
import DocumentUpload from './DocumentUpload'

const CHIPS = [
  { label: 'Quantum computing', icon: '⚛' },
  { label: 'Climate change',    icon: '🌍' },
  { label: 'Machine learning',  icon: '🤖' },
]

function NetworkIcon() {
  return (
    <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
      {/* Center node */}
      <circle cx="20" cy="20" r="4" fill="var(--accent)" />
      {/* Outer nodes */}
      <circle cx="20" cy="6"  r="3" fill="var(--accent)" opacity="0.7" />
      <circle cx="34" cy="28" r="3" fill="var(--accent)" opacity="0.7" />
      <circle cx="6"  cy="28" r="3" fill="var(--accent)" opacity="0.7" />
      {/* Connecting lines */}
      <line x1="20" y1="16" x2="20" y2="9"  stroke="var(--accent)" strokeWidth="1.5" opacity="0.5" />
      <line x1="20" y1="23" x2="31" y2="26" stroke="var(--accent)" strokeWidth="1.5" opacity="0.5" />
      <line x1="20" y1="23" x2="9"  y2="26" stroke="var(--accent)" strokeWidth="1.5" opacity="0.5" />
    </svg>
  )
}

export default function EmptyState() {
  const isGenerating  = useAtlasStore(s => s.isGenerating)
  const setCurrentMap = useAtlasStore(s => s.setCurrentMap)
  const setNodes      = useAtlasStore(s => s.setNodes)
  const setEdges      = useAtlasStore(s => s.setEdges)
  const setIsGenerating = useAtlasStore(s => s.setIsGenerating)
  const setRecentMaps   = useAtlasStore(s => s.setRecentMaps)
  const recentMaps      = useAtlasStore(s => s.recentMaps)
  const depth           = useAtlasStore(s => s.depth)
  const setSelectedNode = useAtlasStore(s => s.setSelectedNode)

  const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  async function generate(topic) {
    if (isGenerating) return
    setIsGenerating(true)
    setSelectedNode(null)
    try {
      const res = await fetch(`${API}/maps`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic, depth }),
      })
      if (!res.ok) throw new Error()
      const map = await res.json()
      setCurrentMap(map)
      setNodes(map.nodes)
      setEdges(map.edges)
      setRecentMaps([
        { id: map.id, topic: map.topic, title: map.title, created_at: map.created_at },
        ...recentMaps.filter(m => m.id !== map.id),
      ])
    } catch {
      // toast handled in TopBar; here we just reset
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <div style={{
      flex: 1,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      userSelect: 'none',
      padding: 24,
    }}>
      <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', justifyContent: 'center', alignItems: 'stretch' }}>

        {/* Card 1 — Explore a topic */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
          style={{
            flex: 1, minWidth: 260, maxWidth: 320,
            border: '1.5px solid var(--border)',
            borderRadius: 'var(--radius-panel)',
            background: 'var(--surface)',
            padding: 24,
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            textAlign: 'center', gap: 10,
          }}
        >
          {/* Icon circle */}
          <div style={{
            width: 48, height: 48, borderRadius: '50%',
            border: '2px solid var(--border)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'var(--bg)', flexShrink: 0,
          }}>
            <NetworkIcon />
          </div>

          <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--text)' }}>Explore a topic</h3>
          <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.5 }}>
            Type a topic above and press Generate. Click any concept to go deeper.
          </p>

          {/* Example chips */}
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center', marginTop: 4 }}>
            {CHIPS.map(chip => (
              <motion.button
                key={chip.label}
                whileHover={{ scale: 1.03, borderColor: 'var(--accent)', color: 'var(--accent-text)', background: 'var(--accent-light)' }}
                whileTap={{ scale: 0.97 }}
                onClick={() => generate(chip.label)}
                disabled={isGenerating}
                style={{
                  border: '1px solid var(--border)',
                  borderRadius: 99,
                  padding: '6px 14px',
                  fontSize: 13,
                  color: 'var(--text-muted)',
                  background: 'var(--surface)',
                  cursor: isGenerating ? 'not-allowed' : 'pointer',
                  fontFamily: 'inherit',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  transition: 'border-color 0.15s, color 0.15s, background 0.15s',
                }}
              >
                <span>{chip.icon}</span>
                {chip.label}
              </motion.button>
            ))}
          </div>
        </motion.div>

        {/* Card 2 — Understand a document */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.05 }}
        >
          <DocumentUpload />
        </motion.div>

      </div>
    </div>
  )
}
