// Global state store — holds map data, UI state, and simple setters
import { create } from 'zustand'

const useAtlasStore = create((set) => ({
  currentMap:  null,
  nodes:       [],
  edges:       [],
  selectedNode: null,
  depth:       'standard',
  sidebarOpen: true,
  isGenerating: false,
  isExpanding:  false,
  recentMaps:  [],

  expandedNodeIds: new Set(),
  viewMode: 'tree',   // 'tree' | 'read'

  setCurrentMap:  (map)   => set({ currentMap: map }),
  setNodes:       (nodes) => set({ nodes }),
  setEdges:       (edges) => set({ edges }),
  setSelectedNode:(node)  => set({ selectedNode: node }),
  setDepth:       (depth) => set({ depth }),
  toggleSidebar:  ()      => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setIsGenerating:(v)     => set({ isGenerating: v }),
  setIsExpanding: (v)     => set({ isExpanding: v }),
  setRecentMaps:  (maps)  => set({ recentMaps: maps }),

  toggleNodeExpanded: (nodeId) => set((state) => {
    const next = new Set(state.expandedNodeIds)
    if (next.has(nodeId)) {
      next.delete(nodeId)
    } else {
      next.add(nodeId)
    }
    return { expandedNodeIds: next }
  }),

  collapseAll: () => set({ expandedNodeIds: new Set() }),
  setViewMode: (mode) => set({ viewMode: mode }),
}))

export default useAtlasStore
