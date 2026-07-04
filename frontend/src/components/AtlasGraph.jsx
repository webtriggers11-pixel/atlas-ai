// Main React Flow canvas — collapsible top-down tree layout
import { useMemo, useEffect, useCallback, useRef } from 'react'
import {
  ReactFlow, Background, Controls,
  useNodesState, useEdgesState,
  ReactFlowProvider, useReactFlow,
  BackgroundVariant,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import toast from 'react-hot-toast'

import CustomNode from './CustomNode'
import EmptyState from './EmptyState'
import LoadingSkeleton from './LoadingSkeleton'
import useAtlasStore from '../store/atlasStore'
import { getLayoutedElements } from '../utils/layoutGraph'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const NODE_TYPES = { custom: CustomNode }

/** Calls fitView whenever expandedNodeIds changes (after a short delay for dagre). */
function FitViewOnExpand({ expandedNodeIds }) {
  const { fitView } = useReactFlow()
  const isFirst = useRef(true)
  useEffect(() => {
    if (isFirst.current) { isFirst.current = false; return }
    const id = setTimeout(() => fitView({ padding: 0.3, duration: 400 }), 50)
    return () => clearTimeout(id)
  }, [expandedNodeIds, fitView])
  return null
}

/** Calls fitView whenever the node count changes (initial map load). */
function FitViewOnLoad({ nodeCount }) {
  const { fitView } = useReactFlow()
  useEffect(() => {
    if (nodeCount > 0) {
      const id = setTimeout(() => fitView({ padding: 0.3, duration: 400 }), 60)
      return () => clearTimeout(id)
    }
  }, [nodeCount, fitView])
  return null
}

/** Walk parent_id chain to compute depth (0 = root). */
function getNodeDepth(nodeId, allNodes) {
  let depth = 0
  let cur = allNodes.find(n => n.id === nodeId)
  while (cur?.parent_id) {
    depth++
    cur = allNodes.find(n => n.id === cur.parent_id)
  }
  return depth
}

function AtlasGraphInner({ onExpandClick, onCollapseClick }) {
  const storeNodes      = useAtlasStore(s => s.nodes)
  const storeEdges      = useAtlasStore(s => s.edges)
  const selectedNode    = useAtlasStore(s => s.selectedNode)
  const isGenerating    = useAtlasStore(s => s.isGenerating)
  const currentMap      = useAtlasStore(s => s.currentMap)
  const expandedNodeIds = useAtlasStore(s => s.expandedNodeIds)
  const setSelectedNode = useAtlasStore(s => s.setSelectedNode)

  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  // Recompute layout whenever store data or expansion state changes
  const { rfNodes, rfEdges } = useMemo(() => {
    if (!currentMap || storeNodes.length === 0) return { rfNodes: [], rfEdges: [] }

    // getLayoutedElements works on raw API nodes/edges
    const { nodes: positioned, edges: visible } = getLayoutedElements(
      storeNodes, storeEdges, expandedNodeIds
    )

    const rfNodes = positioned.map(apiNode => {
      const hasChildren = storeNodes.some(n => n.parent_id === apiNode.id)
      const isExpanded  = expandedNodeIds.has(apiNode.id)
      const childCount  = storeNodes.filter(n => n.parent_id === apiNode.id).length
      const depth       = getNodeDepth(apiNode.id, storeNodes)
      const stdExp      = apiNode.explanations?.find(e => e.depth === 'standard')

      return {
        id:   apiNode.id,
        type: 'custom',
        position: apiNode.position,
        data: {
          nodeId:          apiNode.id,
          label:           apiNode.label,
          summary:         stdExp?.content ?? '',
          isRoot:          apiNode.is_root,
          isSelected:      apiNode.id === selectedNode?.id,
          hasChildren,
          isExpanded,
          childCount,
          depth,
          onExpandClick,
          onCollapseClick,
        },
      }
    })

    const rfEdges = visible.map(e => {
      const active = selectedNode &&
        (e.source_node_id === selectedNode.id || e.target_node_id === selectedNode.id)
      return {
        id:     e.id,
        source: e.source_node_id,
        target: e.target_node_id,
        type:   'smoothstep',
        style:  { stroke: active ? '#A78BFA' : '#E4E4E7', strokeWidth: 1.5 },
      }
    })

    return { rfNodes, rfEdges }
  }, [storeNodes, storeEdges, expandedNodeIds, selectedNode?.id, currentMap?.id,
      onExpandClick, onCollapseClick])

  // Push computed layout into React Flow's internal state
  useEffect(() => {
    setNodes(rfNodes)
    setEdges(rfEdges)
  }, [rfNodes, rfEdges])

  const onNodeClick = useCallback((_, node) => {
    const apiNode = storeNodes.find(n => n.id === node.id)
    setSelectedNode(apiNode ?? null)
  }, [storeNodes, setSelectedNode])

  const onPaneClick = useCallback(() => setSelectedNode(null), [setSelectedNode])

  if (isGenerating) return <LoadingSkeleton />
  if (!currentMap)  return <EmptyState />

  return (
    <div style={{ flex: 1, height: '100%' }}>
      <ReactFlow
        nodes={nodes} edges={edges}
        onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
        onNodeClick={onNodeClick} onPaneClick={onPaneClick}
        nodeTypes={NODE_TYPES}
        nodesConnectable={false} nodesDraggable={true}
        minZoom={0.2} maxZoom={1.5}
        deleteKeyCode={null}
        proOptions={{ hideAttribution: true }}
      >
        <FitViewOnLoad   nodeCount={nodes.length} />
        <FitViewOnExpand expandedNodeIds={expandedNodeIds} />
        <Background variant={BackgroundVariant.Dots} color="#E4E4E7" gap={24} size={1} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  )
}

export default function AtlasGraph() {
  const storeNodes        = useAtlasStore(s => s.nodes)
  const storeEdges        = useAtlasStore(s => s.edges)
  const currentMap        = useAtlasStore(s => s.currentMap)
  const depth             = useAtlasStore(s => s.depth)
  const expandedNodeIds   = useAtlasStore(s => s.expandedNodeIds)
  const setNodes          = useAtlasStore(s => s.setNodes)
  const setEdges          = useAtlasStore(s => s.setEdges)
  const toggleNodeExpanded = useAtlasStore(s => s.toggleNodeExpanded)
  const setIsExpanding    = useAtlasStore(s => s.setIsExpanding)

  const onExpandClick = useCallback(async (nodeId) => {
    // If children already exist in store, just show/hide them
    const hasChildren = storeNodes.some(n => n.parent_id === nodeId)
    if (hasChildren) {
      toggleNodeExpanded(nodeId)
      return
    }

    // First time expanding — call the API to generate sub-concepts
    setIsExpanding(true)
    try {
      const res = await fetch(
        `${API}/maps/${currentMap.id}/nodes/${nodeId}/expand`,
        { method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ depth }) }
      )
      if (!res.ok) throw new Error()
      const { new_nodes, new_edges } = await res.json()

      if (new_nodes.length === 0) {
        toast('Nothing new to expand here — try a different node')
        return
      }

      setNodes([...storeNodes, ...new_nodes])
      setEdges([...storeEdges, ...new_edges])
      toggleNodeExpanded(nodeId)
    } catch {
      toast.error('Could not expand — try again')
    } finally {
      setIsExpanding(false)
    }
  }, [storeNodes, storeEdges, currentMap, depth, toggleNodeExpanded, setNodes, setEdges, setIsExpanding])

  const onCollapseClick = useCallback((nodeId) => {
    toggleNodeExpanded(nodeId)
  }, [toggleNodeExpanded])

  return (
    <ReactFlowProvider>
      <AtlasGraphInner
        onExpandClick={onExpandClick}
        onCollapseClick={onCollapseClick}
      />
    </ReactFlowProvider>
  )
}
