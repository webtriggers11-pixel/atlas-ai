/** Status counts shown on dashboard cards and the analysis header. */
import { Link } from 'react-router-dom'
import { analysisType } from '@/lib/analysisTypes'
import { timeAgo } from '@/lib/format'
import { cn } from '@/lib/utils'
import { FINDING_STATUSES, Panel, STATUS_ICONS, Tag } from '@/components/kit'

/** "18 Covered · 4 Partial · 3 Missing" — icon + number + label per status (only non-zero unless `all`). */
export function StatusCounts({ counts, all = false, onSelect, selected, className }) {
  const shown = FINDING_STATUSES.filter((s) => all || counts?.[s])
  return (
    <div className={cn('flex flex-wrap gap-x-4 gap-y-1.5', className)}>
      {shown.map((s) => {
        const Icon = STATUS_ICONS[s]
        const content = (
          <>
            <Icon className="size-3.5" style={{ color: `var(--${s})` }} aria-hidden />
            <span className="font-mono tabular-nums">{counts?.[s] || 0}</span>
            <span className="text-muted capitalize">{s}</span>
          </>
        )
        return onSelect ? (
          <button
            key={s} type="button" onClick={() => onSelect(selected === s ? null : s)}
            className={cn('inline-flex cursor-pointer items-center gap-1.5 border-b-2 pb-0.5 text-sm', selected === s ? 'border-secondary' : 'border-transparent hover:border-border')}
          >{content}</button>
        ) : <span key={s} className="inline-flex items-center gap-1.5 text-sm">{content}</span>
      })}
    </div>
  )
}

/** Thin stacked bar of finding statuses. */
export function CoverageBar({ counts, className }) {
  const total = FINDING_STATUSES.reduce((n, s) => n + (counts?.[s] || 0), 0)
  if (!total) return null
  return (
    <div className={cn('flex h-1.5 w-full overflow-hidden bg-fill-strong', className)} aria-hidden>
      {FINDING_STATUSES.map((s) => counts?.[s] ? (
        <div key={s} className="h-full" style={{ width: `${(counts[s] / total) * 100}%`, backgroundColor: `var(--${s})` }} />
      ) : null)}
    </div>
  )
}

/** Dashboard card for one analysis. */
export function AnalysisCard({ analysis }) {
  const type = analysisType(analysis.preset)
  const counts = analysis.finding_counts
  return (
    <Panel className="relative flex h-full flex-col p-5 transition-colors hover:border-foreground/30">
      <div className="flex items-center justify-between gap-2">
        <Tag>{type.short}</Tag>
        {analysis.latest_run_status === 'running' || analysis.latest_run_status === 'queued'
          ? <span className="font-mono text-[10px] tracking-wider text-warning uppercase">analysing…</span>
          : null}
      </div>
      <Link to={`/analyses/${analysis.id}`} className="mt-3 text-base leading-snug font-semibold tracking-tight after:absolute after:inset-0">
        {analysis.name}
      </Link>
      <div className="mt-4 flex-1">
        {counts ? (
          <>
            <StatusCounts counts={counts} className="text-sm" />
            <CoverageBar counts={counts} className="mt-3" />
          </>
        ) : (
          <p className="text-sm text-muted">
            {analysis.reference_documents + analysis.existing_documents === 0
              ? 'No documents yet'
              : analysis.requirements ? `${analysis.approved_requirements} of ${analysis.requirements} requirements approved` : 'Documents added — not analysed yet'}
          </p>
        )}
      </div>
      <p className="mt-4 border-t border-border pt-3 text-xs text-muted">
        {analysis.last_analyzed_at ? `Analysed ${timeAgo(analysis.last_analyzed_at)}` : `Updated ${timeAgo(analysis.updated_at)}`}
      </p>
    </Panel>
  )
}
