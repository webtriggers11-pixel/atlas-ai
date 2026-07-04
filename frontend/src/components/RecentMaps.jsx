import { useState } from 'react'
import useAtlasStore from '../store/atlasStore'

/**
 * Collapsible left sidebar showing recently generated maps.
 * Click a map to reload it; trash icon deletes it.
 */
export default function RecentMaps() {
  const recentMaps   = useAtlasStore(s => s.recentMaps)
  const currentMap   = useAtlasStore(s => s.currentMap)
  const loadMap      = useAtlasStore(s => s.loadMap)
  const deleteMap    = useAtlasStore(s => s.deleteMap)
  const [open, setOpen] = useState(true)

  return (
    <div
      className="flex flex-col h-full z-10 flex-shrink-0"
      style={{
        width: open ? '220px' : '40px',
        background: '#1f2937',
        borderRight: '1px solid #374151',
        transition: 'width 0.2s ease',
        overflow: 'hidden',
      }}
    >
      {/* Toggle button */}
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-2 p-3 text-gray-400 hover:text-white text-sm flex-shrink-0 border-b border-gray-700 w-full"
        title={open ? 'Collapse' : 'Recent maps'}
      >
        <span>{open ? '◀' : '▶'}</span>
        {open && <span className="font-medium text-xs uppercase tracking-wider text-gray-500">Recent maps</span>}
      </button>

      {open && (
        <div className="flex-1 overflow-y-auto">
          {recentMaps.length === 0 ? (
            <p className="text-gray-500 text-xs p-3 leading-relaxed">
              Your generated maps will show up here.
            </p>
          ) : (
            recentMaps.map(map => (
              <div
                key={map.id}
                className="group flex items-center gap-1 px-3 py-2 hover:bg-gray-700 cursor-pointer"
                style={{
                  background: currentMap?.id === map.id ? '#374151' : undefined,
                  borderLeft: currentMap?.id === map.id ? '2px solid #6366f1' : '2px solid transparent',
                }}
                onClick={() => loadMap(map.id)}
              >
                <span
                  className="flex-1 text-xs text-gray-200 truncate"
                  title={map.topic}
                >
                  {map.topic}
                </span>
                <button
                  onClick={e => { e.stopPropagation(); deleteMap(map.id) }}
                  className="opacity-0 group-hover:opacity-100 text-gray-500 hover:text-red-400 text-xs flex-shrink-0 transition-opacity"
                  title="Delete map"
                >
                  🗑
                </button>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
