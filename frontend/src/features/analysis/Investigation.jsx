/**
 * Investigator agent UI (Phase 10): start a re-check of one finding and show the agent's
 * trace — every tool call it made and what it concluded — so the result is auditable.
 */
import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Bot, CheckCircle2, CircleAlert, Loader2, Search, XCircle } from 'lucide-react'
import { api } from '@/lib/api'
import { keys, useAction, useTraces } from '@/lib/queries'
import { cn } from '@/lib/utils'
import { Button, Eyebrow, StatusPill } from '@/components/kit'

const OUTCOME = {
  changed: { label: 'Verdict changed', icon: CheckCircle2, tone: 'text-success', text: 'The agent found better evidence and updated this finding.' },
  confirmed: { label: 'Verdict confirmed', icon: CheckCircle2, tone: 'text-success', text: 'A deeper search reached the same conclusion.' },
  rejected: { label: 'Not applied', icon: XCircle, tone: 'text-warning', text: "The agent's evidence could not be verified in the documents, so the original finding was kept." },
  kept: { label: 'Kept original', icon: CircleAlert, tone: 'text-muted', text: 'The agent concluded "missing" or "unclear". An absence claim cannot be verified, so it may only change a finding when it brings verified evidence.' },
  no_verdict: { label: 'No verdict', icon: CircleAlert, tone: 'text-muted', text: 'The agent used its step budget without reaching a verdict.' },
  error: { label: 'Failed', icon: XCircle, tone: 'text-danger', text: 'The investigation failed.' },
}

const STEP_LABELS = { search_documents: 'Searched', get_chunk: 'Read passage', submit_verdict: 'Submitted verdict' }

/** Statuses the agent is most useful for (mirrors the backend's is_uncertain). */
export const isUncertain = (f) => ['missing', 'unclear', 'conflict'].includes(f.status) || (f.confidence != null && f.confidence < 0.6)

/** One trace: outcome, before → after, and the step list. */
function Trace({ trace }) {
  const busy = trace.status === 'queued' || trace.status === 'running'
  const outcome = OUTCOME[trace.outcome]
  return (
    <div className="rounded-lg border border-border p-4">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        {busy ? (
          <span className="inline-flex items-center gap-2 text-secondary"><Loader2 className="size-4 animate-spin" /> Investigating…</span>
        ) : outcome && (
          <span className={cn('inline-flex items-center gap-1.5 font-medium', outcome.tone)}><outcome.icon className="size-4" /> {outcome.label}</span>
        )}
        {trace.new_status && (
          <span className="flex items-center gap-1.5 text-xs text-muted">
            <StatusPill status={trace.previous_status} /> → <StatusPill status={trace.new_status} />
          </span>
        )}
      </div>
      {outcome && <p className="mt-2 text-xs text-muted">{outcome.text}</p>}
      {trace.explanation && !busy && <p className="mt-2 text-sm leading-relaxed">{trace.explanation}</p>}
      {trace.error && <p className="mt-2 text-xs text-danger">{trace.error}</p>}
      {trace.steps?.length > 0 && (
        <ol className="mt-3 space-y-1 border-l border-border pl-3 text-xs text-muted">
          {trace.steps.map((s, i) => (
            <li key={i} className={cn('flex gap-2', !s.ok && 'text-danger')}>
              <span className="font-mono">{i + 1}.</span>
              <span>
                <span className="text-foreground">{STEP_LABELS[s.tool] || s.tool}</span>
                {s.tool === 'search_documents' && s.arguments?.query && <> “{s.arguments.query}”</>}
                {' · '}{s.summary}
              </span>
            </li>
          ))}
        </ol>
      )}
      {!busy && trace.duration_s != null && (
        <p className="mt-3 font-mono text-[11px] text-muted">
          {trace.tool_calls} tool calls · {(trace.prompt_tokens || 0) + (trace.completion_tokens || 0)} tokens · {trace.duration_s}s
        </p>
      )}
    </div>
  )
}

/** Panel inside the evidence drawer. */
export function InvestigationPanel({ finding, projectId }) {
  const queryClient = useQueryClient()
  const { data: traces = [] } = useTraces(finding.id)
  const busy = traces.some((t) => t.status === 'queued' || t.status === 'running')
  const start = useAction(() => api.investigateFinding(finding.id), { invalidate: [keys.traces(finding.id)] })

  // When an investigation finishes, refresh the findings/runs so the card and counts update
  const wasBusy = useRef(busy)
  useEffect(() => {
    if (wasBusy.current && !busy) {
      [keys.findings(finding.run_id), keys.runs(projectId), keys.project(projectId)].forEach((k) => queryClient.invalidateQueries({ queryKey: k }))
    }
    wasBusy.current = busy
  }, [busy, finding.run_id, projectId, queryClient])
  useEffect(() => {   // inline (eager) jobs finish before the request returns — refresh then too
    if (start.isSuccess) [keys.findings(finding.run_id), keys.runs(projectId)].forEach((k) => queryClient.invalidateQueries({ queryKey: k }))
  }, [start.isSuccess]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <section className="space-y-3 border-t border-border pt-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Eyebrow>Investigator agent</Eyebrow>
          <p className="mt-1 text-sm text-muted">
            Re-checks this finding with several searches (synonyms, abbreviations, units) and reads passages in full.
            Its verdict is applied only if its quotes are verified in the documents.
          </p>
        </div>
        <Button size="sm" variant={isUncertain(finding) ? 'accent' : 'outline'} icon={busy ? undefined : Bot}
          loading={busy || start.isPending} onClick={() => start.mutate()}>
          {busy ? 'Investigating' : traces.length ? 'Re-check again' : 'Re-check with agent'}
        </Button>
      </div>
      {traces.map((t) => <Trace key={t.id} trace={t} />)}
      {!traces.length && !busy && (
        <p className="flex items-center gap-2 text-xs text-muted"><Search className="size-3.5" /> Not investigated yet.</p>
      )}
    </section>
  )
}

/** "Re-check uncertain findings" button for the Findings tab. */
export function InvestigateRunButton({ runId, projectId, findings }) {
  const queryClient = useQueryClient()
  const candidates = findings.filter((f) => isUncertain(f) && f.source !== 'agent').length
  const run = useAction(() => api.investigateRun(runId), {
    success: (r) => (r.queued ? `Re-checked ${r.queued} finding${r.queued === 1 ? '' : 's'}` : 'Nothing new to re-check'),
    onSuccess: () => [keys.findings(runId), keys.runs(projectId), keys.project(projectId)].forEach((k) => queryClient.invalidateQueries({ queryKey: k })),
  })
  if (!candidates) return null
  return (
    <Button variant="outline" size="sm" icon={Bot} loading={run.isPending} onClick={() => run.mutate()}
      title="Run the investigator agent on missing, unclear, conflict and low-confidence findings">
      Re-check uncertain ({candidates})
    </Button>
  )
}
