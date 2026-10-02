/**
 * Evidence — every verified quote, grouped by the document it came from, each linked to its
 * finding. Below it, a document search that runs the same retrieval the analysis uses.
 */
import { useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { ChevronDown, FileText, Quote, Search } from 'lucide-react'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import { Button, Empty, Input, Notice, Panel, Progress, StatusPill, Tag } from '@/components/kit'

/** Retrieval inspector: search the processed documents like the analysis does. */
function DocumentSearch({ projectId }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [role, setRole] = useState('existing')
  const search = useMutation({ mutationFn: () => api.search(projectId, query.trim(), role, null) })

  return (
    <Panel>
      <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open}
        className="flex w-full cursor-pointer items-center justify-between gap-3 p-5 text-left">
        <span>
          <span className="block font-semibold">Search the documents</span>
          <span className="mt-0.5 block text-sm text-muted">See what the retrieval step finds for any question — useful when a finding is surprising.</span>
        </span>
        <ChevronDown className={cn('size-4 shrink-0 transition-transform', open && 'rotate-180')} />
      </button>
      {open && (
        <div className="space-y-4 border-t border-border p-5">
          <form className="flex flex-wrap gap-2" onSubmit={(e) => { e.preventDefault(); if (query.trim()) search.mutate() }}>
            <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="e.g. how long do access tokens last?" className="min-w-56 flex-1" />
            <select value={role} onChange={(e) => setRole(e.target.value)} className="h-10 border border-border bg-background px-2 text-sm">
              <option value="existing">Existing documents</option>
              <option value="reference">Reference documents</option>
              <option value="">Both</option>
            </select>
            <Button type="submit" icon={Search} disabled={!query.trim()} loading={search.isPending}>Search</Button>
          </form>
          {search.error && <Notice>{search.error.message}</Notice>}
          {search.data && (search.data.length ? (
            <ol className="space-y-2">
              {search.data.map((r) => (
                <li key={r.chunk_id} className="border border-border p-3">
                  <div className="mb-1.5 flex flex-wrap items-center gap-2 text-xs text-muted">
                    <span className="font-mono">#{r.rank}</span>
                    <span className="font-medium text-foreground">{r.document_filename}</span>
                    {r.section && <Tag>{r.section}</Tag>}
                    {r.page_start && <Tag>p.{r.page_start}</Tag>}
                    <span className="ml-auto flex items-center gap-2 font-mono"><Progress value={Math.max(0, r.score) * 100} className="w-16" />{r.score.toFixed(2)}</span>
                  </div>
                  <p className="text-sm leading-relaxed text-foreground/90">{r.content}</p>
                </li>
              ))}
            </ol>
          ) : <p className="text-sm text-muted">No results.</p>)}
        </div>
      )}
    </Panel>
  )
}

export default function EvidenceTab({ findings, projectId, onView }) {
  const groups = useMemo(() => {
    const byDoc = new Map()
    for (const f of findings) {
      for (const e of f.evidence) {
        const group = byDoc.get(e.document_id) || { filename: e.document_filename, role: e.document_role, items: [] }
        group.items.push({ evidence: e, finding: f })
        byDoc.set(e.document_id, group)
      }
    }
    return [...byDoc.values()]
  }, [findings])

  return (
    <div className="space-y-5">
      {groups.length ? groups.map((g) => (
        <Panel key={g.filename}>
          <div className="flex items-center gap-2 border-b border-border px-5 py-3">
            <FileText className="size-4 text-muted" />
            <span className="font-medium">{g.filename}</span>
            <Tag>{g.role}</Tag>
            <span className="ml-auto text-xs text-muted">{g.items.length} cited passage{g.items.length === 1 ? '' : 's'}</span>
          </div>
          <ul>
            {g.items.map(({ evidence, finding }) => (
              <li key={evidence.id}>
                <button type="button" onClick={() => onView(finding)}
                  className="grid w-full cursor-pointer grid-cols-[1fr_auto] items-start gap-3 border-b border-border px-5 py-3 text-left last:border-b-0 hover:bg-fill">
                  <span className="min-w-0">
                    <span className="flex items-start gap-2">
                      <Quote className="mt-1 size-3 shrink-0 text-secondary" />
                      <span className="font-serif text-base leading-snug italic">{evidence.quote}</span>
                    </span>
                    <span className="mt-1 block truncate pl-5 text-xs text-muted">
                      {finding.requirement.code} · {finding.requirement.text}
                      {evidence.section ? ` · ${evidence.section}` : ''}{evidence.page_start ? ` · p.${evidence.page_start}` : ''}
                    </span>
                  </span>
                  <StatusPill status={finding.status} />
                </button>
              </li>
            ))}
          </ul>
        </Panel>
      )) : (
        <Empty icon={Quote} title="No cited evidence yet">Verified quotes appear here after an analysis run.</Empty>
      )}
      <DocumentSearch projectId={projectId} />
    </div>
  )
}
