/**
 * Step 3 — run the gap analysis and review findings.
 * Every finding opens an evidence drawer: verified quotes with document, section and page.
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { AlertTriangle, BadgeCheck, Download, History, Play, Quote, ScanSearch, Search as SearchIcon } from 'lucide-react'
import { api } from '@/lib/api'
import { keys, useAction, useFindings, useRuns } from '@/lib/queries'
import { cn } from '@/lib/utils'
import {
  Button, Drawer, Empty, Eyebrow, FINDING_STATUSES, Input, Notice, Panel, Progress, STATUS_HELP, Skeleton, StatusPill, Tag,
} from '@/components/kit'

const formatDate = (iso) => new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })

/** Build and download a CSV traceability matrix from the visible findings. */
function exportCsv(findings, projectName) {
  const escape = (v) => `"${String(v ?? '').replaceAll('"', '""')}"`
  const rows = [['Code', 'Requirement', 'Section', 'Status', 'Confidence', 'Explanation', 'Missing', 'Suggested action', 'Evidence']]
  for (const f of findings) {
    rows.push([
      f.requirement.code, f.requirement.text, f.requirement.section, f.status, f.confidence, f.explanation,
      f.missing_detail, f.suggested_action,
      f.evidence.map((e) => `${e.document_filename}${e.page_start ? ` p.${e.page_start}` : ''}: "${e.quote}"`).join(' | '),
    ])
  }
  const blob = new Blob([rows.map((r) => r.map(escape).join(',')).join('\n')], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = Object.assign(document.createElement('a'), { href: url, download: `${projectName.replace(/\W+/g, '-')}-findings.csv` })
  a.click()
  URL.revokeObjectURL(url)
}

/** Stacked bar of finding statuses + clickable count tiles that act as filters. */
function CoverageSummary({ counts, total, filter, onFilter }) {
  const covered = counts.covered || 0
  return (
    <Panel className="p-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <Eyebrow>Coverage</Eyebrow>
          <p className="mt-2 text-4xl font-semibold tracking-tighter tabular-nums">
            {total ? Math.round((covered / total) * 100) : 0}<span className="text-2xl text-muted">%</span>
          </p>
          <p className="mt-1 text-sm text-muted">{covered} of {total} requirements fully covered</p>
        </div>
      </div>
      <div className="mt-5 flex h-2.5 w-full overflow-hidden bg-fill-strong">
        {FINDING_STATUSES.map((s) => counts[s] ? (
          <motion.div
            key={s} className="h-full" style={{ backgroundColor: `var(--${s})` }}
            initial={{ width: 0 }} animate={{ width: `${(counts[s] / total) * 100}%` }} transition={{ duration: 0.7 }}
          />
        ) : null)}
      </div>
      <div className="mt-5 grid grid-cols-2 gap-px border border-border bg-border sm:grid-cols-5">
        {FINDING_STATUSES.map((s) => (
          <button
            key={s} type="button" title={STATUS_HELP[s]}
            onClick={() => onFilter(filter === s ? null : s)}
            className={cn('cursor-pointer bg-background p-3 text-left transition-colors hover:bg-surface', filter === s && 'bg-surface ring-1 ring-inset ring-secondary')}
          >
            <p className="font-mono text-2xl tabular-nums" style={{ color: `var(--${s})` }}>{counts[s] || 0}</p>
            <p className="mt-0.5 text-[11px] tracking-wider text-muted uppercase">{s}</p>
          </button>
        ))}
      </div>
    </Panel>
  )
}

/** Evidence drawer: verdict, explanation, gaps, and verified quotes from the source documents. */
function FindingDrawer({ finding, onClose }) {
  return (
    <Drawer open={Boolean(finding)} onClose={onClose} eyebrow={finding?.requirement.code} title="Finding">
      {finding && (
        <div className="space-y-6">
          <div>
            <p className="text-base leading-relaxed">{finding.requirement.text}</p>
            {finding.requirement.section && <Tag className="mt-2">{finding.requirement.section}</Tag>}
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <StatusPill status={finding.status} />
            {finding.confidence != null && (
              <span className="flex items-center gap-2 text-xs text-muted">
                confidence
                <Progress value={finding.confidence * 100} className="w-20" />
                <span className="font-mono">{Math.round(finding.confidence * 100)}%</span>
              </span>
            )}
            {finding.source === 'cache' && <Tag>from cache</Tag>}
          </div>
          <p className="text-sm text-muted">{STATUS_HELP[finding.status]}</p>

          <section>
            <Eyebrow>Why</Eyebrow>
            <p className="mt-2 text-sm leading-relaxed">{finding.explanation}</p>
          </section>
          {finding.missing_detail && (
            <section>
              <Eyebrow>What&apos;s missing</Eyebrow>
              <p className="mt-2 text-sm leading-relaxed">{finding.missing_detail}</p>
            </section>
          )}
          {finding.suggested_action && (
            <section className="border-l-2 border-secondary pl-4">
              <Eyebrow>Suggested action</Eyebrow>
              <p className="mt-2 text-sm leading-relaxed">{finding.suggested_action}</p>
            </section>
          )}

          <section>
            <Eyebrow>Evidence ({finding.evidence.length})</Eyebrow>
            {finding.evidence.length ? (
              <ul className="mt-3 space-y-3">
                {finding.evidence.map((e) => (
                  <li key={e.id} className="border border-border p-4">
                    <Quote className="size-4 text-secondary" />
                    <blockquote className="mt-2 font-serif text-lg leading-snug italic">&ldquo;{e.quote}&rdquo;</blockquote>
                    <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted">
                      <span className="font-medium text-foreground">{e.document_filename}</span>
                      {e.section && <Tag>{e.section}</Tag>}
                      {e.page_start && <Tag>p.{e.page_start}</Tag>}
                      {e.verified && (
                        <span className="inline-flex items-center gap-1 text-success" title="This exact text was found in the source document">
                          <BadgeCheck className="size-3.5" /> verified in source
                        </span>
                      )}
                      {e.score != null && <span className="font-mono">sim {e.score.toFixed(2)}</span>}
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-sm text-muted">
                {finding.status === 'missing' ? 'No passage in the existing documents addresses this requirement.' : 'No verifiable quote was found.'}
              </p>
            )}
          </section>
        </div>
      )}
    </Drawer>
  )
}

/** Findings list with text search; rows open the evidence drawer. */
function FindingsList({ findings, onOpen }) {
  if (!findings.length) return <Empty icon={SearchIcon} title="Nothing matches">Clear the filter or search.</Empty>
  return (
    <Panel>
      <ul>
        {findings.map((f) => (
          <li key={f.id}>
            <button
              type="button" onClick={() => onOpen(f)}
              className="grid w-full cursor-pointer grid-cols-[4.5rem_1fr_auto] items-center gap-3 border-b border-border px-4 py-3 text-left transition-colors last:border-b-0 hover:bg-fill"
            >
              <span className="font-mono text-xs text-muted">{f.requirement.code}</span>
              <span className="min-w-0">
                <span className="block truncate text-sm">{f.requirement.text}</span>
                <span className="mt-0.5 block truncate text-xs text-muted">{f.explanation}</span>
              </span>
              <span className="flex items-center gap-3">
                <span className="hidden font-mono text-[11px] text-muted sm:inline">{f.evidence.length} quote{f.evidence.length === 1 ? '' : 's'}</span>
                <StatusPill status={f.status} />
              </span>
            </button>
          </li>
        ))}
      </ul>
    </Panel>
  )
}

export default function AnalysisStep({ project }) {
  const projectId = project.id
  const { data: runs = [], isLoading } = useRuns(projectId)
  const [selectedRunId, setSelectedRunId] = useState(null)
  const [filter, setFilter] = useState(null)
  const [query, setQuery] = useState('')
  const [open, setOpen] = useState(null)
  const queryClient = useQueryClient()

  const run = runs.find((r) => r.id === selectedRunId) || runs[0]
  const active = run && (run.status === 'queued' || run.status === 'running')
  const { data: findings = [], isLoading: loadingFindings } = useFindings(run?.id, run?.status === 'completed')

  const analyze = useAction(() => api.analyze(projectId), {
    invalidate: [keys.runs(projectId), keys.project(projectId)],
    onSuccess: (r) => setSelectedRunId(r.id),
  })

  // When a run finishes, refresh the project counters (latest run status, etc.)
  const wasActive = useRef(active)
  useEffect(() => {
    if (wasActive.current && !active) queryClient.invalidateQueries({ queryKey: keys.project(projectId) })
    wasActive.current = active
  }, [active, projectId, queryClient])

  const counts = useMemo(() => FINDING_STATUSES.reduce((a, s) => ({ ...a, [s]: findings.filter((f) => f.status === s).length }), {}), [findings])
  const visible = findings.filter((f) =>
    (!filter || f.status === filter) &&
    (!query || `${f.requirement.code} ${f.requirement.text} ${f.explanation}`.toLowerCase().includes(query.toLowerCase())))

  if (isLoading) return <Skeleton className="h-72" />

  return (
    <div className="space-y-5">
      <Panel className="flex flex-wrap items-center justify-between gap-4 p-5">
        <div>
          <p className="font-semibold">Run gap analysis</p>
          <p className="mt-1 text-sm text-muted">
            {project.approved_requirements} approved requirements will be matched against the existing documents.
            Unchanged requirements are reused from cache.
          </p>
        </div>
        <Button size="lg" variant="accent" icon={Play} loading={active || analyze.isPending}
          disabled={!project.approved_requirements} onClick={() => analyze.mutate()}
        >
          {active ? 'Analysing…' : runs.length ? 'Re-run analysis' : 'Run analysis'}
        </Button>
        {active && (
          <div className="w-full">
            <div className="mb-2 flex justify-between text-xs text-muted">
              <span>{run.status === 'queued' ? 'Queued…' : 'Matching evidence and classifying…'}</span>
              <span className="font-mono">{run.processed} / {run.total}</span>
            </div>
            <Progress value={run.total ? (run.processed / run.total) * 100 : 5} />
          </div>
        )}
        {run?.status === 'failed' && <Notice icon={AlertTriangle} className="w-full">{run.error_message}</Notice>}
      </Panel>

      {runs.length > 1 && (
        <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
          <History className="size-3.5" /> Runs:
          {runs.map((r, i) => (
            <button key={r.id} type="button" onClick={() => setSelectedRunId(r.id)}
              className={cn('cursor-pointer border px-2 py-1 font-mono', r.id === run?.id ? 'border-secondary text-foreground' : 'border-border hover:text-foreground')}
            >
              #{runs.length - i} · {formatDate(r.created_at)} · {r.status}
            </button>
          ))}
        </div>
      )}

      {!run ? (
        <Empty icon={ScanSearch} title="No analysis yet">Run the analysis to see which requirements are covered, partial, missing or contradicted.</Empty>
      ) : run.status === 'completed' && (
        loadingFindings ? <Skeleton className="h-72" /> : (
          <>
            <CoverageSummary counts={counts} total={findings.length} filter={filter} onFilter={setFilter} />
            {run.stats && (
              <p className="font-mono text-[11px] text-muted">
                {run.model} · {run.prompt_version} · {run.stats.llm_calls} LLM calls · {run.stats.cache_hits} cached ·{' '}
                {(run.stats.prompt_tokens || 0) + (run.stats.completion_tokens || 0)} tokens · {run.stats.duration_s}s
              </p>
            )}
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="relative w-full max-w-sm">
                <SearchIcon className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted" />
                <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search findings…" className="pl-9" />
              </div>
              <div className="flex items-center gap-2">
                {filter && <Button variant="ghost" size="sm" onClick={() => setFilter(null)}>Clear filter: {filter}</Button>}
                <Button variant="outline" size="sm" icon={Download} onClick={() => exportCsv(visible, project.name)}>Export CSV</Button>
              </div>
            </div>
            <FindingsList findings={visible} onOpen={setOpen} />
          </>
        )
      )}

      <FindingDrawer finding={open} onClose={() => setOpen(null)} />
    </div>
  )
}
