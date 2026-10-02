/** All analyses as a searchable list. */
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { FolderOpen, Plus, Search, Trash2 } from 'lucide-react'
import { api } from '@/lib/api'
import { analysisType } from '@/lib/analysisTypes'
import { timeAgo } from '@/lib/format'
import { keys, useAction, useProjects } from '@/lib/queries'
import { Button, Empty, ErrorState, Input, Panel, Skeleton, Tag } from '@/components/kit'
import { PageBody, PageHeader } from '@/components/layout'
import { StatusCounts } from '@/features/analysis/summary'

/** One analysis row with a delete action. */
function AnalysisRow({ analysis }) {
  const remove = useAction(() => api.deleteProject(analysis.id), { invalidate: [keys.projects], success: 'Analysis deleted' })
  return (
    <li className="grid grid-cols-1 items-center gap-3 border-b border-border px-4 py-4 last:border-b-0 sm:grid-cols-[1fr_auto_auto]">
      <div className="min-w-0">
        <Link to={`/analyses/${analysis.id}`} className="font-medium hover:underline">{analysis.name}</Link>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-muted">
          <Tag>{analysisType(analysis.preset).short}</Tag>
          <span>{analysis.reference_documents} reference · {analysis.existing_documents} existing</span>
          <span>· {analysis.approved_requirements} requirements</span>
          <span>· {analysis.last_analyzed_at ? `analysed ${timeAgo(analysis.last_analyzed_at)}` : 'not analysed yet'}</span>
        </div>
      </div>
      <div>{analysis.finding_counts ? <StatusCounts counts={analysis.finding_counts} /> : <span className="text-xs text-muted">—</span>}</div>
      <Button
        variant="ghost" size="icon" aria-label={`Delete ${analysis.name}`} title="Delete" loading={remove.isPending}
        onClick={() => window.confirm(`Delete "${analysis.name}" with its documents and findings?`) && remove.mutate()}
      >
        <Trash2 className="size-4" />
      </Button>
    </li>
  )
}

export default function AnalysesPage() {
  const navigate = useNavigate()
  const { data: analyses, isLoading, error, refetch } = useProjects()
  const [query, setQuery] = useState('')
  const visible = (analyses || []).filter((a) => a.name.toLowerCase().includes(query.toLowerCase()))

  return (
    <>
      <PageHeader
        title="Analyses"
        description="Every comparison you have created."
        actions={<Button icon={Plus} onClick={() => navigate('/analyses/new')}>New analysis</Button>}
      />
      <PageBody className="space-y-4">
        <div className="relative max-w-sm">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted" />
          <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search analyses…" className="pl-9" />
        </div>
        {error ? <ErrorState error={error} onRetry={refetch} />
          : isLoading ? <Skeleton className="h-64" />
          : visible.length ? <Panel><ul>{visible.map((a) => <AnalysisRow key={a.id} analysis={a} />)}</ul></Panel>
          : (
            <Empty icon={FolderOpen} title={analyses?.length ? 'No analyses match your search.' : 'No analyses yet.'}
              action={!analyses?.length && <Button icon={Plus} onClick={() => navigate('/analyses/new')}>Create your first analysis</Button>}
            />
          )}
      </PageBody>
    </>
  )
}
