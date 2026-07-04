// Root layout — all views and keyboard shortcuts wired together
import { useEffect, useRef } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Toaster } from 'react-hot-toast'

import TopBar          from './components/TopBar'
import Sidebar         from './components/Sidebar'
import AtlasGraph      from './components/AtlasGraph'
import NodeDetailPanel from './components/NodeDetailPanel'
import ViewModeToggle  from './components/ViewModeToggle'
import ReadingMode     from './components/ReadingMode'
import GraphBreadcrumb from './components/GraphBreadcrumb'
import useAtlasStore   from './store/atlasStore'

export default function App() {
  const selectedNode      = useAtlasStore(s => s.selectedNode)
  const viewMode          = useAtlasStore(s => s.viewMode)
  const storeNodes        = useAtlasStore(s => s.nodes)
  const expandedNodeIds   = useAtlasStore(s => s.expandedNodeIds)
  const currentMap        = useAtlasStore(s => s.currentMap)
  const setSelectedNode   = useAtlasStore(s => s.setSelectedNode)
  const setViewMode       = useAtlasStore(s => s.setViewMode)
  const toggleNodeExpanded = useAtlasStore(s => s.toggleNodeExpanded)
  const collapseAll       = useAtlasStore(s => s.collapseAll)
  const topicInputRef     = useRef(null)

  // ── Keyboard shortcuts ─────────────────────────────────────────────────
  useEffect(() => {
    function handleKey(e) {
      const tag = document.activeElement?.tagName
      const isTyping = tag === 'INPUT' || tag === 'TEXTAREA'

      // "/" — focus topic input (always)
      if (e.key === '/' && !isTyping) {
        e.preventDefault()
        document.querySelector('input[placeholder]')?.focus()
        return
      }

      // R — toggle reading mode
      if (e.key === 'r' && !isTyping) {
        const s = useAtlasStore.getState()
        if (s.viewMode === 'read') {
          s.setViewMode('tree')
        } else {
          s.setSelectedNode(null)
          s.setViewMode('read')
        }
        return
      }

      // Escape
      if (e.key === 'Escape') {
        const s = useAtlasStore.getState()
        if (s.viewMode === 'read') { s.setViewMode('tree'); return }
        if (s.selectedNode) { s.setSelectedNode(null); return }
        if (isTyping) document.activeElement.blur()
        return
      }

      if (isTyping) return  // don't intercept while user is typing

      const s = useAtlasStore.getState()
      const sel = s.selectedNode
      if (!sel) return

      // E — expand selected node
      if (e.key === 'e' || e.key === 'E') {
        if (!s.expandedNodeIds.has(sel.id)) toggleNodeExpanded(sel.id)
        return
      }

      const siblings = s.nodes.filter(n => n.parent_id === sel.parent_id)
      const selfIdx  = siblings.findIndex(n => n.id === sel.id)

      // ArrowDown — next sibling
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        const next = siblings[selfIdx + 1]
        if (next) setSelectedNode(next)
        return
      }
      // ArrowUp — previous sibling
      if (e.key === 'ArrowUp') {
        e.preventDefault()
        const prev = siblings[selfIdx - 1]
        if (prev) setSelectedNode(prev)
        return
      }
      // ArrowLeft — go to parent
      if (e.key === 'ArrowLeft') {
        e.preventDefault()
        const parent = s.nodes.find(n => n.id === sel.parent_id)
        if (parent) setSelectedNode(parent)
        return
      }
      // ArrowRight — go to first child or expand
      if (e.key === 'ArrowRight') {
        e.preventDefault()
        const firstChild = s.nodes.find(n => n.parent_id === sel.id)
        if (firstChild && s.expandedNodeIds.has(sel.id)) {
          setSelectedNode(firstChild)
        } else {
          toggleNodeExpanded(sel.id)
        }
        return
      }
    }

    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [setSelectedNode, setViewMode, toggleNodeExpanded])

  const showCollapseAll = viewMode === 'tree' && expandedNodeIds.size > 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: 'var(--bg)' }}>
      <TopBar inputRef={topicInputRef} />

      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        <Sidebar />

        {/* Main canvas area */}
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}>

          {/* ViewModeToggle — always visible top-right */}
          {currentMap && <ViewModeToggle />}

          {/* Node count — top-right next to toggle */}
          {currentMap && viewMode === 'tree' && (
            <div style={{
              position: 'absolute', top: 22, right: 150, zIndex: 10,
              fontSize: 12, color: 'var(--text-muted)',
              pointerEvents: 'none',
            }}>
              {storeNodes.length} concepts
            </div>
          )}

          {/* Collapse All — top-left of canvas */}
          <AnimatePresence>
            {showCollapseAll && (
              <motion.button
                initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
                onClick={collapseAll}
                style={{
                  position: 'absolute', top: 16, left: 16, zIndex: 10,
                  background: 'rgba(255,255,255,0.9)',
                  border: '1px solid var(--border)', borderRadius: 6,
                  padding: '4px 10px', fontSize: 12, color: 'var(--text-muted)',
                  cursor: 'pointer', fontFamily: 'inherit',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
                }}
              >
                Collapse all
              </motion.button>
            )}
          </AnimatePresence>

          {/* Tree view / Reading mode — animated switch */}
          <AnimatePresence mode="wait">
            {viewMode === 'tree' ? (
              <motion.div
                key="tree"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.25 }}
                style={{ flex: 1, display: 'flex', overflow: 'hidden', position: 'relative' }}
              >
                {/* Breadcrumb sits on top of canvas */}
                <AnimatePresence>
                  {selectedNode && <GraphBreadcrumb key="crumb" />}
                </AnimatePresence>

                <AtlasGraph />

                {/* Side panel */}
                <AnimatePresence>
                  {selectedNode && <NodeDetailPanel key="panel" />}
                </AnimatePresence>
              </motion.div>
            ) : (
              <motion.div
                key="read"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                transition={{ duration: 0.25 }}
                style={{ flex: 1, display: 'flex', overflow: 'hidden' }}
              >
                <ReadingMode />
              </motion.div>
            )}
          </AnimatePresence>

        </div>
      </div>

      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: '#09090B', color: '#FAFAFA',
            borderRadius: '8px', fontSize: '14px',
            border: '1px solid #27272A',
            fontFamily: 'Plus Jakarta Sans, sans-serif',
          },
        }}
      />
    </div>
  )
}
