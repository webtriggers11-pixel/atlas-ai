/**
 * Retrieval inspector — run the same search the analysis uses and see what it finds.
 * Useful to understand a surprising finding ("why was this marked missing?").
 */
import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Search } from 'lucide-react'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import { Button, Empty, Input, Notice, Panel, Progress, Tag } from '@/components/kit'

const ROLES = [
  { value: 'existing', label: 'Existing docs' },
  { value: 'reference', label: 'Reference docs' },
  { value: '', label: 'Both' },
]
const MODES = [
  { value: 'vector', label: 'Vector', help: 'Meaning-based (embeddings). The default used by the analysis.' },
  { value: 'hybrid', label: 'Hybrid', help: 'Vector + keyword search fused with Reciprocal Rank Fusion.' },
]

/** Segmented control. */
function Segmented({ options, value, onChange }) {
  return (
    <div className="flex gap-px border border-border bg-border">
      {options.map((o) => (
        <button key={o.label} type="button" title={o.help} onClick={() => onChange(o.value)}
          className={cn('cursor-pointer px-3 py-2 text-xs transition-colors', value === o.value ? 'bg-surface font-semibold' : 'bg-background text-muted hover:text-foreground')}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

export default function SearchStep({ project }) {
  const [query, setQuery] = useState('')
  const [role, setRole] = useState('existing')
  const [mode, setMode] = useState('vector')
  const search = useMutation({ mutationFn: () => api.search(project.id, query.trim(), role, mode) })

  return (
    <div className="space-y-5">
      <Panel className="space-y-4 p-5">
        <div>
          <p className="font-semibold">Retrieval inspector</p>
          <p className="mt-1 text-sm text-muted">Search the processed documents the way the analysis does. Scores are cosine similarity (higher = closer in meaning).</p>
        </div>
        <form className="flex flex-wrap gap-3" onSubmit={(e) => { e.preventDefault(); if (query.trim()) search.mutate() }}>
          <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="e.g. how long do access tokens last?" className="min-w-64 flex-1" />
          <Button type="submit" icon={Search} disabled={!query.trim()} loading={search.isPending}>Search</Button>
        </form>
        <div className="flex flex-wrap gap-3">
          <Segmented options={ROLES} value={role} onChange={setRole} />
          <Segmented options={MODES} value={mode} onChange={setMode} />
        </div>
      </Panel>

      {search.error && <Notice>{search.error.message}</Notice>}
      {search.data && (search.data.length ? (
        <ol className="space-y-3">
          {search.data.map((r) => (
            <li key={r.chunk_id}>
              <Panel className="p-4">
                <div className="mb-2 flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs text-muted">#{r.rank}</span>
                  <span className="text-sm font-medium">{r.document_filename}</span>
                  <Tag>{r.document_role}</Tag>
                  {r.section && <Tag>{r.section}</Tag>}
                  {r.page_start && <Tag>p.{r.page_start}</Tag>}
                  <span className="ml-auto flex items-center gap-2 font-mono text-xs text-muted">
                    <Progress value={Math.max(0, r.score) * 100} className="w-20" /> {r.score.toFixed(3)}
                  </span>
                </div>
                <p className="text-sm leading-relaxed text-foreground/90">{r.content}</p>
              </Panel>
            </li>
          ))}
        </ol>
      ) : <Empty icon={Search} title="No results">Are the documents processed?</Empty>)}
    </div>
  )
}
