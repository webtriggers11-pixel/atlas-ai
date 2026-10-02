/**
 * New Analysis flow (UI spec §6–9):
 *   1. What do you want to analyze? (type + name)  →  creates the analysis
 *   2. What should exist? / What currently exists? (uploads, with real processing state)
 *   3. Start analysis → the analysis page takes over (extraction → review → findings)
 * The created analysis id is kept in the URL (?id=) so a reload doesn't lose progress.
 */
import { useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { ArrowRight, Check, Play } from 'lucide-react'
import { api } from '@/lib/api'
import { ANALYSIS_TYPES, analysisType } from '@/lib/analysisTypes'
import { keys, useAction, useDocuments, useProject } from '@/lib/queries'
import { cn } from '@/lib/utils'
import { Button, ErrorState, Eyebrow, Field, Input, Notice, Panel, Skeleton } from '@/components/kit'
import { PageBody, PageHeader } from '@/components/layout'
import { DocumentRow, DocumentUploader } from '@/features/documents'

/** Step indicator: 1 Type · 2 Documents · 3 Start. */
function Steps({ current }) {
  const steps = ['Analysis type', 'Documents', 'Start']
  return (
    <ol className="mt-5 flex flex-wrap gap-4 text-sm">
      {steps.map((label, i) => (
        <li key={label} className={cn('flex items-center gap-2', i === current ? 'text-foreground' : 'text-muted')}>
          <span className={cn('grid size-6 place-items-center border font-mono text-[11px]',
            i < current ? 'border-success/50 bg-success/10 text-success' : i === current ? 'border-secondary text-secondary' : 'border-border')}>
            {i < current ? <Check className="size-3" /> : i + 1}
          </span>
          {label}
        </li>
      ))}
    </ol>
  )
}

/** Step 1 — choose the analysis type and name it. */
function TypeStep({ onCreated }) {
  const [preset, setPreset] = useState(null)   // no default: the type decides how the AI reads the documents
  const [name, setName] = useState('')
  const create = useAction(() => api.createProject(name.trim(), preset), {
    invalidate: [keys.projects],
    onSuccess: (project) => onCreated(project.id),
  })
  return (
    <form className="max-w-3xl space-y-6" onSubmit={(e) => { e.preventDefault(); if (name.trim() && preset) create.mutate() }}>
      <div>
        <h2 className="text-lg font-semibold tracking-tight">What do you want to analyze?</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {Object.entries(ANALYSIS_TYPES).map(([key, t]) => (
            <button
              key={key} type="button" onClick={() => setPreset(key)} aria-pressed={preset === key}
              className={cn('cursor-pointer border p-4 text-left transition-colors', preset === key ? 'border-secondary bg-secondary/10' : 'border-border bg-surface hover:bg-fill')}
            >
              <p className="font-semibold">{t.label}</p>
              <p className="mt-1 text-sm text-muted">{t.blurb}</p>
            </button>
          ))}
        </div>
      </div>
      <Field label="Name" hint="Name it after what you're comparing.">
        <Input
          value={name} onChange={(e) => setName(e.target.value)} maxLength={200}
          placeholder={preset === 'resume_jd' ? 'Resume vs Python Backend JD' : preset ? 'Payments API — SRS vs design docs' : 'Choose a type above, then name it'}
        />
      </Field>
      <div className="flex flex-wrap items-center gap-3">
        <Button type="submit" icon={ArrowRight} disabled={!name.trim() || !preset} loading={create.isPending}>Continue</Button>
        {!preset && <span className="text-sm text-muted">Choose what you want to analyze first.</span>}
      </div>
    </form>
  )
}

/** One upload group ("What should exist?" or "What currently exists?"). */
function UploadGroup({ projectId, role, type, docs }) {
  const copy = type[role]
  return (
    <Panel className="flex flex-col">
      <div className="border-b border-border p-5">
        <Eyebrow>{role === 'reference' ? 'Reference documents' : 'Existing documents'}</Eyebrow>
        <h3 className="mt-1 text-lg font-semibold tracking-tight">{copy.title}</h3>
        <p className="mt-1 text-sm text-muted">{copy.text}</p>
        <p className="mt-1 text-xs text-muted">{copy.examples}</p>
      </div>
      <div className="p-5"><DocumentUploader projectId={projectId} role={role} label={role === 'reference' ? 'reference documents' : 'existing documents'} /></div>
      {docs.length > 0 && <ul className="border-t border-border">{docs.map((d) => <DocumentRow key={d.id} doc={d} projectId={projectId} />)}</ul>}
    </Panel>
  )
}

/** Step 2/3 — upload both groups, then start. */
function DocumentsStep({ projectId }) {
  const navigate = useNavigate()
  const { data: project, error: projectError, refetch } = useProject(projectId)
  const { data: documents = [], isLoading } = useDocuments(projectId)

  if (projectError) return <ErrorState error={projectError} onRetry={refetch} />
  if (!project || isLoading) return <Skeleton className="h-80" />

  const type = analysisType(project.preset)
  const group = (role) => documents.filter((d) => d.role === role)
  const ready = (role) => group(role).some((d) => d.status === 'indexed')
  const busy = documents.some((d) => d.status === 'uploaded' || d.status === 'processing')
  const failed = documents.filter((d) => d.status === 'failed')
  const canStart = ready('reference') && ready('existing') && !busy

  return (
    <div className="space-y-5">
      <p className="text-sm text-muted">Analysis: <span className="font-medium text-foreground">{project.name}</span> · {type.label}</p>
      <div className="grid gap-4 lg:grid-cols-2">
        <UploadGroup projectId={projectId} role="reference" type={type} docs={group('reference')} />
        <UploadGroup projectId={projectId} role="existing" type={type} docs={group('existing')} />
      </div>
      {failed.length > 0 && (
        <Notice tone="warning">
          {documents.length - failed.length} of {documents.length} documents processed. {failed.map((d) => d.filename).join(', ')} failed — use Retry, or remove it.
        </Notice>
      )}
      <div className="flex flex-wrap items-center justify-end gap-3">
        <span className="text-sm text-muted">
          {busy ? 'Processing documents…' : !ready('reference') || !ready('existing') ? 'Add at least one document to each group.' : 'Ready to analyse.'}
        </span>
        <Button size="lg" icon={Play} disabled={!canStart} onClick={() => navigate(`/analyses/${projectId}?start=1`)}>Start analysis</Button>
      </div>
    </div>
  )
}

export default function NewAnalysisPage() {
  const [params, setParams] = useSearchParams()
  const projectId = params.get('id')
  return (
    <>
      <PageHeader crumbs={[{ label: 'Analyses', to: '/analyses' }, { label: 'New analysis' }]} title="Create new analysis">
        <Steps current={projectId ? 1 : 0} />
      </PageHeader>
      <PageBody>
        {projectId ? <DocumentsStep projectId={projectId} /> : <TypeStep onCreated={(id) => setParams({ id })} />}
      </PageBody>
    </>
  )
}
