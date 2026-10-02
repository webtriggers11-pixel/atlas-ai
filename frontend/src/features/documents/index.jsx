/**
 * Document building blocks shared by New Analysis, the analysis Documents tab and the global Documents page:
 * uploader (drag-drop / browse / paste), document row with honest processing state, and a viewer
 * that shows the processed text with evidence quotes highlighted.
 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { AlertTriangle, ClipboardPaste, FileText, RotateCw, Trash2, Upload } from 'lucide-react'
import toast from 'react-hot-toast'
import { api } from '@/lib/api'
import { formatSize } from '@/lib/format'
import { keys, useAction, useChunks } from '@/lib/queries'
import { cn } from '@/lib/utils'
import { Button, Empty, ErrorState, Field, Input, Notice, Skeleton, StatusPill, Tag, Textarea } from '@/components/kit'

const ACCEPT = '.pdf,.docx,.txt,.md'
export const DOC_STATUS_LABEL = { uploaded: 'queued', processing: 'processing', indexed: 'ready', failed: 'failed' }

/** Drag-and-drop / browse upload area, with a "paste text instead" alternative. */
export function DocumentUploader({ projectId, role, label }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)
  const [pasting, setPasting] = useState(false)
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const invalidate = [keys.documents(projectId), keys.project(projectId), keys.allDocuments()]

  const upload = useAction(async (files) => {
    const results = []
    for (const file of files) results.push(await api.uploadFile(projectId, role, file)) // sequential: clear order and errors
    return results
  }, { invalidate, success: (docs) => (docs.length === 1 ? `Added ${docs[0].filename}` : `Added ${docs.length} files`) })

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
      <div className="space-y-3 border border-border bg-background p-4">
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
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); onFiles(e.dataTransfer.files) }}
        className={cn(
          'flex cursor-pointer flex-col items-center gap-2 border border-dashed px-4 py-8 text-center transition-colors',
          dragging ? 'border-secondary bg-secondary/10' : 'border-border hover:border-foreground/30 hover:bg-fill',
        )}
      >
        {upload.isPending ? <RotateCw className="size-5 animate-spin text-secondary" /> : <Upload className={cn('size-5', dragging ? 'text-secondary' : 'text-muted')} />}
        <span className="text-sm font-medium">{upload.isPending ? 'Uploading and processing…' : `Drop ${label || 'documents'} here`}</span>
        <span className="text-xs text-muted">or <span className="underline underline-offset-2">browse files</span> · PDF · DOCX · TXT · MD</span>
      </div>
      <input ref={inputRef} type="file" accept={ACCEPT} multiple hidden onChange={(e) => { onFiles(e.target.files); e.target.value = '' }} />
      <button type="button" onClick={() => setPasting(true)} className="mt-2 inline-flex cursor-pointer items-center gap-1.5 text-xs text-muted hover:text-foreground">
        <ClipboardPaste className="size-3.5" /> or paste text instead
      </button>
    </div>
  )
}

/** One document with type, size, processing state, and retry/remove actions. */
export function DocumentRow({ doc, projectId, onOpen, selected = false }) {
  const invalidate = [keys.documents(projectId), keys.project(projectId), keys.allDocuments()]
  const reprocess = useAction(() => api.reprocessDocument(doc.id), { invalidate, success: 'Processing again' })
  const remove = useAction(() => api.deleteDocument(doc.id), { invalidate, success: 'Document removed' })
  const busy = doc.status === 'uploaded' || doc.status === 'processing'

  return (
    <li className={cn('border-b border-border last:border-b-0', selected && 'bg-fill-strong')}>
      <div className="flex items-center gap-3 px-4 py-3">
        <FileText className="size-4 shrink-0 text-muted" />
        <div className="min-w-0 flex-1">
          {onOpen && doc.status === 'indexed'
            ? <button type="button" onClick={() => onOpen(doc)} className="block max-w-full cursor-pointer truncate text-left text-sm font-medium hover:underline" title={doc.filename}>{doc.filename}</button>
            : <p className="truncate text-sm font-medium" title={doc.filename}>{doc.filename}</p>}
          <p className="mt-0.5 font-mono text-[11px] text-muted">
            {doc.file_type.toUpperCase()} · {formatSize(doc.size_bytes)}
            {doc.status === 'indexed' && <> · {doc.chunk_count} chunks{doc.page_count ? ` · ${doc.page_count} pages` : ''}</>}
          </p>
        </div>
        <StatusPill status={doc.status}>{DOC_STATUS_LABEL[doc.status]}</StatusPill>
        {(doc.status === 'failed' || (busy && doc.error_message)) && (
          <Button variant="ghost" size="icon" aria-label="Retry processing" title="Retry" loading={reprocess.isPending} onClick={() => reprocess.mutate()}>
            <RotateCw className="size-4" />
          </Button>
        )}
        <Button
          variant="ghost" size="icon" aria-label={`Remove ${doc.filename}`} title="Remove" loading={remove.isPending}
          onClick={() => window.confirm(`Remove ${doc.filename}?`) && remove.mutate()}
        >
          <Trash2 className="size-4" />
        </Button>
      </div>
      {doc.error_message && (
        <Notice tone={doc.status === 'failed' ? 'danger' : 'warning'} icon={AlertTriangle} className="mx-4 mb-3">
          {doc.error_message}
          {busy && (
            <span className="mt-1 block text-xs text-muted">
              Running locally without Redis? Set <code className="font-mono">CELERY_TASK_ALWAYS_EAGER=true</code> in backend/.env, restart the API, then Retry.
            </span>
          )}
        </Notice>
      )}
    </li>
  )
}

/** Escape a string for use inside a RegExp. */
const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

/** Chunk text with every evidence quote wrapped in <mark>. */
function Highlighted({ text, quotes }) {
  const parts = useMemo(() => {
    const usable = quotes.filter((q) => q && q.length > 3 && text.includes(q))
    if (!usable.length) return [text]
    const re = new RegExp(`(${usable.map(escapeRe).join('|')})`, 'g')
    return text.split(re)
  }, [text, quotes])
  return parts.map((part, i) =>
    quotes.includes(part)
      ? <mark key={i} className="bg-secondary/30 px-0.5 text-foreground">{part}</mark>
      : <span key={i}>{part}</span>)
}

/**
 * Processed text of one document, chunk by chunk, with evidence quotes highlighted.
 * `doc` = the document; `evidence` = [{ chunk_id, quote }]; `focusChunkId` scrolls that chunk into view.
 */
export function DocumentViewer({ doc, evidence = [], focusChunkId }) {
  const { data: chunks, isLoading, error, refetch } = useChunks(doc?.id)
  const byChunk = useMemo(() => {
    const map = new Map()
    evidence.forEach((e) => map.set(e.chunk_id, [...(map.get(e.chunk_id) || []), e.quote]))
    return map
  }, [evidence])

  useEffect(() => {
    if (!focusChunkId || !chunks) return
    document.getElementById(`chunk-${focusChunkId}`)?.scrollIntoView({ block: 'center' })
  }, [focusChunkId, chunks])

  if (!doc) return <Empty icon={FileText} title="Select a document">Choose a document on the left to read its processed text.</Empty>
  if (isLoading) return <Skeleton className="h-96" />
  if (error) return <ErrorState error={error} onRetry={refetch} />

  const highlighted = chunks.filter((c) => byChunk.has(c.id)).length
  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-2 text-xs text-muted">
        <span className="font-medium text-foreground">{doc.filename}</span>
        <Tag>{doc.role}</Tag>
        <span>{chunks.length} chunks</span>
        {highlighted > 0 && <span className="text-secondary">· {highlighted} with cited evidence (highlighted)</span>}
      </div>
      <ol className="space-y-2">
        {chunks.map((c) => (
          <li
            key={c.id}
            id={`chunk-${c.id}`}
            className={cn('border p-4', c.id === focusChunkId ? 'border-secondary' : byChunk.has(c.id) ? 'border-secondary/40' : 'border-border')}
          >
            <div className="mb-2 flex flex-wrap items-center gap-2">
              <span className="font-mono text-[11px] text-muted">#{c.chunk_index}</span>
              {c.section && <Tag>{c.section}</Tag>}
              {c.page_start && <Tag>p.{c.page_start}{c.page_end && c.page_end !== c.page_start ? `–${c.page_end}` : ''}</Tag>}
            </div>
            <p className="text-sm leading-relaxed whitespace-pre-wrap text-foreground/90">
              <Highlighted text={c.content} quotes={byChunk.get(c.id) || []} />
            </p>
          </li>
        ))}
      </ol>
    </div>
  )
}
