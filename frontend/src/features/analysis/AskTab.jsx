/**
 * Ask — question answering over one analysis (Phase 9, tool calling).
 * Every answer shows which read-only tools the AI used and the sources it read,
 * and sources open the exact document passage or finding.
 */
import { useEffect, useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { ArrowUp, ChevronDown, FileText, Loader2, MessageSquare, Sparkles, Wrench } from 'lucide-react'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'
import { Button, Empty, Panel, StatusPill, Textarea } from '@/components/kit'

const SUGGESTIONS = {
  spec_coverage: [
    'Which requirements are missing?',
    'Summarise the conflicts and what to do about them.',
    'What do the documents say about authentication?',
  ],
  resume_jd: [
    'What are my biggest gaps for this job?',
    'Which required skills are fully covered, with proof?',
    'What should I add to my resume first?',
  ],
}

const TOOL_LABELS = {
  get_overview: 'Read the analysis overview',
  list_findings: 'Listed findings',
  get_requirement: 'Opened a requirement',
  search_documents: 'Searched the documents',
  get_chunk: 'Read a passage',
}

/** Tiny, safe markdown: **bold**, bullet lines, line breaks — rendered as React nodes (no innerHTML). */
function Markdownish({ text }) {
  const lines = text.split('\n')
  const bold = (line, key) => line.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') ? <strong key={`${key}-${i}`}>{part.slice(2, -2)}</strong> : part)
  return (
    <div className="space-y-1.5 text-sm leading-relaxed">
      {lines.map((line, i) => {
        const trimmed = line.trim()
        if (!trimmed) return null
        if (/^[-*•]\s+/.test(trimmed)) {
          return <p key={i} className="flex gap-2 pl-1"><span className="text-secondary">•</span><span>{bold(trimmed.replace(/^[-*•]\s+/, ''), i)}</span></p>
        }
        return <p key={i}>{bold(trimmed, i)}</p>
      })}
    </div>
  )
}

/** Collapsible list of the tool calls behind an answer. */
function Steps({ steps }) {
  const [open, setOpen] = useState(false)
  if (!steps.length) return null
  return (
    <div className="mt-3">
      <button type="button" onClick={() => setOpen((o) => !o)} className="inline-flex cursor-pointer items-center gap-1.5 text-xs text-muted hover:text-foreground">
        <Wrench className="size-3" /> Used {steps.length} tool{steps.length === 1 ? '' : 's'}
        <ChevronDown className={cn('size-3 transition-transform', open && 'rotate-180')} />
      </button>
      {open && (
        <ol className="mt-2 space-y-1 border-l border-border pl-3 font-mono text-[11px] text-muted">
          {steps.map((s, i) => (
            <li key={i} className={s.ok ? '' : 'text-danger'}>
              {TOOL_LABELS[s.tool] || s.tool}
              {s.arguments && Object.keys(s.arguments).length > 0 && <> · {Object.entries(s.arguments).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(', ')}</>}
              {' → '}{s.summary}
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}

/** One exchange: the user's question and the assistant's answer with steps and sources. */
function Message({ message, onOpenChunk, onOpenRequirement }) {
  if (message.role === 'user') {
    return <div className="ml-auto max-w-[85%] border border-border bg-surface-2 px-4 py-2.5 text-sm">{message.content}</div>
  }
  return (
    <Panel className="max-w-[92%] p-4">
      <p className="mb-2 flex items-center gap-1.5 text-[11px] font-medium tracking-wider text-muted uppercase"><Sparkles className="size-3" /> AI answer</p>
      <Markdownish text={message.content} />
      {message.sources?.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {message.sources.slice(0, 8).map((s) => (
            <button
              key={s.id} type="button"
              onClick={() => (s.kind === 'chunk' ? onOpenChunk(s) : onOpenRequirement(s.id))}
              className="inline-flex cursor-pointer items-center gap-1 border border-border px-2 py-0.5 text-[11px] text-muted hover:border-secondary hover:text-foreground"
              title={s.kind === 'chunk' ? 'Open this passage in the document' : 'Open this finding'}
            >
              {s.kind === 'chunk'
                ? <><FileText className="size-3" />{s.document}{s.section ? ` › ${s.section}` : ''}{s.page ? ` › p.${s.page}` : ''}</>
                : <>{s.id}{s.status && <StatusPill status={s.status} className="ml-1 px-1 py-0" />}</>}
            </button>
          ))}
        </div>
      )}
      <Steps steps={message.steps || []} />
    </Panel>
  )
}

export default function AskTab({ project, findings, onOpenChunk, onOpenFinding }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const endRef = useRef(null)
  const ask = useMutation({
    mutationFn: ({ message, history }) => api.chat(project.id, message, history),
    onSuccess: (data) => setMessages((m) => [...m, { role: 'assistant', content: data.answer, steps: data.steps, sources: data.sources }]),
    onError: (err) => setMessages((m) => [...m, { role: 'assistant', content: `Sorry — ${err.message}`, steps: [], sources: [] }]),
  })
  useEffect(() => endRef.current?.scrollIntoView({ block: 'end' }), [messages, ask.isPending])

  const send = (text) => {
    const message = (text ?? input).trim()
    if (!message || ask.isPending) return
    const history = messages.map(({ role, content }) => ({ role, content }))
    setMessages((m) => [...m, { role: 'user', content: message }])
    setInput('')
    ask.mutate({ message, history })
  }
  const openRequirement = (code) => {
    const finding = findings.find((f) => f.requirement.code === code)
    if (finding) onOpenFinding(finding)
  }

  return (
    <div className="space-y-4">
      <Panel className="p-4 text-sm text-muted">
        Ask questions about this analysis. The AI can only <span className="text-foreground">read</span> this analysis —
        its documents, requirements and findings — and shows the tools and sources behind every answer.
      </Panel>

      <div className="min-h-[18rem] space-y-3">
        {messages.length === 0 ? (
          <Empty icon={MessageSquare} title="Ask anything about this analysis">
            <div className="mt-3 flex flex-col gap-2">
              {(SUGGESTIONS[project.preset] || SUGGESTIONS.spec_coverage).map((q) => (
                <button key={q} type="button" onClick={() => send(q)}
                  className="cursor-pointer border border-border px-3 py-2 text-left text-sm text-foreground hover:border-secondary">
                  {q}
                </button>
              ))}
            </div>
          </Empty>
        ) : messages.map((m, i) => (
          <Message key={i} message={m} onOpenChunk={onOpenChunk} onOpenRequirement={openRequirement} />
        ))}
        {ask.isPending && (
          <p className="flex items-center gap-2 text-sm text-muted"><Loader2 className="size-4 animate-spin" /> Looking things up…</p>
        )}
        <div ref={endRef} />
      </div>

      <form className="sticky bottom-4 flex items-end gap-2 border border-border bg-background p-2" onSubmit={(e) => { e.preventDefault(); send() }}>
        <Textarea
          value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about requirements, gaps or evidence…"
          className="min-h-10 flex-1 resize-none border-0 bg-transparent" rows={1} maxLength={2000}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
        />
        <Button type="submit" size="icon" aria-label="Send" disabled={!input.trim()} loading={ask.isPending}><ArrowUp className="size-4" /></Button>
      </form>
    </div>
  )
}
