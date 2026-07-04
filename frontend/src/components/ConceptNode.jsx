import { Handle, Position } from '@xyflow/react'
import useAtlasStore from '../store/atlasStore'

/**
 * Custom React Flow node — renders a concept label with an expand button.
 * Root node gets a distinct visual style so the eye knows the "center of gravity."
 */
export default function ConceptNode({ id, data, selected }) {
  const expandNode    = useAtlasStore(s => s.expandNode)
  const expandingId   = useAtlasStore(s => s.expandingNodeId)
  const isExpanding   = expandingId === id

  const classes = [
    'atlas-node',
    data.isRoot   ? 'root'      : '',
    selected      ? 'selected'  : '',
    isExpanding   ? 'expanding' : '',
  ].filter(Boolean).join(' ')

  return (
    <>
      {/* Handles are required for edge routing but kept invisible */}
      <Handle type="target" position={Position.Top} style={{ opacity: 0, width: 1, height: 1, minWidth: 0, minHeight: 0, border: 'none' }} />

      <div className={classes}>
        <span style={{ flex: 1, wordBreak: 'break-word', lineHeight: 1.3 }}>
          {data.label}
        </span>

        {!data.isRoot && (
          <button
            className="expand-btn"
            title="Expand this concept"
            onClick={e => {
              e.stopPropagation()   // prevent node selection on button click
              if (!isExpanding) expandNode(id)
            }}
          >
            {isExpanding ? '…' : '+'}
          </button>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} style={{ opacity: 0, width: 1, height: 1, minWidth: 0, minHeight: 0, border: 'none' }} />
    </>
  )
}
