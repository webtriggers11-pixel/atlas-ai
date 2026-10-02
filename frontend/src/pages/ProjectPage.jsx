/**
 * Project workspace — the guided flow:
 *   ① Documents → ② Requirements → ③ Analysis & findings → (Search: retrieval inspector)
 * The active step lives in the URL (?step=) so reloads and links keep their place.
 */
import { useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { Check, ClipboardList, FileText, Pencil, ScanSearch, Search } from 'lucide-react'
import { api } from '@/lib/api'
import { keys, useAction, useDocuments, useProject, useRuns } from '@/lib/queries'
import { cn } from '@/lib/utils'
import { Input, Notice, Skeleton } from '@/components/kit'
import { PageHeader } from '@/components/layout'
import { PRESETS } from '@/pages/ProjectsPage'
import DocumentsStep from '@/features/project/DocumentsStep'
import RequirementsStep from '@/features/project/RequirementsStep'
import AnalysisStep from '@/features/project/AnalysisStep'
import SearchStep from '@/features/project/SearchStep'

/** Project name that turns into an input on click. */
function EditableName({ project }) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(project.name)
  const rename = useAction((name) => api.renameProject(project.id, name), {
    invalidate: [keys.project(project.id), keys.projects],
  })
  const save = () => {
    setEditing(false)
    if (value.trim() && value.trim() !== project.name) rename.mutate(value.trim())
    else setValue(project.name)
  }
  if (editing) {
    return (
      <Input
        autoFocus value={value} maxLength={200}
        className="h-auto max-w-3xl border-0 border-b bg-transparent px-0 text-4xl font-semibold tracking-tighter"
        onChange={(e) => setValue(e.target.value)}
        onBlur={save}
        onKeyDown={(e) => { if (e.key === 'Enter') save(); if (e.key === 'Escape') { setValue(project.name); setEditing(false) } }}
      />
    )
  }
  return (
    <button type="button" onClick={() => setEditing(true)} className="group inline-flex cursor-text items-center gap-3 text-left">
      {project.name}
      <Pencil className="size-4 text-muted opacity-0 transition-opacity group-hover:opacity-100" />
    </button>
  )
}

const STEPS = [
  { id: 'documents', label: 'Documents', icon: FileText },
  { id: 'requirements', label: 'Requirements', icon: ClipboardList },
  { id: 'analysis', label: 'Analysis', icon: ScanSearch },
  { id: 'search', label: 'Search', icon: Search, secondary: true },
]

export default function ProjectPage() {
  const { projectId } = useParams()
  const [params, setParams] = useSearchParams()
  const { data: project, isLoading, error } = useProject(projectId)
  const { data: documents = [] } = useDocuments(projectId)
  const { data: runs = [] } = useRuns(projectId)

  if (error) {
    return <div className="mx-auto max-w-6xl px-6 pt-36"><Notice>{error.message}</Notice></div>
  }
  if (isLoading || !project) {
    return <div className="mx-auto max-w-6xl space-y-4 px-6 pt-36"><Skeleton className="h-12 w-2/3" /><Skeleton className="h-64" /></div>
  }

  const indexed = (role) => documents.some((d) => d.role === role && d.status === 'indexed')
  const done = {
    documents: indexed('reference') && indexed('existing'),
    requirements: project.approved_requirements > 0,
    analysis: runs.some((r) => r.status === 'completed'),
  }
  const step = params.get('step') || (done.requirements ? 'analysis' : done.documents ? 'requirements' : 'documents')
  const preset = PRESETS[project.preset]

  return (
    <>
      <PageHeader
        eyebrow={preset?.label}
        crumbs={[{ label: 'Projects', to: '/' }, { label: project.name }]}
        title={<EditableName key={project.name} project={project} />}
        intro={`${preset?.reference} compared against ${preset?.existing.toLowerCase()}.`}
      >
        <nav className="mt-10 flex flex-wrap gap-px border border-border bg-border" aria-label="Steps">
          {STEPS.map((s, i) => {
            const active = step === s.id
            return (
              <button
                key={s.id}
                type="button"
                onClick={() => setParams({ step: s.id })}
                aria-current={active ? 'step' : undefined}
                className={cn(
                  'flex flex-1 cursor-pointer items-center gap-3 px-4 py-3 text-left transition-colors',
                  s.secondary ? 'grow-0 basis-auto' : 'min-w-40',
                  active ? 'bg-surface' : 'bg-background hover:bg-surface/60',
                )}
              >
                <span className={cn(
                  'grid size-7 shrink-0 place-items-center border font-mono text-[11px]',
                  done[s.id] ? 'border-success/50 bg-success/10 text-success' : active ? 'border-secondary text-secondary' : 'border-border text-muted',
                )}>
                  {done[s.id] ? <Check className="size-3.5" /> : s.secondary ? <s.icon className="size-3.5" /> : i + 1}
                </span>
                <span className={cn('text-sm', active ? 'font-semibold' : 'text-muted')}>{s.label}</span>
                {active && <span className="ml-auto hidden h-0.5 w-6 bg-secondary sm:block" />}
              </button>
            )
          })}
        </nav>
      </PageHeader>

      <section className="px-6 pb-24">
        <div className="mx-auto max-w-6xl">
        {step === 'documents' && <DocumentsStep project={project} onNext={() => setParams({ step: 'requirements' })} />}
        {step === 'requirements' && <RequirementsStep project={project} documentsReady={done.documents} onNext={() => setParams({ step: 'analysis' })} />}
        {step === 'analysis' && <AnalysisStep project={project} />}
        {step === 'search' && <SearchStep project={project} />}
        </div>
      </section>
    </>
  )
}
