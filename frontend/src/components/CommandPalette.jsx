// Ctrl+K / Cmd+K command palette — jump to a node, switch maps, or run an action
import { useEffect, useState, useCallback } from 'react'
import toast from 'react-hot-toast'
import useAtlasStore from '../store/atlasStore'
import {
  CommandDialog, CommandInput, CommandList,
  CommandEmpty, CommandGroup, CommandItem,
} from '@/components/ui/command'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function CommandPalette() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')

  const nodes            = useAtlasStore(s => s.nodes)
  const recentMaps        = useAtlasStore(s => s.recentMaps)
  const currentMap         = useAtlasStore(s => s.currentMap)
  const viewMode            = useAtlasStore(s => s.viewMode)
  const setViewMode          = useAtlasStore(s => s.setViewMode)
  const setSelectedNode       = useAtlasStore(s => s.setSelectedNode)
  const focusNode               = useAtlasStore(s => s.focusNode)
  const collapseAll              = useAtlasStore(s => s.collapseAll)
  const setCurrentMap             = useAtlasStore(s => s.setCurrentMap)
  const setNodes                   = useAtlasStore(s => s.setNodes)
  const setEdges                    = useAtlasStore(s => s.setEdges)

  // Ctrl+K / Cmd+K opens from anywhere; Esc closes via the underlying Dialog
  useEffect(() => {
    function onKey(e) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setOpen(o => !o)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const close = useCallback(() => { setOpen(false); setQuery('') }, [])

  function jumpToNode(node) {
    setSelectedNode(node)
    focusNode(node.id)
    close()
  }

  async function switchToMap(id) {
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
    close()
  }

  function runAction(id) {
    if (id === 'new-topic') {
      close()
      requestAnimationFrame(() => document.querySelector('input[placeholder]')?.focus())
      return
    }
    if (id === 'toggle-reading') {
      setViewMode(viewMode === 'read' ? 'tree' : 'read')
      close()
      return
    }
    if (id === 'collapse-all') {
      collapseAll()
      close()
      return
    }
  }

  const q = query.trim().toLowerCase()
  const filteredNodes = q
    ? nodes.filter(n => n.label.toLowerCase().includes(q)).slice(0, 8)
    : nodes.slice(0, 8)
  const filteredMaps = q
    ? recentMaps.filter(m => m.topic.toLowerCase().includes(q)).slice(0, 6)
    : recentMaps.slice(0, 6)

  const actions = [
    { id: 'new-topic', label: 'New topic…' },
    { id: 'toggle-reading', label: viewMode === 'read' ? 'Switch to tree view' : 'Toggle Reading Mode' },
    { id: 'collapse-all', label: 'Collapse all' },
  ].filter(a => !q || a.label.toLowerCase().includes(q))

  return (
    <CommandDialog open={open} onOpenChange={o => { setOpen(o); if (!o) setQuery('') }}>
      <CommandInput
        value={query}
        onValueChange={setQuery}
        placeholder="Search concepts, maps, or actions…"
      />
      <CommandList>
        {filteredNodes.length === 0 && filteredMaps.length === 0 && actions.length === 0 && (
          <CommandEmpty>No results found.</CommandEmpty>
        )}

        {currentMap && filteredNodes.length > 0 && (
          <CommandGroup heading="Concepts in this map">
            {filteredNodes.map(n => (
              <CommandItem key={n.id} value={n.id} onSelect={() => jumpToNode(n)}>
                {n.label}
              </CommandItem>
            ))}
          </CommandGroup>
        )}

        {filteredMaps.length > 0 && (
          <CommandGroup heading="Recent maps">
            {filteredMaps.map(m => (
              <CommandItem key={m.id} value={m.id} onSelect={() => switchToMap(m.id)}>
                {m.topic}
              </CommandItem>
            ))}
          </CommandGroup>
        )}

        {actions.length > 0 && (
          <CommandGroup heading="Actions">
            {actions.map(a => (
              <CommandItem key={a.id} value={a.id} onSelect={() => runAction(a.id)}>
                {a.label}
              </CommandItem>
            ))}
          </CommandGroup>
        )}
      </CommandList>
    </CommandDialog>
  )
}
