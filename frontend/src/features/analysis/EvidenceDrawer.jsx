/**
 * Evidence panel for one finding (UI spec §17). Source text and AI interpretation are
 * visually distinct: quotes are serif with a "Source text" label and a verified badge;
 * the model's reasoning is labelled "AI assessment".
 */
import { BadgeCheck, FileText, Quote, Sparkles } from 'lucide-react'
import { Button, Drawer, Eyebrow, Progress, STATUS_HELP, StatusPill, Tag } from '@/components/kit'
import { InvestigationPanel } from '@/features/analysis/Investigation'

/** "sdd.pdf › 4. Auth › p.7". */
export const sourceLabel = (e) => [e.document_filename, e.section, e.page_start ? `p.${e.page_start}` : null].filter(Boolean).join(' › ')

/** Labelled block of AI-written text. */
export function AiText({ label = 'AI assessment', children }) {
  return (
    <div>
      <p className="flex items-center gap-1.5 text-[11px] font-medium tracking-wider text-muted uppercase">
        <Sparkles className="size-3" /> {label}
      </p>
      <p className="mt-1.5 text-sm leading-relaxed">{children}</p>
    </div>
  )
}

/** One verified quote from a source document. */
export function SourceQuote({ evidence, onOpenDocument, compact = false }) {
  return (
    <div className="border-l-2 border-secondary bg-fill px-4 py-3">
      <p className="flex items-center gap-1.5 text-[11px] font-medium tracking-wider text-muted uppercase">
        <Quote className="size-3" /> Source text
        {evidence.verified && (
          <span className="ml-1 inline-flex items-center gap-1 text-success normal-case" title="This exact text was found in the document">
            <BadgeCheck className="size-3" /> verified
          </span>
        )}
      </p>
      <blockquote className={compact ? 'mt-1.5 font-serif text-base leading-snug italic' : 'mt-2 font-serif text-lg leading-snug italic'}>
        &ldquo;{evidence.quote}&rdquo;
      </blockquote>
      <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted">
        <span>{sourceLabel(evidence)}</span>
        {onOpenDocument && (
          <button type="button" onClick={() => onOpenDocument(evidence)} className="inline-flex cursor-pointer items-center gap-1 text-foreground underline-offset-2 hover:underline">
            <FileText className="size-3" /> Open in document
          </button>
        )}
      </div>
    </div>
  )
}

export default function EvidenceDrawer({ finding, projectId, onClose, onOpenDocument }) {
  return (
    <Drawer open={Boolean(finding)} onClose={onClose} eyebrow={finding?.requirement.code} title="Evidence">
      {finding && (
        <div className="space-y-6">
          <section>
            <Eyebrow>Requirement</Eyebrow>
            <p className="mt-2 text-base leading-relaxed">{finding.requirement.text}</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {finding.requirement.section && <Tag>{finding.requirement.section}</Tag>}
              {finding.requirement.source_document && (
                <Tag>from {finding.requirement.source_document}{finding.requirement.source_page ? ` p.${finding.requirement.source_page}` : ''}</Tag>
              )}
            </div>
          </section>

          <section className="flex flex-wrap items-center gap-3">
            <StatusPill status={finding.status} />
            <span className="text-sm text-muted">{STATUS_HELP[finding.status]}</span>
            {finding.confidence != null && (
              <span className="flex items-center gap-2 text-xs text-muted">
                confidence <Progress value={finding.confidence * 100} className="w-16" />
                <span className="font-mono">{Math.round(finding.confidence * 100)}%</span>
              </span>
            )}
            {finding.source === 'cache' && <Tag>reused from previous run</Tag>}
            {finding.source === 'agent' && <Tag>re-checked by agent</Tag>}
          </section>

          <section className="space-y-3">
            <Eyebrow>Matched text ({finding.evidence.length})</Eyebrow>
            {finding.evidence.length
              ? finding.evidence.map((e) => <SourceQuote key={e.id} evidence={e} onOpenDocument={onOpenDocument} />)
              : <p className="text-sm text-muted">No supporting evidence was found in the provided existing documents.</p>}
          </section>

          <section className="space-y-4 border-t border-border pt-5">
            <AiText>{finding.explanation}</AiText>
            {finding.missing_detail && <AiText label="Missing or different">{finding.missing_detail}</AiText>}
            {finding.suggested_action && <AiText label="Suggested action">{finding.suggested_action}</AiText>}
          </section>

          <InvestigationPanel finding={finding} projectId={projectId} />

          <Button variant="outline" size="sm" onClick={onClose}>Back to findings</Button>
        </div>
      )}
    </Drawer>
  )
}
