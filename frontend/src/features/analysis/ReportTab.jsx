/**
 * Report — the analysis as a structured document (UI spec §22 "Read view"):
 * executive summary, coverage overview, changes since the previous run, gaps by type,
 * recommended actions. Downloadable as CSV (traceability matrix), Markdown or PDF.
 */
import { useState } from 'react'
import { ArrowDownRight, ArrowUpRight, ChevronDown, Download, FileText, Minus } from 'lucide-react'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { formatDateTime } from '@/lib/format'
import { useDiff, useReport } from '@/lib/queries'
import { cn } from '@/lib/utils'
import { Button, Empty, ErrorState, Eyebrow, Panel, Skeleton, StatusPill } from '@/components/kit'
import { CoverageBar, StatusCounts } from '@/features/analysis/summary'
import { AiText } from '@/features/analysis/EvidenceDrawer'

const SECTIONS = [
  ['missing', 'Missing areas'], ['conflict', 'Conflicts'], ['partial', 'Partial areas'],
  ['unclear', 'Needs a human decision'], ['covered', 'Covered'],
]

/** Export buttons (server-generated files). */
function Exports({ runId }) {
  const [busy, setBusy] = useState(null)
  const get = async (format) => {
    setBusy(format)
    try { await api.downloadExport(runId, format) } catch (err) { toast.error(err.message) } finally { setBusy(null) }
  }
  return (
    <div className="flex flex-wrap gap-2">
      {[['pdf', 'PDF'], ['md', 'Markdown'], ['csv', 'CSV matrix']].map(([f, label]) => (
        <Button key={f} variant="outline" size="sm" icon={Download} loading={busy === f} onClick={() => get(f)}>{label}</Button>
      ))}
    </div>
  )
}

/** "Changes since previous run" — per-requirement improvements and regressions. */
function Changes({ runId }) {
  const { data: diff } = useDiff(runId)
  if (!diff?.against_run_id) return null
  const moved = diff.changes.filter((c) => c.change !== 'unchanged')
  const icon = { improved: ArrowUpRight, regressed: ArrowDownRight, new: ArrowUpRight, removed: Minus }
  const tone = { improved: 'text-success', regressed: 'text-danger', new: 'text-secondary', removed: 'text-muted' }
  return (
    <Panel className="p-5">
      <Eyebrow>Changes since previous run</Eyebrow>
      <p className="mt-1 text-xs text-muted">Compared with the run from {formatDateTime(diff.against_finished_at)}</p>
      <p className="mt-3 text-sm">
        <span className="text-success">{diff.summary.improved} improved</span> ·{' '}
        <span className="text-danger">{diff.summary.regressed} regressed</span> · {diff.summary.unchanged} unchanged
        {diff.summary.new ? ` · ${diff.summary.new} new` : ''}{diff.summary.removed ? ` · ${diff.summary.removed} removed` : ''}
      </p>
      {moved.length > 0 && (
        <ul className="mt-3 space-y-1.5">
          {moved.map((c) => {
            const Icon = icon[c.change]
            return (
              <li key={c.code} className="flex flex-wrap items-center gap-2 text-sm">
                <Icon className={cn('size-4', tone[c.change])} />
                <span className="font-mono text-xs text-muted">{c.code}</span>
                <span className="min-w-0 flex-1 truncate">{c.requirement}</span>
                {c.before && <StatusPill status={c.before} />}{c.before && c.after && '→'}{c.after && <StatusPill status={c.after} />}
              </li>
            )
          })}
        </ul>
      )}
    </Panel>
  )
}

/** One gap section; Covered starts collapsed. */
function Section({ status, title, rows }) {
  const [open, setOpen] = useState(status !== 'covered')
  if (!rows.length) return null
  return (
    <section>
      <button type="button" onClick={() => setOpen((o) => !o)} className="flex w-full cursor-pointer items-center gap-2 border-b border-border pb-2 text-left">
        <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
        <span className="font-mono text-sm text-muted">{rows.length}</span>
        <ChevronDown className={cn('ml-auto size-4 transition-transform', open && 'rotate-180')} />
      </button>
      {open && (
        <ol className="mt-3 space-y-3">
          {rows.map((r) => (
            <li key={r.code} className="rounded-lg border border-border p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <p className="text-sm font-medium"><span className="mr-2 font-mono text-xs text-muted">{r.code}</span>{r.requirement}</p>
                <StatusPill status={status} />
              </div>
              <div className="mt-3 space-y-2">
                <AiText>{r.assessment}</AiText>
                {r.missing_or_different && <AiText label="Missing or different">{r.missing_or_different}</AiText>}
                {r.evidence.map((e, i) => (
                  <p key={i} className="border-l-2 border-secondary pl-3 text-sm">
                    <span className="font-serif italic">&ldquo;{e.quote}&rdquo;</span>
                    <span className="block text-xs text-muted">{e.source}{e.verified ? ' · verified' : ''}</span>
                  </p>
                ))}
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}

export default function ReportTab({ runId }) {
  const { data: report, isLoading, error, refetch } = useReport(runId)
  if (!runId) return <Empty icon={FileText} title="No report yet">Run the analysis to generate a report.</Empty>
  if (error) return <ErrorState error={error} onRetry={refetch} />
  if (isLoading || !report) return <Skeleton className="h-96" />

  return (
    <div className="space-y-6">
      <Panel className="p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <Eyebrow>Executive summary</Eyebrow>
            <p className="mt-2 max-w-3xl text-lg leading-snug">{report.summary.headline}</p>
          </div>
          <Exports runId={runId} />
        </div>
        <StatusCounts counts={report.summary.counts} all className="mt-5" />
        <CoverageBar counts={report.summary.counts} className="mt-3" />
        <p className="mt-4 text-xs text-muted">
          Documents: {report.documents.map((d) => `${d.name} (${d.role})`).join(' · ')}
        </p>
      </Panel>

      <Changes runId={runId} />

      {SECTIONS.map(([status, title]) => <Section key={status} status={status} title={title} rows={report.sections[status]} />)}

      {report.actions.length > 0 && (
        <section>
          <h2 className="border-b border-border pb-2 text-lg font-semibold tracking-tight">Recommended actions</h2>
          <ol className="mt-3 space-y-2">
            {report.actions.map((a) => (
              <li key={a.code} className="flex gap-3 text-sm">
                <span className="font-mono text-xs text-muted">{a.code}</span>
                <StatusPill status={a.status} />
                <span>{a.action}</span>
              </li>
            ))}
          </ol>
        </section>
      )}

      <p className="text-xs text-muted">Quotes are copied from the source documents and verified by code; assessments and actions are AI-generated.</p>
    </div>
  )
}
