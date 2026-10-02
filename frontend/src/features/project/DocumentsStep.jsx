/** Step 1 — upload reference and existing documents and watch them get processed. */
import { useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, ArrowRight, ClipboardPaste, Eye, FileText, RotateCw, Trash2, Upload } from 'lucide-react'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { keys, useAction, useChunks, useDocuments } from '@/lib/queries'
import { cn } from '@/lib/utils'
import { Button, Drawer, Empty, Eyebrow, Field, Input, Notice, Panel, Skeleton, StatusPill, Tag, Textarea } from '@/components/kit'
import { PRESETS } from '@/pages/ProjectsPage'

const ACCEPT = '.pdf,.docx,.txt,.md'

const formatSize = (bytes) =>
  bytes < 1024 ? `${bytes} B` : bytes < 1024 ** 2 ? `${(bytes / 1024).toFixed(0)} KB` : `${(bytes / 1024 ** 2).toFixed(1)} MB`

/** Drag-and-drop / click-to-browse upload area plus a "paste text" alternative. */
function UploadArea({ projectId, role }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)
  const [pasting, setPasting] = useState(false)
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const invalidate = [keys.documents(projectId), keys.project(projectId)]

  const upload = useAction(async (files) => {
    const results = []
    for (const file of files) results.push(await api.uploadFile(projectId, role, file))  // one at a time: keeps order & errors clear
    return results
  }, { invalidate, success: (docs) => (docs.length === 1 ? `Uploaded ${docs[0].filename}` : `Uploaded ${docs.length} files`) })

  const paste = useAction(() => api.uploadText(projectId, role, title.trim() || 'pasted-text', text), {
    invalidate,
    success: 'Text added',
    onSuccess: () => { setText(''); setTitle(''); setPasting(false) },
  })

  const onFiles = (fileList) => {
    const files = [...fileList].filter((f) => /\.(pdf|docx|txt|md)$/i.test(f.name))
    if (files.length < fileList.length) toast.error('Only PDF, DOCX, TXT and MD files are supported.')
    if (files.length) upload.mutate(files)
  }

  if (pasting) {
    return (
      <div className="space-y-3 border border-border p-4">
        <Field label="Title"><Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Job description" /></Field>
        <Field label="Text"><Textarea value={text} onChange={(e) => setText(e.target.value)} className="min-h-40" placeholder="Paste the document text here…" /></Field>
        <div className="flex justify-end gap-2">
          <Button variant="outline" size="sm" onClick={() => setPasting(false)}>Cancel</Button>
          <Button size="sm" disabled={!text.trim()} loading={paste.isPending} onClick={() => paste.mutate()}>Add text</Button>
        </div>
      </div>
    )
  }

  return (
    <div>
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); onFiles(e.dataTransfer.files) }}
        className={cn(
          'flex w-full cursor-pointer flex-col items-center gap-2 border border-dashed px-4 py-8 text-center transition-colors',
          dragging ? 'border-secondary bg-secondary/10' : 'border-border hover:border-foreground/30 hover:bg-fill',
        )}
      >
        {upload.isPending
          ? <RotateCw className="size-5 animate-spin text-secondary" />
          : <Upload className={cn('size-5', dragging ? 'text-secondary' : 'text-muted')} />}
        <span className="text-sm font-medium">{upload.isPending ? 'Uploading…' : 'Drop files or click to browse'}</span>
        <span className="text-xs text-muted">PDF, DOCX, TXT, MD · max 20 MB</span>
      </button>
      <input ref={inputRef} type="file" accept={ACCEPT} multiple hidden onChange={(e) => { onFiles(e.target.files); e.target.value = '' }} />
      <button type="button" onClick={() => setPasting(true)} className="mt-2 inline-flex cursor-pointer items-center gap-1.5 text-xs text-muted hover:text-foreground">
        <ClipboardPaste className="size-3.5" /> or paste text instead
      </button>
    </div>
  )
}

/** One document row: name, size, status, and actions. */
function DocumentRow({ doc, projectId, onView }) {
  const invalidate = [keys.documents(projectId), keys.project(projectId)]
  const reprocess = useAction(() => api.reprocessDocument(doc.id), { invalidate, success: 'Re-queued' })
  const remove = useAction(() => api.deleteDocument(doc.id), { invalidate, success: 'Document removed' })
  const busy = doc.status === 'uploaded' || doc.status === 'processing'
  const label = { uploaded: 'queued', processing: 'processing', indexed: 'ready', failed: 'failed' }[doc.status]

  return (
    <motion.li layout initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="border-b border-border last:border-b-0">
      <div className="flex items-center gap-3 px-4 py-3">
        <FileText className="size-4 shrink-0 text-muted" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium" title={doc.filename}>{doc.filename}</p>
          <p className="mt-0.5 font-mono text-[11px] text-muted">
            {doc.file_type.toUpperCase()} · {formatSize(doc.size_bytes)}
            {doc.status === 'indexed' && <> · {doc.chunk_count} chunks{doc.page_count ? ` · ${doc.page_count} pages` : ''}</>}
          </p>
        </div>
        <StatusPill status={doc.status}>{label}</StatusPill>
        <div className="flex">
          {doc.status === 'indexed' && <Button variant="ghost" size="icon" aria-label="View chunks" onClick={() => onView(doc)}><Eye className="size-4" /></Button>}
          {(doc.status === 'failed' || (busy && doc.error_message)) && (
            <Button variant="ghost" size="icon" aria-label="Reprocess" loading={reprocess.isPending} onClick={() => reprocess.mutate()}><RotateCw className="size-4" /></Button>
          )}
          <Button
            variant="ghost" size="icon" aria-label="Delete" loading={remove.isPending}
            onClick={() => window.confirm(`Remove ${doc.filename}?`) && remove.mutate()}
          >
            <Trash2 className="size-4" />
          </Button>
        </div>
      </div>
      {doc.error_message && (
        <Notice tone={doc.status === 'failed' ? 'danger' : 'warning'} icon={AlertTriangle} className="mx-4 mb-3">
          {doc.error_message}
          {busy && <span className="mt-1 block text-xs text-muted">Local dev without Redis? Set <code className="font-mono">CELERY_TASK_ALWAYS_EAGER=true</code> in backend/.env, then Reprocess.</span>}
        </Notice>
      )}
    </motion.li>
  )
}

/** Shows exactly what the AI will read: the document's chunks with section and page. */
function ChunksDrawer({ doc, onClose }) {
  const { data: chunks, isLoading } = useChunks(doc?.id)
  return (
    <Drawer open={Boolean(doc)} onClose={onClose} eyebrow="Processed text" title={doc?.filename || ''} width="max-w-2xl">
      <p className="mb-5 text-sm text-muted">Each chunk is embedded and searched separately. Evidence quotes always come from these exact texts.</p>
      {isLoading ? <Skeleton className="h-64" /> : (
        <ol className="space-y-3">
          {chunks?.map((c) => (
            <li key={c.id} className="border border-border p-4">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span className="font-mono text-[11px] text-muted">#{c.chunk_index}</span>
                {c.section && <Tag>{c.section}</Tag>}
                {c.page_start && <Tag>p.{c.page_start}{c.page_end && c.page_end !== c.page_start ? `–${c.page_end}` : ''}</Tag>}
              </div>
              <p className="text-sm leading-relaxed whitespace-pre-wrap text-foreground/90">{c.content}</p>
            </li>
          ))}
        </ol>
      )}
    </Drawer>
  )
}

/** One column: reference or existing documents. */
function DocumentColumn({ project, role, docs, onView }) {
  const preset = PRESETS[project.preset]
  const title = role === 'reference' ? preset?.reference : preset?.existing
  const hint = role === 'reference' ? 'What SHOULD exist — requirements are extracted from these.' : 'What DOES exist — evidence is searched in these.'
  return (
    <Panel className="flex flex-col">
      <div className="border-b border-border p-5">
        <Eyebrow>{role}</Eyebrow>
        <h2 className="mt-1 text-lg font-semibold tracking-tight">{title}</h2>
        <p className="mt-1 text-sm text-muted">{hint}</p>
      </div>
      <div className="p-5"><UploadArea projectId={project.id} role={role} /></div>
      {docs.length > 0 && (
        <ul className="border-t border-border">
          <AnimatePresence initial={false}>
            {docs.map((d) => <DocumentRow key={d.id} doc={d} projectId={project.id} onView={onView} />)}
          </AnimatePresence>
        </ul>
      )}
    </Panel>
  )
}

export default function DocumentsStep({ project, onNext }) {
  const { data: documents, isLoading } = useDocuments(project.id)
  const [viewing, setViewing] = useState(null)

  if (isLoading) return <div className="grid gap-4 lg:grid-cols-2"><Skeleton className="h-72" /><Skeleton className="h-72" /></div>

  const docs = documents || []
  const ready = (role) => docs.some((d) => d.role === role && d.status === 'indexed')

  return (
    <div className="space-y-6">
      <div className="grid gap-4 lg:grid-cols-2">
        {['reference', 'existing'].map((role) => (
          <DocumentColumn key={role} project={project} role={role} docs={docs.filter((d) => d.role === role)} onView={setViewing} />
        ))}
      </div>
      {docs.length === 0 && (
        <Empty icon={Upload} title="Start by uploading both sides">
          Atlas compares the two columns: requirements come from the left, evidence from the right.
        </Empty>
      )}
      <div className="flex justify-end">
        <Button icon={ArrowRight} disabled={!ready('reference') || !ready('existing')} onClick={onNext}>
          Next: requirements
        </Button>
      </div>
      <ChunksDrawer doc={viewing} onClose={() => setViewing(null)} />
    </div>
  )
}
