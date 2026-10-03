/**
 * Map — the v1 tree idea repositioned as a supporting coverage map (UI spec §21):
 * analysis → sections → requirements, each requirement colored and labelled by status.
 * Clicking a requirement opens its finding/evidence.
 */
import { useMemo } from 'react'
import { Background, Controls, Handle, Position, ReactFlow, ReactFlowProvider } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import dagre from 'dagre'
import { Network } from 'lucide-react'
import { Empty, FINDING_STATUSES, STATUS_ICONS } from '@/components/kit'

const SIZES = { root: [240, 56], section: [200, 48], requirement: [260, 76] }

/** Position nodes left-to-right with dagre. */
function layout(nodes, edges) {
  const g = new dagre.graphlib.Graph()
  g.setDefaultEdgeLabel(() => ({}))
  g.setGraph({ rankdir: 'LR', nodesep: 14, ranksep: 70, marginx: 20, marginy: 20 })
  nodes.forEach((n) => g.setNode(n.id, { width: SIZES[n.type][0], height: SIZES[n.type][1] }))
  edges.forEach((e) => g.setEdge(e.source, e.target))
  dagre.layout(g)
  return nodes.map((n) => {
    const { x, y } = g.node(n.id)
    return { ...n, position: { x: x - SIZES[n.type][0] / 2, y: y - SIZES[n.type][1] / 2 } }
  })
}

const hidden = { opacity: 0, width: 1, height: 1, border: 0 }

/** Root node: the analysis itself. */
function RootNode({ data }) {
  return (
    <div className="rounded-lg flex h-14 w-60 items-center border border-secondary bg-surface px-4 text-sm font-semibold">
      <span className="truncate">{data.label}</span>
      <Handle type="source" position={Position.Right} style={hidden} />
    </div>
  )
}

/** Section node with a covered/total counter. */
function SectionNode({ data }) {
  return (
    <div className="rounded-lg flex h-12 w-[200px] items-center justify-between gap-2 border border-border bg-surface px-3 text-xs">
      <Handle type="target" position={Position.Left} style={hidden} />
      <span className="truncate font-medium">{data.label}</span>
      <span className="font-mono text-muted">{data.covered}/{data.total}</span>
      <Handle type="source" position={Position.Right} style={hidden} />
    </div>
  )
}

/** Requirement node colored by finding status (icon + label too, not color alone). */
function RequirementNode({ data }) {
  const Icon = data.status ? STATUS_ICONS[data.status] : null
  const color = data.status ? `var(--${data.status})` : 'var(--border)'
  return (
    <div className="rounded-lg h-[76px] w-[260px] cursor-pointer border bg-surface px-3 py-2 text-xs transition-colors hover:bg-surface-2" style={{ borderColor: color, borderLeftWidth: 3 }}>
      <Handle type="target" position={Position.Left} style={hidden} />
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-muted">{data.code}</span>
        {Icon
          ? <span className="inline-flex items-center gap-1 font-mono text-[10px] uppercase" style={{ color }}><Icon className="size-3" />{data.status}</span>
          : <span className="font-mono text-[10px] text-muted uppercase">not analysed</span>}
      </div>
      <p className="mt-1 line-clamp-2 leading-snug">{data.text}</p>
    </div>
  )
}

const nodeTypes = { root: RootNode, section: SectionNode, requirement: RequirementNode }

export default function MapTab({ project, requirements, findings, onView }) {
  const approved = useMemo(() => requirements.filter((r) => r.status === 'approved'), [requirements])
  const byRequirement = useMemo(() => new Map(findings.map((f) => [f.requirement.id, f])), [findings])

  const { nodes, edges } = useMemo(() => {
    const sections = new Map()
    approved.forEach((r) => {
      const key = r.section || 'General'
      sections.set(key, [...(sections.get(key) || []), r])
    })
    const n = [{ id: 'root', type: 'root', data: { label: project.name }, position: { x: 0, y: 0 } }]
    const e = []
    for (const [section, reqs] of sections) {
      const sid = `s:${section}`
      const covered = reqs.filter((r) => byRequirement.get(r.id)?.status === 'covered').length
      n.push({ id: sid, type: 'section', data: { label: section, covered, total: reqs.length }, position: { x: 0, y: 0 } })
      e.push({ id: `root-${sid}`, source: 'root', target: sid })
      for (const r of reqs) {
        n.push({ id: r.id, type: 'requirement', data: { code: r.code, text: r.text, status: byRequirement.get(r.id)?.status }, position: { x: 0, y: 0 } })
        e.push({ id: `${sid}-${r.id}`, source: sid, target: r.id })
      }
    }
    return { nodes: layout(n, e), edges: e.map((x) => ({ ...x, style: { stroke: 'var(--border)' } })) }
  }, [approved, byRequirement, project.name])

  if (!approved.length) {
    return <Empty icon={Network} title="Nothing to map yet">Approve requirements (and run the analysis) to see the coverage map.</Empty>
  }

  return (
    <div className="rounded-lg flex h-[75vh] min-h-[480px] flex-col border border-border">
      <ReactFlowProvider>
        <div className="min-h-0 flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ minZoom: 0.65, maxZoom: 1 }}   // stay readable; pan for the rest
          panOnScroll
          minZoom={0.2}
          nodesDraggable={false}
          nodesConnectable={false}
          proOptions={{ hideAttribution: true }}
          onNodeClick={(_, node) => node.type === 'requirement' && byRequirement.get(node.id) && onView(byRequirement.get(node.id))}
        >
          <Background gap={28} color="var(--border)" />
          <Controls showInteractive={false} />
        </ReactFlow>
        </div>
      </ReactFlowProvider>
      <div className="flex flex-wrap items-center gap-4 border-t border-border px-4 py-2 text-xs text-muted">
        {findings.length
          ? FINDING_STATUSES.map((st) => {
            const Icon = STATUS_ICONS[st]
            return <span key={st} className="inline-flex items-center gap-1.5 capitalize"><Icon className="size-3" style={{ color: `var(--${st})` }} />{st}</span>
          })
          : 'Run the analysis to color requirements by status.'}
        <span className="ml-auto">Scroll to pan · click a requirement to open its evidence</span>
      </div>
    </div>
  )
}
