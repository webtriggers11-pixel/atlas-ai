// Centered empty state shown on the canvas when no map is loaded
import { motion } from 'framer-motion'
import useAtlasStore from '../store/atlasStore'

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
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      userSelect: 'none',
    }}>

      {/* Icon circle */}
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.4, ease: 'easeOut' }}
        style={{
          width: 120,
          height: 120,
          borderRadius: '50%',
          border: '2px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--surface)',
        }}
      >
        <NetworkIcon />
      </motion.div>

      {/* Heading */}
      <motion.h2
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.3 }}
        style={{ fontSize: 20, fontWeight: 700, color: 'var(--text)', marginTop: 24 }}
      >
        Explore any idea
      </motion.h2>

      {/* Subtext */}
      <motion.p
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15, duration: 0.3 }}
        style={{
          fontSize: 14,
          color: 'var(--text-muted)',
          textAlign: 'center',
          maxWidth: 260,
          marginTop: 8,
          lineHeight: 1.6,
        }}
      >
        Type a topic above and press Generate<br />Click any concept to go deeper
      </motion.p>

      {/* Example chips */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2, duration: 0.3 }}
        style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center', marginTop: 24 }}
      >
        {CHIPS.map((chip, i) => (
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
      </motion.div>

    </div>
  )
}
