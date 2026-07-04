// Custom React Flow node — root card and collapsible child cards
import { memo } from 'react'
import { motion } from 'framer-motion'
import { Handle, Position } from '@xyflow/react'

// Handles are required for React Flow to know where to draw edges.
// They are hidden visually — display:none in index.css and inline style here.
const hiddenHandle = { display: 'none' }

function RootNode({ data }) {
  return (
    <div style={{
      width: 220, minHeight: 64,
      background: '#09090B',
      borderRadius: 'var(--radius-node)',
      padding: '16px 20px',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      position: 'relative', cursor: 'pointer',
    }}>
      <span style={{ fontSize: 15, fontWeight: 600, color: '#FAFAFA', lineHeight: 1.4 }}>
        {data.label}
      </span>
      <div style={{
        width: 6, height: 6, borderRadius: '50%',
        background: 'var(--accent)',
        position: 'absolute', bottom: 10, right: 12,
      }} />
    </div>
  )
}

function ExpandToggleButton({ isExpanded, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        width: 20, height: 20, borderRadius: '50%',
        border: '1px solid #E4E4E7',
        background: 'none', color: '#71717A',
        fontSize: 14, lineHeight: 1,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        cursor: 'pointer', padding: 0, fontFamily: 'inherit',
        transition: 'border-color 0.12s, color 0.12s, background 0.12s',
        flexShrink: 0,
      }}
      onMouseEnter={e => {
        e.currentTarget.style.borderColor = '#7C3AED'
        e.currentTarget.style.color = '#7C3AED'
        e.currentTarget.style.background = '#EDE9FE'
      }}
      onMouseLeave={e => {
        e.currentTarget.style.borderColor = '#E4E4E7'
        e.currentTarget.style.color = '#71717A'
        e.currentTarget.style.background = 'none'
      }}
    >
      {isExpanded ? '−' : '+'}
    </button>
  )
}

function ChildNode({ data }) {
  const { isSelected, isExpanded, hasChildren, childCount, depth = 1 } = data

  // Depth-based typography
  const labelSize  = depth >= 3 ? 12 : depth === 2 ? 13 : 14
  const summarySize = depth === 2 ? 11 : 12
  const showSummary = depth < 3

  // Depth-based colour
  const nodeBg     = depth >= 3 ? '#FAFAFA' : isSelected ? 'var(--accent-light)' : 'var(--surface)'
  const borderColor = isSelected
    ? 'var(--accent)'
    : isExpanded
      ? '#A78BFA'
      : depth === 2 ? '#F4F4F5' : 'var(--border)'

  function handleToggle(e) {
    e.stopPropagation() // don't fire node-select on the canvas
    if (isExpanded) {
      data.onCollapseClick?.(data.nodeId)
    } else {
      data.onExpandClick?.(data.nodeId)
    }
  }

  return (
    <div style={{
      width: 180,
      background: nodeBg,
      border: `1px solid ${borderColor}`,
      borderRadius: 'var(--radius-node)',
      padding: '12px 14px',
      boxShadow: 'var(--shadow-card)',
      cursor: 'pointer',
      transition: 'border-color 0.15s, background 0.15s',
    }}>
      <p style={{
        fontSize: labelSize, fontWeight: 600, lineHeight: 1.4,
        color: isSelected ? 'var(--accent-text)' : 'var(--text)',
      }}>
        {data.label}
      </p>

      {showSummary && data.summary && (
        <p style={{
          fontSize: summarySize, color: 'var(--text-muted)',
          marginTop: 4, lineHeight: 1.5,
          display: '-webkit-box',
          WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
        }}>
          {data.summary}
        </p>
      )}

      <div style={{
        display: 'flex', justifyContent: 'space-between',
        alignItems: 'center', marginTop: 10,
      }}>
        <span style={{ fontSize: 11, color: 'var(--accent)', fontWeight: 500 }}>
          {isExpanded && hasChildren ? `${childCount} concepts` : ''}
        </span>
        <ExpandToggleButton isExpanded={isExpanded} onClick={handleToggle} />
      </div>
    </div>
  )
}

function CustomNode({ data }) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.85 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.18, ease: 'easeOut' }}
    >
      {/* Edges connect to these handles. Hidden visually but required by React Flow. */}
      <Handle type="target" position={Position.Top}    style={hiddenHandle} isConnectable={false} />
      {data.isRoot ? <RootNode data={data} /> : <ChildNode data={data} />}
      <Handle type="source" position={Position.Bottom} style={hiddenHandle} isConnectable={false} />
    </motion.div>
  )
}

export default memo(CustomNode)
