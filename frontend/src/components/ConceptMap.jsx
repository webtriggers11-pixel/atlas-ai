import { useEffect, useCallback } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  BackgroundVariant,
  useReactFlow,
  ReactFlowProvider,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import ConceptNode from './ConceptNode'
import useAtlasStore from '../store/atlasStore'
import { computeLayout } from '../utils/layout'

// Must be outside component — React Flow warns if this object changes every render
const NODE_TYPES = { conceptNode: ConceptNode }

/** Convert API nodes → React Flow node format. */
function buildRFNodes(apiNodes, positions, selectedId) {
  return apiNodes.map(n => ({
    id:       n.id,
    type:     'conceptNode',
    position: positions[n.id] ?? { x: 0, y: 0 },
    selected: n.id === selectedId,
    data:     { label: n.label, isRoot: n.is_root },
  }))
}

/** Convert API edges → React Flow edge format, highlighting selected node's edges. */
function buildRFEdges(apiEdges, selectedId) {
  return apiEdges.map(e => {
    const active = selectedId && (e.source_node_id === selectedId || e.target_node_id === selectedId)
    return {
      id:     e.id,
      source: e.source_node_id,
      target: e.target_node_id,
      type:   'smoothstep',
      style: {
        stroke:      active ? '#6366f1' : '#374151',
        strokeWidth: active ? 2 : 1.5,
        opacity:     active ? 1 : 0.5,
      },
      animated: !!active,
    }
  })
}

/**
 * Sits inside ReactFlow so it can call useReactFlow().
 * Triggers fitView every time the node count changes (map loaded or expanded).
 */
function FitViewOnChange({ nodeCount }) {
  const { fitView } = useReactFlow()
  useEffect(() => {
    if (nodeCount > 0) {
      // Small delay ensures React Flow has rendered the nodes before fitting
      const id = setTimeout(() => fitView({ padding: 0.25, duration: 350 }), 60)
      return () => clearTimeout(id)
    }
  }, [nodeCount, fitView])
  return null
}

/** Inner canvas — wrapped by ReactFlowProvider below. */
function ConceptMapInner() {
  const currentMap     = useAtlasStore(s => s.currentMap)
  const selectedNodeId = useAtlasStore(s => s.selectedNodeId)
  const isGenerating   = useAtlasStore(s => s.isGenerating)
  const selectNode     = useAtlasStore(s => s.selectNode)
  const closePanel     = useAtlasStore(s => s.closePanel)

  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  // Rebuild layout whenever the map changes or nodes are added (expand)
  useEffect(() => {
    if (!currentMap) { setNodes([]); setEdges([]); return }
    const positions = computeLayout(currentMap.nodes, currentMap.edges)
    setNodes(buildRFNodes(currentMap.nodes, positions, selectedNodeId))
    setEdges(buildRFEdges(currentMap.edges, selectedNodeId))
  }, [currentMap?.id, currentMap?.nodes.length])

  // Update edge / selection styles when selected node changes — no layout rebuild
  useEffect(() => {
    if (!currentMap) return
    setNodes(nds => nds.map(n => ({ ...n, selected: n.id === selectedNodeId })))
    setEdges(eds => eds.map(e => {
      const active = selectedNodeId && (e.source === selectedNodeId || e.target === selectedNodeId)
      return {
        ...e,
        style: { stroke: active ? '#6366f1' : '#374151', strokeWidth: active ? 2 : 1.5, opacity: active ? 1 : 0.5 },
        animated: !!active,
      }
    }))
  }, [selectedNodeId])

  const onNodeClick  = useCallback((_, node) => selectNode(node.id), [selectNode])
  const onPaneClick  = useCallback(() => closePanel(), [closePanel])

  // ── Empty state ───────────────────────────────────────────────────────────
  if (!currentMap && !isGenerating) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-center px-6">
        <div style={{ fontSize: 64, opacity: 0.08, lineHeight: 1 }}>◉</div>
        <p className="text-gray-400 text-sm max-w-xs leading-relaxed mt-6">
          Type a topic above and press <strong className="text-gray-200">Generate</strong> to build your first concept map.
        </p>
      </div>
    )
  }

  // ── Generating skeleton ───────────────────────────────────────────────────
  if (isGenerating) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-6">
        <div
          className="rounded-full border-2 border-indigo-400 w-16 h-16 animate-pulse"
          style={{ boxShadow: '0 0 28px rgba(99,102,241,0.35)' }}
        />
        <div className="flex gap-3 flex-wrap justify-center px-8">
          {[100, 130, 90, 115, 95, 120].map((w, i) => (
            <div
              key={i}
              className="rounded-lg animate-pulse"
              style={{ width: w, height: 38, background: '#374151', animationDelay: `${i * 0.12}s` }}
            />
          ))}
        </div>
        <p className="text-gray-500 text-xs">Asking the AI — this can take up to a minute…</p>
      </div>
    )
  }

  // ── React Flow canvas ─────────────────────────────────────────────────────
  return (
    <div className="flex-1 h-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        nodeTypes={NODE_TYPES}
        minZoom={0.15}
        maxZoom={2.5}
        deleteKeyCode={null}
        proOptions={{ hideAttribution: true }}
      >
        {/* Triggers fitView each time node count changes */}
        <FitViewOnChange nodeCount={nodes.length} />

        <Background variant={BackgroundVariant.Dots} gap={28} size={1} color="#1e2533" />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  )
}

/** Wrap in ReactFlowProvider so child components can call useReactFlow(). */
export default function ConceptMap() {
  return (
    <ReactFlowProvider>
      <ConceptMapInner />
    </ReactFlowProvider>
  )
}
