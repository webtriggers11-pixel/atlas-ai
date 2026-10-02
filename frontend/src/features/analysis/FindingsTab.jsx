/**
 * Findings — the core screen (UI spec §12–16). Each card is readable on its own:
 * covered/partial show the matched source text, missing says "no supporting evidence found",
 * conflict shows the reference source next to the existing source.
 */
import { useMemo, useState } from 'react'
import { Download, Search, ScanSearch } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button, Empty, FINDING_STATUSES, Input, Panel, StatusPill, Tag } from '@/components/kit'
import { AiText, SourceQuote, sourceLabel } from '@/features/analysis/EvidenceDrawer'

/** Build and download a CSV traceability matrix of the given findings. */
function exportCsv(findings, name) {
  const escape = (v) => `"${String(v ?? '').replaceAll('"', '""')}"`
  const rows = [['Code', 'Requirement', 'Section', 'Status', 'Confidence', 'AI assessment', 'Missing / different', 'Suggested action', 'Evidence']]
  for (const f of findings) {
    rows.push([f.requirement.code, f.requirement.text, f.requirement.section, f.status, f.confidence, f.explanation,
      f.missing_detail, f.suggested_action, f.evidence.map((e) => `${sourceLabel(e)}: "${e.quote}"`).join(' | ')])
  }
  const url = URL.createObjectURL(new Blob([rows.map((r) => r.map(escape).join(',')).join('\n')], { type: 'text/csv;charset=utf-8' }))
  Object.assign(document.createElement('a'), { href: url, download: `${name.replace(/\W+/g, '-')}-findings.csv` }).click()
  URL.revokeObjectURL(url)
}

/** One finding, readable without opening the drawer. */
function FindingCard({ finding, onView }) {
  const first = finding.evidence[0]
  return (
    <Panel className="p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-xs text-muted">{finding.requirement.code}</span>
          {finding.requirement.section && <Tag>{finding.requirement.section}</Tag>}
        </div>
        <StatusPill status={finding.status} />
      </div>

      <p className="mt-3 text-[11px] font-medium tracking-wider text-muted uppercase">Requirement</p>
      <p className="mt-1 text-sm leading-relaxed">{finding.requirement.text}</p>

      <div className="mt-4 space-y-3">
        {finding.status === 'missing' && (
          <>
            <p className="text-sm text-muted">No supporting evidence was found in the provided existing documents.</p>
            {finding.suggested_action && <AiText label="Suggested action">{finding.suggested_action}</AiText>}
          </>
        )}

        {finding.status === 'conflict' && (
          <>
            <div className="grid gap-2 text-xs sm:grid-cols-2">
              <div className="border border-border px-3 py-2">
                <p className="text-muted">Reference source</p>
                <p className="mt-0.5 font-medium">{finding.requirement.source_document || 'Reference documents'}{finding.requirement.source_page ? ` · p.${finding.requirement.source_page}` : ''}</p>
              </div>
              <div className="border border-conflict/40 px-3 py-2">
                <p className="text-muted">Existing source</p>
                <p className="mt-0.5 font-medium">{first ? sourceLabel(first) : '—'}</p>
              </div>
            </div>
            {first && <SourceQuote evidence={first} compact />}
            <AiText>{finding.explanation}</AiText>
          </>
        )}

        {(finding.status === 'covered' || finding.status === 'partial') && (
          <>
            {first && <SourceQuote evidence={first} compact />}
            {finding.status === 'partial' && finding.missing_detail && <AiText label="Missing area">{finding.missing_detail}</AiText>}
          </>
        )}

        {finding.status === 'unclear' && <AiText>{finding.explanation}</AiText>}
      </div>

      <div className="mt-4 flex justify-end">
        <Button variant="outline" size="sm" onClick={() => onView(finding)}>
          {finding.status === 'conflict' ? 'Compare evidence' : finding.status === 'missing' ? 'View details' : 'View evidence'}
        </Button>
      </div>
    </Panel>
  )
}

export default function FindingsTab({ findings, filter, onFilter, onView, analysisName }) {
  const [query, setQuery] = useState('')
  const counts = useMemo(() => FINDING_STATUSES.reduce((a, s) => ({ ...a, [s]: findings.filter((f) => f.status === s).length }), {}), [findings])
  const visible = findings.filter((f) =>
    (!filter || f.status === filter) &&
    (!query || `${f.requirement.code} ${f.requirement.text} ${f.explanation} ${f.requirement.section || ''}`.toLowerCase().includes(query.toLowerCase())))

  if (!findings.length) {
    return <Empty icon={ScanSearch} title="No findings yet">Run the analysis to see what is covered, partial, missing, conflicting or unclear.</Empty>
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-px border border-border bg-border" role="group" aria-label="Filter by status">
          {[null, ...FINDING_STATUSES].map((s) => (
            <button key={s || 'all'} type="button" onClick={() => onFilter(s)} aria-pressed={filter === s}
              className={cn('cursor-pointer px-3 py-1.5 text-xs capitalize transition-colors', filter === s ? 'bg-surface font-semibold' : 'bg-background text-muted hover:text-foreground')}
            >
              {s || 'all'} <span className="font-mono text-muted">{s ? counts[s] : findings.length}</span>
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative w-56">
            <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted" />
            <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search findings…" className="h-9 pl-9" />
          </div>
          <Button variant="outline" size="sm" icon={Download} onClick={() => exportCsv(visible, analysisName)}>Export CSV</Button>
        </div>
      </div>
      {visible.length
        ? <div className="grid gap-3 xl:grid-cols-2">{visible.map((f) => <FindingCard key={f.id} finding={f} onView={onView} />)}</div>
        : <Empty icon={Search} title="No findings match">Clear the filter or search.</Empty>}
    </div>
  )
}
