/**
 * Analysis page (UI spec §11–21): header with summary counts, real processing stages,
 * and tabs — Findings · Evidence · Requirements · Documents · Map.
 * Tab, filter, open document/chunk live in the URL so navigation keeps context.
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { Check, ClipboardList, FileText, ListChecks, Network, Pencil, Play, Quote, RotateCw, Sparkles } from 'lucide-react'
import { api } from '@/lib/api'
import { analysisType } from '@/lib/analysisTypes'
import { timeAgo } from '@/lib/format'
import { keys, useAction, useDocuments, useFindings, useProject, useRequirements, useRuns } from '@/lib/queries'
import { Button, ErrorState, Input, Notice, Skeleton, Tabs, Tag } from '@/components/kit'
import { PageBody, PageHeader } from '@/components/layout'
import { ProcessingStages, computeStages } from '@/features/analysis/ProcessingStages'
import { StatusCounts } from '@/features/analysis/summary'
import EvidenceDrawer from '@/features/analysis/EvidenceDrawer'
import FindingsTab from '@/features/analysis/FindingsTab'
import EvidenceTab from '@/features/analysis/EvidenceTab'
import RequirementsTab from '@/features/analysis/RequirementsTab'
import DocumentsTab from '@/features/analysis/DocumentsTab'
import MapTab from '@/features/analysis/MapTab'

/** Analysis name that becomes an input on click. */
function EditableName({ project }) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(project.name)
  const rename = useAction((name) => api.renameProject(project.id, name), { invalidate: [keys.project(project.id), keys.projects] })
  const save = () => {
    setEditing(false)
    if (value.trim() && value.trim() !== project.name) rename.mutate(value.trim())
    else setValue(project.name)
  }
  if (editing) {
    return (
      <Input autoFocus value={value} maxLength={200} className="h-auto border-0 border-b bg-transparent px-0 text-2xl font-semibold sm:text-3xl"
        onChange={(e) => setValue(e.target.value)} onBlur={save}
        onKeyDown={(e) => { if (e.key === 'Enter') save(); if (e.key === 'Escape') { setValue(project.name); setEditing(false) } }} />
    )
  }
  return (
    <button type="button" onClick={() => setEditing(true)} className="group inline-flex cursor-text items-center gap-2 text-left" title="Rename">
      {project.name}<Pencil className="size-4 text-muted opacity-0 transition-opacity group-hover:opacity-100" />
    </button>
  )
}

export default function AnalysisPage() {
  const { analysisId: id } = useParams()
  const [params, setParams] = useSearchParams()
  const queryClient = useQueryClient()
  const project = useProject(id)
  const { data: documents = [] } = useDocuments(id)
  const { data: requirements = [] } = useRequirements(id)
  const { data: runs = [] } = useRuns(id)
  const [openFinding, setOpenFinding] = useState(null)

  const latest = runs[0]
  const completed = runs.find((r) => r.status === 'completed')
  const { data: findings = [] } = useFindings(completed?.id)
  const runActive = latest && (latest.status === 'queued' || latest.status === 'running')
  const p = project.data

  const setParam = (changes) => setParams((prev) => {
    const next = new URLSearchParams(prev)
    Object.entries(changes).forEach(([k, v]) => (v == null ? next.delete(k) : next.set(k, v)))
    return next
  }, { replace: true })

  const invalidateAll = [keys.project(id), keys.requirements(id), keys.runs(id), keys.projects]
  const extract = useAction(() => api.extractRequirements(id), { invalidate: invalidateAll })
  const analyze = useAction(() => api.analyze(id), { invalidate: invalidateAll })
  const approveAllAndAnalyze = useAction(async () => { await api.approveAll(id); return api.analyze(id) }, { invalidate: invalidateAll })

  // "Start analysis" from the New Analysis flow: extract requirements once the documents are ready
  const started = useRef(false)
  const docsReady = documents.some((d) => d.role === 'reference' && d.status === 'indexed')
    && documents.some((d) => d.role === 'existing' && d.status === 'indexed')
    && !documents.some((d) => d.status === 'uploaded' || d.status === 'processing')
  useEffect(() => {
    if (params.get('start') !== '1' || !p || started.current) return
    if (p.extraction_status !== 'idle' || requirements.length) { setParam({ start: null }); return }
    if (docsReady) {
      started.current = true
      setParam({ start: null, tab: 'requirements' })
      extract.mutate()
    }
  }, [params, p, docsReady, requirements.length]) // eslint-disable-line react-hooks/exhaustive-deps

  // When a background job finishes (polling flips the status), refresh what it produced
  const prev = useRef({ extracting: false, active: false })
  useEffect(() => {
    const extracting = p?.extraction_status === 'running'
    if (prev.current.extracting && !extracting) queryClient.invalidateQueries({ queryKey: keys.requirements(id) })
    if (prev.current.active && !runActive) invalidateAll.forEach((k) => queryClient.invalidateQueries({ queryKey: k }))
    prev.current = { extracting, active: Boolean(runActive) }
  }) // eslint-disable-line react-hooks/exhaustive-deps

  const counts = useMemo(() => (findings.length ? findings.reduce((a, f) => ({ ...a, [f.status]: (a[f.status] || 0) + 1 }), {}) : null), [findings])

  if (project.error) return <PageBody><ErrorState error={project.error} onRetry={project.refetch} /></PageBody>
  if (!p) return <PageBody className="space-y-4"><Skeleton className="h-24" /><Skeleton className="h-72" /></PageBody>

  const type = analysisType(p.preset)
  const stages = computeStages({ project: p, documents, requirements, run: latest })
  const somethingWrong = stages.some((s) => s.state === 'failed')
  const showStages = !completed || runActive || somethingWrong || p.extraction_status === 'running'
  const drafts = requirements.filter((r) => r.status === 'draft').length
  const tab = params.get('tab') || (completed ? 'findings' : requirements.length ? 'requirements' : 'documents')
  const canAnalyze = p.approved_requirements > 0 && docsReady && !runActive

  const openDocument = (evidence) => {
    setOpenFinding(null)
    setParam({ tab: 'documents', doc: evidence.document_id, chunk: evidence.chunk_id })
  }

  return (
    <>
      <PageHeader
        crumbs={[{ label: 'Analyses', to: '/analyses' }, { label: p.name }]}
        eyebrow={type.label}
        title={<EditableName key={p.name} project={p} />}
        description={p.last_analyzed_at ? `Last analysed ${timeAgo(p.last_analyzed_at)}` : 'Not analysed yet'}
        actions={
          <Button icon={completed ? RotateCw : Play} variant={completed ? 'outline' : 'accent'} disabled={!canAnalyze} loading={runActive || analyze.isPending}
            title={!p.approved_requirements ? 'Approve requirements first' : !docsReady ? 'Documents are still processing' : undefined}
            onClick={() => analyze.mutate()}
          >
            {runActive ? 'Analysing…' : completed ? 'Analyse again' : 'Run analysis'}
          </Button>
        }
      >
        {counts && (
          <StatusCounts counts={counts} all className="mt-4" selected={params.get('status')}
            onSelect={(s) => setParam({ tab: 'findings', status: s })} />
        )}
      </PageHeader>

      <PageBody className="space-y-5">
        {showStages && (
          <ProcessingStages
            stages={stages}
            actions={{
              upload: <Button size="sm" variant="outline" icon={FileText} onClick={() => setParam({ tab: 'documents' })}>Add documents</Button>,
              extract: <Button size="sm" variant="accent" icon={Sparkles} loading={extract.isPending || p.extraction_status === 'running'}
                disabled={!docsReady} onClick={() => extract.mutate()}>{p.extraction_status === 'failed' ? 'Retry extraction' : 'Extract requirements'}</Button>,
              review: drafts > 0 && <>
                <Button size="sm" variant="outline" icon={ClipboardList} onClick={() => setParam({ tab: 'requirements' })}>Review {drafts} drafts</Button>
                <Button size="sm" icon={Check} loading={approveAllAndAnalyze.isPending} disabled={!docsReady} onClick={() => approveAllAndAnalyze.mutate()}>Approve all &amp; analyse</Button>
              </>,
              analyse: !runActive && p.approved_requirements > 0 && drafts === 0 && <Button size="sm" variant="accent" icon={Play} disabled={!canAnalyze}
                loading={analyze.isPending} onClick={() => analyze.mutate()}>{latest?.status === 'failed' ? 'Retry analysis' : 'Run analysis'}</Button>,
            }}
          />
        )}
        {completed && runActive && <Notice tone="info">Showing results from the previous run while the new analysis runs.</Notice>}

        <Tabs
          value={tab}
          onChange={(t) => setParam({ tab: t, doc: null, chunk: null })}
          tabs={[
            { id: 'findings', label: 'Findings', icon: ListChecks, count: findings.length || null },
            { id: 'evidence', label: 'Evidence', icon: Quote, count: findings.reduce((n, f) => n + f.evidence.length, 0) || null },
            { id: 'requirements', label: 'Requirements', icon: ClipboardList, count: requirements.length || null },
            { id: 'documents', label: 'Documents', icon: FileText, count: documents.length || null },
            { id: 'map', label: 'Map', icon: Network },
          ]}
        />

        {tab === 'findings' && <FindingsTab findings={findings} analysisName={p.name} filter={params.get('status')} onFilter={(s) => setParam({ status: s })} onView={setOpenFinding} />}
        {tab === 'evidence' && <EvidenceTab findings={findings} projectId={id} onView={setOpenFinding} />}
        {tab === 'requirements' && <RequirementsTab project={p} documentsReady={docsReady} />}
        {tab === 'documents' && (
          <DocumentsTab project={p} documents={documents} findings={findings}
            selectedDocId={params.get('doc')} focusChunkId={params.get('chunk')} onSelect={(docId) => setParam({ doc: docId, chunk: null })} />
        )}
        {tab === 'map' && <MapTab project={p} requirements={requirements} findings={findings} onView={setOpenFinding} />}

        <p className="pt-4 text-xs text-muted">
          <Tag>{type.short}</Tag>{' '}
          {completed && <>Run {completed.model} · {completed.prompt_version} · {completed.stats?.llm_calls ?? 0} LLM calls · {completed.stats?.cache_hits ?? 0} reused from cache</>}
        </p>
      </PageBody>

      <EvidenceDrawer finding={openFinding} onClose={() => setOpenFinding(null)} onOpenDocument={openDocument} />
    </>
  )
}
