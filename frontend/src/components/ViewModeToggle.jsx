// Segmented control that switches between Tree view and Reading Mode
import { motion } from 'framer-motion'
import useAtlasStore from '../store/atlasStore'

function TreeIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <circle cx="12" cy="5" r="2" />
      <circle cx="5" cy="19" r="2" />
      <circle cx="19" cy="19" r="2" />
      <line x1="12" y1="7" x2="12" y2="13" />
      <line x1="12" y1="13" x2="5" y2="17" />
      <line x1="12" y1="13" x2="19" y2="17" />
    </svg>
  )
}

function ReadIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <line x1="4" y1="6"  x2="20" y2="6" />
      <line x1="4" y1="12" x2="20" y2="12" />
      <line x1="4" y1="18" x2="14" y2="18" />
    </svg>
  )
}

const MODES = [
  { key: 'tree', label: 'Tree', Icon: TreeIcon },
  { key: 'read', label: 'Read', Icon: ReadIcon },
]

export default function ViewModeToggle() {
  const viewMode   = useAtlasStore(s => s.viewMode)
  const setViewMode = useAtlasStore(s => s.setViewMode)
  const setSelectedNode = useAtlasStore(s => s.setSelectedNode)

  function handleSwitch(mode) {
    if (mode === viewMode) return
    if (mode === 'read') setSelectedNode(null)
    setViewMode(mode)
  }

  return (
    <div style={{
      position: 'absolute', top: 16, right: 16, zIndex: 10,
      display: 'flex',
      background: '#FFFFFF',
      border: '1px solid var(--border)',
      borderRadius: 8,
      padding: 3,
      boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
    }}>
      {MODES.map(({ key, label, Icon }) => {
        const active = viewMode === key
        return (
          <button
            key={key}
            onClick={() => handleSwitch(key)}
            style={{
              position: 'relative', zIndex: 1,
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '6px 14px',
              fontSize: 13, fontWeight: 500,
              fontFamily: 'inherit',
              color: active ? '#FFFFFF' : 'var(--text-muted)',
              background: 'transparent',
              border: 'none',
              borderRadius: 6,
              cursor: 'pointer',
              transition: 'color 0.15s',
            }}
            onMouseEnter={e => { if (!active) e.currentTarget.style.color = 'var(--text)' }}
            onMouseLeave={e => { if (!active) e.currentTarget.style.color = 'var(--text-muted)' }}
          >
            {active && (
              <motion.div
                layoutId="view-mode-indicator"
                style={{
                  position: 'absolute', inset: 0,
                  background: 'var(--accent)',
                  borderRadius: 6, zIndex: -1,
                }}
                transition={{ duration: 0.18, ease: 'easeOut' }}
              />
            )}
            <Icon />
            {label}
          </button>
        )
      })}
    </div>
  )
}
