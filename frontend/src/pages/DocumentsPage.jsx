/** Global Documents page (UI spec §19): every document across analyses. */
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { FileText, Files, Plus, Search } from 'lucide-react'
import { formatSize, timeAgo } from '@/lib/format'
import { useAllDocuments } from '@/lib/queries'
import { Button, Empty, ErrorState, Input, Notice, Panel, Skeleton, StatusPill, Tag } from '@/components/kit'
import { PageBody, PageHeader } from '@/components/layout'
import { DOC_STATUS_LABEL } from '@/features/documents'

export default function DocumentsPage() {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [debounced, setDebounced] = useState('')
  useEffect(() => {
    const t = setTimeout(() => setDebounced(query.trim()), 250)   // search on the server, not on every keystroke
    return () => clearTimeout(t)
  }, [query])
  const { data: documents, isLoading, error, refetch } = useAllDocuments(debounced)

  return (
    <>
      <PageHeader title="Documents" description="Every document across your analyses. Documents are uploaded inside an analysis." />
      <PageBody className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="relative w-full max-w-sm">
            <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted" />
            <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search documents…" className="pl-9" />
          </div>
          <Button variant="outline" icon={Plus} onClick={() => navigate('/analyses/new')}>Upload in a new analysis</Button>
        </div>

        {error ? <ErrorState error={error} onRetry={refetch} />
          : isLoading ? <Skeleton className="h-64" />
          : documents.length ? (
            <Panel>
              <ul>
                {documents.map((d) => (
                  <li key={d.id} className="grid grid-cols-1 items-center gap-2 border-b border-border px-4 py-3 last:border-b-0 sm:grid-cols-[1fr_auto]">
                    <div className="flex min-w-0 items-start gap-3">
                      <FileText className="mt-0.5 size-4 shrink-0 text-muted" />
                      <div className="min-w-0">
                        <Link to={`/analyses/${d.project_id}?tab=documents&doc=${d.id}`} className="block truncate text-sm font-medium hover:underline">{d.filename}</Link>
                        <p className="mt-0.5 text-xs text-muted">
                          {d.file_type.toUpperCase()} · {formatSize(d.size_bytes)} · added {timeAgo(d.created_at)} · used in{' '}
                          <Link to={`/analyses/${d.project_id}`} className="text-foreground hover:underline">{d.project_name}</Link>
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Tag>{d.role}</Tag>
                      <StatusPill status={d.status}>{DOC_STATUS_LABEL[d.status]}</StatusPill>
                    </div>
                  </li>
                ))}
              </ul>
            </Panel>
          ) : (
            <Empty icon={Files} title={debounced ? 'No documents match your search.' : 'No documents yet.'}
              action={!debounced && <Button icon={Plus} onClick={() => navigate('/analyses/new')}>Create an analysis</Button>} />
          )}
        {documents?.some((d) => d.status === 'failed') && (
          <Notice tone="warning">Some documents failed to process — open their analysis to retry.</Notice>
        )}
      </PageBody>
    </>
  )
}
