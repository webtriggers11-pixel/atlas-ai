/**
 * Real processing stages derived from backend state (UI spec §10): no fake percentages —
 * each stage is done / active / waiting / failed based on what the API reports, and the only
 * number shown is the real "requirements analysed so far / total" while a run is active.
 */
import { AlertTriangle, Check, Circle, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Panel } from '@/components/kit'

/** Compute the stage list from project/document/requirement/run state. */
export function computeStages({ project, documents, requirements, run }) {
  const has = (role) => documents.some((d) => d.role === role)
  const busyDocs = documents.filter((d) => d.status === 'uploaded' || d.status === 'processing')
  const failedDocs = documents.filter((d) => d.status === 'failed')
  const drafts = requirements.filter((r) => r.status === 'draft').length
  const approved = requirements.filter((r) => r.status === 'approved').length
  const runActive = run && (run.status === 'queued' || run.status === 'running')

  return [
    {
      id: 'upload', label: 'Upload documents',
      state: has('reference') && has('existing') ? 'done' : 'active',
      detail: has('reference') && has('existing') ? `${documents.length} documents` : 'Add reference and existing documents',
    },
    {
      id: 'text', label: 'Extract text and document structure',
      state: !documents.length ? 'waiting' : busyDocs.length ? 'active' : failedDocs.length ? 'failed' : 'done',
      detail: busyDocs.length ? `${busyDocs.length} processing`
        : failedDocs.length ? `${documents.length - failedDocs.length} of ${documents.length} processed — ${failedDocs.map((d) => d.filename).join(', ')} failed`
        : documents.length ? 'All documents processed' : '',
    },
    {
      id: 'extract', label: 'Extract requirements',
      state: project.extraction_status === 'running' ? 'active' : project.extraction_status === 'failed' ? 'failed'
        : requirements.length || project.extraction_status === 'completed' ? 'done' : 'waiting',
      detail: project.extraction_status === 'failed' ? project.extraction_error
        : requirements.length ? `${requirements.length} requirements` : '',
    },
    {
      id: 'review', label: 'Review requirements',
      state: !requirements.length ? 'waiting' : drafts ? 'active' : approved ? 'done' : 'waiting',
      detail: requirements.length ? `${approved} approved${drafts ? ` · ${drafts} waiting for review` : ''}` : '',
    },
    {
      id: 'analyse', label: 'Find evidence and generate findings',
      state: runActive ? 'active' : run?.status === 'failed' ? 'failed' : run?.status === 'completed' ? 'done' : 'waiting',
      detail: runActive ? `${run.processed} of ${run.total} requirements analysed`
        : run?.status === 'failed' ? run.error_message
        : run?.status === 'completed' ? `${run.total} findings` : '',
    },
  ]
}

const ICONS = {
  done: <Check className="size-3.5 text-success" />,
  active: <Loader2 className="size-3.5 animate-spin text-secondary" />,
  failed: <AlertTriangle className="size-3.5 text-danger" />,
  waiting: <Circle className="size-3 text-muted" />,
}

/** Vertical list of stages with an optional call-to-action for the current one. */
export function ProcessingStages({ stages, actions }) {
  return (
    <Panel className="p-5">
      <p className="font-semibold">Analysis progress</p>
      <ol className="mt-4 space-y-3">
        {stages.map((s) => (
          <li key={s.id} className="flex items-start gap-3">
            <span className={cn('mt-0.5 grid size-5 shrink-0 place-items-center border',
              s.state === 'done' ? 'border-success/40' : s.state === 'active' ? 'border-secondary' : s.state === 'failed' ? 'border-danger/50' : 'border-border')}
            >
              {ICONS[s.state]}
            </span>
            <div className="min-w-0 flex-1">
              <p className={cn('text-sm', s.state === 'waiting' ? 'text-muted' : 'text-foreground', s.state === 'active' && 'font-medium')}>{s.label}</p>
              {s.detail && <p className={cn('mt-0.5 text-xs', s.state === 'failed' ? 'text-danger' : 'text-muted')}>{s.detail}</p>}
              {actions?.[s.id] && s.state !== 'done' && <div className="mt-2 flex flex-wrap gap-2">{actions[s.id]}</div>}
            </div>
          </li>
        ))}
      </ol>
    </Panel>
  )
}
