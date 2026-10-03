/**
 * Requirements — the human review step: AI extracts draft requirements, the user edits,
 * merges, rejects or approves them. Only approved requirements are analysed.
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { AlertTriangle, Check, ClipboardList, Merge, Plus, Sparkles, X } from 'lucide-react'
import { api } from '@/lib/api'
import { keys, useAction, useRequirements } from '@/lib/queries'
import { cn } from '@/lib/utils'
import { Button, Empty, Field, Input, Modal, Notice, Panel, Skeleton, StatusPill, Tag, Textarea } from '@/components/kit'

const FILTERS = ['all', 'draft', 'approved', 'rejected']

/** Requirement text that becomes a textarea on click; saves on blur or Ctrl/⌘+Enter. */
function EditableText({ requirement, projectId }) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(requirement.text)
  useEffect(() => { setValue(requirement.text) }, [requirement.text])
  const save = useAction((text) => api.updateRequirement(requirement.id, { text }), { invalidate: [keys.requirements(projectId)] })

  const commit = () => {
    setEditing(false)
    if (value.trim() && value.trim() !== requirement.text) save.mutate(value.trim())
    else setValue(requirement.text)
  }
  if (editing) {
    return (
      <Textarea
        autoFocus value={value} className="min-h-16 text-sm"
        onChange={(e) => setValue(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) commit()
          if (e.key === 'Escape') { setValue(requirement.text); setEditing(false) }
        }}
      />
    )
  }
  return (
    <button
      type="button"
      onClick={() => setEditing(true)}
      title="Click to edit"
      className={cn('w-full cursor-text text-left text-sm leading-relaxed', requirement.status === 'rejected' && 'text-muted line-through')}
    >
      {requirement.text}
    </button>
  )
}

/** One requirement row with select box, approve/reject toggles and metadata tags. */
function RequirementRow({ requirement, projectId, selected, onSelect }) {
  const setStatus = useAction((status) => api.updateRequirement(requirement.id, { status }), {
    invalidate: [keys.requirements(projectId), keys.project(projectId)],
  })
  return (
    <motion.li layout initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      className={cn('grid grid-cols-[auto_4.5rem_1fr_auto] items-start gap-3 border-b border-border px-4 py-3 last:border-b-0', selected && 'bg-secondary/5')}
    >
      <input
        type="checkbox" checked={selected} onChange={() => onSelect(requirement.id)}
        aria-label={`Select ${requirement.code}`} className="mt-1 size-4 cursor-pointer accent-[var(--secondary)]"
      />
      <span className="mt-0.5 font-mono text-xs text-muted">{requirement.code}</span>
      <div className="min-w-0 space-y-1.5">
        <EditableText requirement={requirement} projectId={projectId} />
        <div className="flex flex-wrap gap-1.5">
          {requirement.section && <Tag>{requirement.section}</Tag>}
          {requirement.origin === 'manual' && <Tag>manual</Tag>}
        </div>
      </div>
      <div className="flex items-center gap-1">
        <StatusPill status={requirement.status} className="mr-1 hidden sm:inline-flex" />
        <Button
          variant="ghost" size="icon" aria-label="Approve" title="Approve"
          className={cn(requirement.status === 'approved' && 'text-success')}
          onClick={() => setStatus.mutate(requirement.status === 'approved' ? 'draft' : 'approved')}
        ><Check className="size-4" /></Button>
        <Button
          variant="ghost" size="icon" aria-label="Reject" title="Reject"
          className={cn(requirement.status === 'rejected' && 'text-danger')}
          onClick={() => setStatus.mutate(requirement.status === 'rejected' ? 'draft' : 'rejected')}
        ><X className="size-4" /></Button>
      </div>
    </motion.li>
  )
}

/** Dialog to add a requirement by hand. */
function AddRequirementModal({ projectId, open, onClose }) {
  const [text, setText] = useState('')
  const [section, setSection] = useState('')
  const add = useAction(() => api.addRequirement(projectId, text.trim(), section.trim()), {
    invalidate: [keys.requirements(projectId), keys.project(projectId)],
    success: (r) => `Added ${r.code}`,
    onSuccess: () => { setText(''); setSection(''); onClose() },
  })
  return (
    <Modal open={open} onClose={onClose} title="Add requirement" description="Manual requirements start approved."
      footer={<><Button variant="outline" onClick={onClose}>Cancel</Button><Button disabled={!text.trim()} loading={add.isPending} onClick={() => add.mutate()}>Add</Button></>}
    >
      <div className="space-y-4">
        <Field label="Requirement"><Textarea autoFocus value={text} onChange={(e) => setText(e.target.value)} placeholder="The system must…" /></Field>
        <Field label="Section (optional)"><Input value={section} onChange={(e) => setSection(e.target.value)} placeholder="e.g. Authentication" /></Field>
      </div>
    </Modal>
  )
}

export default function RequirementsTab({ project, documentsReady }) {
  const projectId = project.id
  const { data: requirements, isLoading } = useRequirements(projectId)
  const [filter, setFilter] = useState('all')
  const [selected, setSelected] = useState(new Set())
  const [adding, setAdding] = useState(false)
  const running = project.extraction_status === 'running'
  const invalidate = [keys.requirements(projectId), keys.project(projectId)]

  // Refresh the list on return too: with inline (eager) jobs, extraction has already finished by now
  const extract = useAction(() => api.extractRequirements(projectId), { invalidate })
  const approveAll = useAction(() => api.approveAll(projectId), { invalidate, success: (r) => `Approved ${r.approved}` })
  const merge = useAction(() => api.mergeRequirements(projectId, [...selected]), {
    invalidate, success: (r) => `Merged into ${r.code}`, onSuccess: () => setSelected(new Set()),
  })

  // The project query polls while extraction runs; when it flips running → finished, reload the list once.
  const queryClient = useQueryClient()
  const wasRunning = useRef(running)
  useEffect(() => {
    if (wasRunning.current && !running) queryClient.invalidateQueries({ queryKey: keys.requirements(projectId) })
    wasRunning.current = running
  }, [running, projectId, queryClient])

  const list = requirements || []
  const counts = useMemo(() => FILTERS.reduce((acc, f) => ({
    ...acc, [f]: f === 'all' ? list.length : list.filter((r) => r.status === f).length,
  }), {}), [list])
  const visible = filter === 'all' ? list : list.filter((r) => r.status === filter)
  const toggle = (id) => setSelected((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); return n })

  return (
    <div className="space-y-5">
      <Panel className="flex flex-wrap items-center justify-between gap-4 p-5">
        <div>
          <p className="font-semibold">Extract requirements with AI</p>
          <p className="mt-1 text-sm text-muted">
            Atomic, testable requirements are pulled from your reference documents. Re-running only replaces unreviewed drafts.
          </p>
        </div>
        <Button
          variant="accent" icon={Sparkles} loading={running || extract.isPending}
          disabled={!documentsReady}
          onClick={() => extract.mutate()}
        >
          {running ? 'Extracting…' : list.length ? 'Re-extract' : 'Extract'}
        </Button>
        {!documentsReady && <p className="w-full text-xs text-muted">Upload and process at least one reference and one existing document first.</p>}
        {project.extraction_status === 'failed' && <Notice icon={AlertTriangle} className="w-full">{project.extraction_error}</Notice>}
        {project.extraction_status === 'completed' && project.extraction_error && (
          <Notice tone="warning" icon={AlertTriangle} className="w-full">{project.extraction_error}</Notice>
        )}
      </Panel>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex gap-px border border-border bg-border">
          {FILTERS.map((f) => (
            <button key={f} type="button" onClick={() => setFilter(f)}
              className={cn('cursor-pointer px-3 py-1.5 text-xs capitalize transition-colors', filter === f ? 'bg-surface font-semibold' : 'bg-background text-muted hover:text-foreground')}
            >
              {f} <span className="font-mono text-muted">{counts[f]}</span>
            </button>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" size="sm" icon={Plus} onClick={() => setAdding(true)}>Add</Button>
          <Button variant="outline" size="sm" icon={Check} disabled={!counts.draft} loading={approveAll.isPending} onClick={() => approveAll.mutate()}>
            Approve all drafts
          </Button>
        </div>
      </div>

      {isLoading ? <Skeleton className="h-64" /> : visible.length ? (
        <Panel>
          <ul>
            <AnimatePresence initial={false}>
              {visible.map((r) => (
                <RequirementRow key={r.id} requirement={r} projectId={projectId} selected={selected.has(r.id)} onSelect={toggle} />
              ))}
            </AnimatePresence>
          </ul>
        </Panel>
      ) : (
        <Empty icon={ClipboardList} title={list.length ? `No ${filter} requirements` : 'No requirements yet'}>
          {list.length ? 'Try another filter.' : 'Run the AI extraction above, or add requirements by hand.'}
        </Empty>
      )}

      <AnimatePresence>
        {selected.size > 0 && (
          <motion.div
            initial={{ y: 40, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ y: 40, opacity: 0 }}
            className="sticky bottom-6 z-20 mx-auto flex w-fit items-center gap-3 border border-border bg-surface px-4 py-3 shadow-2xl shadow-black/30"
          >
            <span className="text-sm">{selected.size} selected</span>
            <Button size="sm" icon={Merge} disabled={selected.size < 2} loading={merge.isPending} onClick={() => merge.mutate()}>Merge</Button>
            <Button variant="ghost" size="sm" onClick={() => setSelected(new Set())}>Clear</Button>
          </motion.div>
        )}
      </AnimatePresence>

      <p className="text-sm text-muted">{project.approved_requirements} approved — only approved requirements are analysed.</p>

      <AddRequirementModal projectId={projectId} open={adding} onClose={() => setAdding(false)} />
    </div>
  )
}
