/** Dashboard — what the product does, the main action, and recent analyses. */
import { useNavigate, Link } from 'react-router-dom'
import { ArrowRight, BadgeCheck, FileText, FolderOpen, Plus, ScanSearch } from 'lucide-react'
import { useProjects } from '@/lib/queries'
import { Button, Empty, ErrorState, Panel, Skeleton } from '@/components/kit'
import { PageBody } from '@/components/layout'
import { AnalysisCard } from '@/features/analysis/summary'

const HOW = [
  { icon: FileText, title: 'What should exist', text: 'Upload the reference: a spec, requirements or a job description.' },
  { icon: FileText, title: 'What currently exists', text: 'Upload the current state: design docs, API docs or a resume.' },
  { icon: ScanSearch, title: 'Find gaps', text: 'Every requirement is checked: covered, partial, missing, conflict or unclear.' },
  { icon: BadgeCheck, title: 'Review evidence', text: 'Each finding cites text verified in your documents.' },
]

export default function DashboardPage() {
  const navigate = useNavigate()
  const { data: analyses, isLoading, error, refetch } = useProjects()
  const recent = analyses?.slice(0, 6) || []

  return (
    <PageBody className="space-y-8">
      <section className="rounded-lg border border-border bg-surface p-6 sm:p-8">
        <p className="text-[11px] font-medium tracking-[0.2em] text-secondary uppercase">Document intelligence</p>
        <h1 className="mt-2 max-w-3xl text-3xl font-semibold tracking-tight text-balance sm:text-4xl">
          Find gaps between what <span className="font-serif font-normal italic">should</span> exist and what currently exists.
        </h1>
        <p className="mt-3 max-w-2xl text-sm text-muted">
          Compare requirements against technical documentation — or a job description against a resume — and inspect the evidence behind every finding.
        </p>
        <Button size="lg" icon={Plus} className="mt-6" onClick={() => navigate('/analyses/new')}>New analysis</Button>
      </section>

      <section>
        <div className="mb-4 flex items-end justify-between">
          <h2 className="text-lg font-semibold tracking-tight">Recent analyses</h2>
          {analyses?.length > recent.length && (
            <Link to="/analyses" className="inline-flex items-center gap-1 text-sm text-muted hover:text-foreground">All analyses <ArrowRight className="size-3.5" /></Link>
          )}
        </div>
        {error ? <ErrorState error={error} onRetry={refetch} />
          : isLoading ? (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-44" />)}</div>
          ) : recent.length ? (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{recent.map((a) => <AnalysisCard key={a.id} analysis={a} />)}</div>
          ) : (
            <Empty icon={FolderOpen} title="No analyses yet." action={<Button icon={Plus} onClick={() => navigate('/analyses/new')}>Create your first analysis</Button>}>
              Compare two sets of documents and discover what is covered, missing, conflicting or unclear.
            </Empty>
          )}
      </section>

      <section>
        <h2 className="mb-4 text-lg font-semibold tracking-tight">How it works</h2>
        <div className="overflow-hidden rounded-xl grid gap-px border border-border bg-border sm:grid-cols-2 xl:grid-cols-4">
          {HOW.map((s, i) => (
            <Panel key={s.title} className="border-0 p-5">
              <span className="font-mono text-xs text-muted">0{i + 1}</span>
              <s.icon className="mt-3 size-5 text-secondary" />
              <p className="mt-2 font-semibold">{s.title}</p>
              <p className="mt-1 text-sm text-muted">{s.text}</p>
            </Panel>
          ))}
        </div>
      </section>
    </PageBody>
  )
}
