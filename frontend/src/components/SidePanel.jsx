import { useEffect } from 'react'
import useAtlasStore from '../store/atlasStore'

const DEPTHS = ['gist', 'standard', 'expert']

/**
 * Side panel that slides in from the right when a node is selected.
 * Shows the node's explanation at the active depth plus a 3-way depth toggle.
 */
export default function SidePanel() {
  const currentMap    = useAtlasStore(s => s.currentMap)
  const selectedNodeId = useAtlasStore(s => s.selectedNodeId)
  const activeDepth   = useAtlasStore(s => s.activeDepth)
  const depthLoading  = useAtlasStore(s => s.depthLoading)
  const expandingId   = useAtlasStore(s => s.expandingNodeId)
  const closePanel    = useAtlasStore(s => s.closePanel)
  const changeDepth   = useAtlasStore(s => s.changeDepth)
  const expandNode    = useAtlasStore(s => s.expandNode)

  const node = currentMap?.nodes.find(n => n.id === selectedNodeId)
  const explanation = node?.explanations.find(e => e.depth === activeDepth)

  // Close on Escape
  useEffect(() => {
    const onKey = e => { if (e.key === 'Escape') closePanel() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [closePanel])

  if (!node) return null

  const isExpanding = expandingId === selectedNodeId

  return (
    <div
      className="absolute right-0 top-0 h-full w-80 flex flex-col z-10"
      style={{ background: '#1f2937', borderLeft: '1px solid #374151' }}
    >
      {/* Header */}
      <div className="flex items-start justify-between p-4 border-b border-gray-700">
        <h2 className="text-base font-semibold text-white leading-snug pr-2" style={{ wordBreak: 'break-word' }}>
          {node.label}
        </h2>
        <button
          onClick={closePanel}
          className="text-gray-400 hover:text-white flex-shrink-0 text-lg leading-none"
          title="Close (Esc)"
        >
          ✕
        </button>
      </div>

      {/* Depth toggle */}
      <div className="flex gap-1 p-3 border-b border-gray-700">
        {DEPTHS.map(d => (
          <button
            key={d}
            onClick={() => changeDepth(d)}
            className="flex-1 py-1.5 rounded text-xs font-medium transition-colors"
            style={{
              background: activeDepth === d ? '#6366f1' : '#374151',
              color:      activeDepth === d ? '#fff'    : '#9ca3af',
            }}
          >
            {d}
          </button>
        ))}
      </div>

      {/* Explanation body */}
      <div className="flex-1 overflow-y-auto p-4">
        {depthLoading ? (
          <div className="flex items-center gap-2 text-gray-400 text-sm">
            <span className="inline-block w-3 h-3 rounded-full border-2 border-indigo-400 border-t-transparent animate-spin" />
            Generating explanation…
          </div>
        ) : explanation ? (
          <p className="text-gray-200 text-sm leading-relaxed">{explanation.content}</p>
        ) : (
          <p className="text-gray-500 text-sm italic">
            No {activeDepth} explanation yet — click the depth button above to generate one.
          </p>
        )}
      </div>

      {/* Expand button */}
      {!node.is_root && (
        <div className="p-4 border-t border-gray-700">
          <button
            onClick={() => { expandNode(selectedNodeId); closePanel() }}
            disabled={isExpanding}
            className="w-full py-2 rounded text-sm font-medium transition-colors"
            style={{
              background: isExpanding ? '#374151' : '#6366f1',
              color: isExpanding ? '#9ca3af' : '#fff',
            }}
          >
            {isExpanding ? 'Expanding…' : 'Expand this concept →'}
          </button>
        </div>
      )}
    </div>
  )
}
