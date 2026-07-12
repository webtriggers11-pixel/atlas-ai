// Left sidebar — collapsible list of recently saved maps
import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import useAtlasStore from '../store/atlasStore'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogDescription, DialogFooter,
} from '@/components/ui/dialog'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function MapIcon() {
  return (
    <svg width="32" height="32" viewBox="0 0 24 24" fill="none"
      stroke="#E4E4E7" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21" />
      <line x1="9" y1="3" x2="9" y2="18" /><line x1="15" y1="6" x2="15" y2="21" />
    </svg>
  )
}

function ChevronIcon({ open }) {
  return (
    <motion.svg
      animate={{ rotate: open ? 0 : 180 }}
      transition={{ duration: 0.2 }}
      width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
    >
      <polyline points="15 18 9 12 15 6" />
    </motion.svg>
  )
}

export default function Sidebar() {
  const sidebarOpen   = useAtlasStore(s => s.sidebarOpen)
  const toggleSidebar = useAtlasStore(s => s.toggleSidebar)
  const recentMaps    = useAtlasStore(s => s.recentMaps)
  const setRecentMaps = useAtlasStore(s => s.setRecentMaps)
  const currentMap    = useAtlasStore(s => s.currentMap)
  const setCurrentMap = useAtlasStore(s => s.setCurrentMap)
  const setNodes      = useAtlasStore(s => s.setNodes)
  const setEdges      = useAtlasStore(s => s.setEdges)
  const setSelectedNode = useAtlasStore(s => s.setSelectedNode)
  const storeNodes      = useAtlasStore(s => s.nodes)
  const collapseAll     = useAtlasStore(s => s.collapseAll)

  const [pendingDelete, setPendingDelete] = useState(null) // { id, topic } | null

  // Load recent maps on mount
  useEffect(() => {
    fetch(`${API}/maps`)
      .then(r => r.json())
      .then(setRecentMaps)
      .catch(() => {})
  }, [])

  async function loadMap(id) {
    try {
      const res = await fetch(`${API}/maps/${id}`)
      const map = await res.json()
      setCurrentMap(map)
      setNodes(map.nodes)
      setEdges(map.edges)
      setSelectedNode(null)
      collapseAll()
    } catch {
      toast.error('Could not load map')
    }
  }

  async function confirmDeleteMap() {
    if (!pendingDelete) return
    const id = pendingDelete.id
    setPendingDelete(null)
    try {
      await fetch(`${API}/maps/${id}`, { method: 'DELETE' })
      setRecentMaps(recentMaps.filter(m => m.id !== id))
      if (currentMap?.id === id) {
        setCurrentMap(null)
        setNodes([])
        setEdges([])
        setSelectedNode(null)
      }
      toast.success('Map deleted')
    } catch {
      toast.error('Could not delete map')
    }
  }

  function formatDate(iso) {
    const d = new Date(iso)
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  }

  return (
    <motion.div
      animate={{ width: sidebarOpen ? 260 : 40 }}
      transition={{ duration: 0.2, ease: 'easeInOut' }}
      style={{
        background: 'var(--surface)',
        borderRight: '1px solid var(--border)',
        height: '100%',
        overflow: 'hidden',
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Header row */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: sidebarOpen ? 'space-between' : 'center',
        padding: sidebarOpen ? '16px 16px 12px' : '16px 0',
        borderBottom: '1px solid var(--border)',
        flexShrink: 0,
      }}>
        {sidebarOpen && (
          <span style={{
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            color: 'var(--text-muted)',
          }}>
            Recent Maps
          </span>
        )}
        <button
          onClick={toggleSidebar}
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: 'var(--text-muted)',
            display: 'flex',
            alignItems: 'center',
            padding: 4,
            borderRadius: 4,
          }}
          title={sidebarOpen ? 'Collapse' : 'Expand'}
        >
          <ChevronIcon open={sidebarOpen} />
        </button>
      </div>

      {/* Map list */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            style={{ flex: 1, overflowY: 'auto', padding: 8 }}
          >
            {recentMaps.length === 0 ? (
              <div style={{
                display: 'flex', flexDirection: 'column',
                alignItems: 'center', justifyContent: 'center',
                padding: '40px 16px', gap: 10, textAlign: 'center',
              }}>
                <MapIcon />
                <p style={{ fontSize: 14, color: 'var(--text-muted)', marginTop: 4 }}>No maps yet</p>
                <p style={{ fontSize: 12, color: '#A1A1AA' }}>Generate your first topic above</p>
              </div>
            ) : (
              recentMaps.map((map, i) => {
                const isActive = currentMap?.id === map.id
                return (
                  <motion.div
                    key={map.id}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                    onClick={() => loadMap(map.id)}
                    className="map-item"
                    style={{
                      padding: '10px 12px',
                      borderRadius: 'var(--radius-btn)',
                      cursor: 'pointer',
                      background: isActive ? 'var(--accent-light)' : 'transparent',
                      borderLeft: isActive ? '3px solid var(--accent)' : '3px solid transparent',
                      display: 'flex',
                      alignItems: 'flex-start',
                      justifyContent: 'space-between',
                      gap: 8,
                      marginBottom: 2,
                      transition: 'background 0.12s',
                    }}
                    onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = '#F4F4F5' }}
                    onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = 'transparent' }}
                  >
                    <div style={{ minWidth: 0, flex: 1 }}>
                      <p style={{
                        fontSize: 14, fontWeight: 500,
                        color: isActive ? 'var(--accent-text)' : 'var(--text)',
                        overflow: 'hidden', textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap', maxWidth: 140,
                      }}>
                        {map.topic}
                      </p>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 3 }}>
                        <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                          {formatDate(map.created_at)}
                        </p>
                        {isActive && storeNodes.length > 0 && (
                          <Badge style={{ fontSize: 11, padding: '1px 7px' }}>
                            {storeNodes.length} concepts
                          </Badge>
                        )}
                      </div>
                    </div>

                    {/* Delete button — shows on hover via CSS class */}
                    <button
                      onClick={e => { e.stopPropagation(); setPendingDelete({ id: map.id, topic: map.topic }) }}
                      className="delete-btn"
                      style={{
                        background: 'none',
                        border: 'none',
                        cursor: 'pointer',
                        color: 'var(--text-muted)',
                        fontSize: 14,
                        lineHeight: 1,
                        padding: '2px 4px',
                        borderRadius: 4,
                        flexShrink: 0,
                        opacity: 0,
                        transition: 'opacity 0.1s, color 0.1s',
                      }}
                      title="Delete map"
                    >
                      ✕
                    </button>
                  </motion.div>
                )
              })
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Hover CSS for delete button and map item */}
      <style>{`
        .map-item:hover .delete-btn { opacity: 1 !important; }
        .delete-btn:hover { color: #EF4444 !important; }
      `}</style>

      <Dialog open={!!pendingDelete} onOpenChange={open => !open && setPendingDelete(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete this map?</DialogTitle>
            <DialogDescription>
              "{pendingDelete?.topic}" and all its concepts will be permanently removed. This can't be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setPendingDelete(null)}>Cancel</Button>
            <Button variant="destructive" onClick={confirmDeleteMap}>Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </motion.div>
  )
}
