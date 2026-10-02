/** Projects list — every gap analysis, with its progress at a glance, plus "New analysis". */
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, BadgeCheck, ClipboardList, FileText, FolderOpen, Plus, ScanSearch, Trash2 } from 'lucide-react'
import { api } from '@/lib/api'
import { keys, useAction, useProjects } from '@/lib/queries'
import { cn } from '@/lib/utils'
import { Button, Empty, Field, Input, Modal, Notice, Panel, Reveal, Skeleton, StatusPill, Tag } from '@/components/kit'
import { PageHeader } from '@/components/layout'

export const PRESETS = {
  spec_coverage: {
    label: 'Spec coverage',
    reference: 'Requirements / spec',
    existing: 'Design & technical docs',
    blurb: 'Does the technical documentation cover every requirement? SRS/BRD vs SDD/API docs.',
  },
  resume_jd: {
    label: 'Resume vs job',
    reference: 'Job description',
    existing: 'Resume',
    blurb: 'Which job requirements does the resume prove, and which are missing?',
  },
}

const STEPS = [
  { icon: FileText, title: 'Upload', text: 'Reference documents (what should exist) and existing documents (what does).' },
  { icon: ClipboardList, title: 'Review requirements', text: 'AI extracts atomic requirements; you edit, merge and approve them.' },
  { icon: ScanSearch, title: 'Analyse', text: 'Each requirement is matched to evidence and classified.' },
  { icon: BadgeCheck, title: 'Verify', text: 'Every finding cites quotes checked against the source — nothing invented.' },
]

/** Dialog to create a project (name + preset). */
function NewProjectModal({ open, onClose }) {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [preset, setPreset] = useState('spec_coverage')
  const create = useAction(() => api.createProject(name.trim(), preset), {
    invalidate: [keys.projects],
    onSuccess: (project) => {
      onClose()
      setName('')
      navigate(`/projects/${project.id}`)
    },
  })

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="New analysis"
      description="Name it after what you're comparing."
      footer={<>
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button icon={ArrowRight} disabled={!name.trim()} loading={create.isPending} onClick={() => create.mutate()}>Create</Button>
      </>}
    >
      <form className="space-y-5" onSubmit={(e) => { e.preventDefault(); if (name.trim()) create.mutate() }}>
        <Field label="Name">
          <Input autoFocus value={name} onChange={(e) => setName(e.target.value)} placeholder="Payments API v2 — spec review" maxLength={200} />
        </Field>
        <div className="space-y-1.5">
          <span className="text-[11px] font-medium tracking-wider text-muted uppercase">Type</span>
          <div className="grid gap-2 sm:grid-cols-2">
            {Object.entries(PRESETS).map(([key, p]) => (
              <button
                key={key}
                type="button"
                onClick={() => setPreset(key)}
                className={cn(
                  'cursor-pointer border p-3 text-left transition-colors',
                  preset === key ? 'border-secondary bg-secondary/10' : 'border-border hover:bg-fill',
                )}
              >
                <p className="text-sm font-semibold">{p.label}</p>
                <p className="mt-1 text-xs text-muted">{p.blurb}</p>
              </button>
            ))}
          </div>
        </div>
      </form>
    </Modal>
  )
}

/** One project card with counts and the latest run status. */
function ProjectCard({ project, index }) {
  const preset = PRESETS[project.preset]
  const remove = useAction(() => api.deleteProject(project.id), { invalidate: [keys.projects], success: 'Project deleted' })

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.04 * index, duration: 0.4 }}
    >
      <Panel className="group relative flex h-full flex-col p-5 transition-colors hover:border-foreground/25">
        <div className="flex items-start justify-between gap-3">
          <Tag>{preset?.label || project.preset}</Tag>
          {project.latest_run_status
            ? <StatusPill status={project.latest_run_status}>{project.latest_run_status === 'completed' ? 'analysed' : project.latest_run_status}</StatusPill>
            : <span className="font-mono text-[10px] tracking-wider text-muted uppercase">not analysed</span>}
        </div>
        <Link to={`/projects/${project.id}`} className="mt-4 block text-lg leading-snug font-semibold tracking-tight after:absolute after:inset-0">
          {project.name}
        </Link>
        <dl className="mt-auto grid grid-cols-3 gap-2 border-t border-border pt-4 text-center">
          {[
            ['Reference', project.reference_documents],
            ['Existing', project.existing_documents],
            ['Approved', `${project.approved_requirements}/${project.requirements}`],
          ].map(([label, value]) => (
            <div key={label}>
              <dd className="font-mono text-lg tabular-nums">{value}</dd>
              <dt className="text-[10px] tracking-wider text-muted uppercase">{label}</dt>
            </div>
          ))}
        </dl>
        <Button
          variant="ghost" size="icon"
          className="absolute right-3 bottom-[4.6rem] z-10 opacity-0 transition-opacity group-hover:opacity-100 focus:opacity-100"
          aria-label={`Delete ${project.name}`}
          loading={remove.isPending}
          onClick={() => window.confirm(`Delete "${project.name}" and all its documents and findings?`) && remove.mutate()}
        >
          <Trash2 className="size-4" />
        </Button>
      </Panel>
    </motion.div>
  )
}

export default function ProjectsPage() {
  const { data: projects, isLoading, error } = useProjects()
  const [creating, setCreating] = useState(false)

  return (
    <>
      <PageHeader
        eyebrow="Document gap analysis"
        title={<>Find what your documents <span className="font-serif font-normal italic">don&apos;t</span> say.</>}
        intro="Compare requirements against technical documentation — or a job description against a resume — and get evidence-backed findings you can verify."
        actions={<Button size="lg" icon={Plus} onClick={() => setCreating(true)}>New analysis</Button>}
      />

      <section className="px-6 pb-24">
        <div className="mx-auto max-w-6xl">
        {error && <Notice className="mb-6">{error.message}</Notice>}

        {isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[0, 1, 2].map((i) => <Skeleton key={i} className="h-48" />)}
          </div>
        ) : projects?.length ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((p, i) => <ProjectCard key={p.id} project={p} index={i} />)}
          </div>
        ) : !error && (
          <Reveal>
            <Empty
              icon={FolderOpen}
              title="No analyses yet"
              action={<Button icon={Plus} onClick={() => setCreating(true)}>Start your first analysis</Button>}
            >
              Create a project, upload two sets of documents and let Atlas show you what&apos;s covered, partial, missing or contradicting.
            </Empty>
          </Reveal>
        )}

        <div className="mt-16 grid gap-px border border-border bg-border sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((s, i) => (
            <Reveal key={s.title} delay={0.05 * i} className="bg-background p-6">
              <span className="font-mono text-xs text-muted">0{i + 1}</span>
              <s.icon className="mt-4 size-5 text-secondary" />
              <p className="mt-3 font-semibold">{s.title}</p>
              <p className="mt-1 text-sm text-muted">{s.text}</p>
            </Reveal>
          ))}
        </div>
        </div>
      </section>

      <NewProjectModal open={creating} onClose={() => setCreating(false)} />
    </>
  )
}
