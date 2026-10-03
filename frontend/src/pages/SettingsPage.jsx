/**
 * Settings (UI spec §23) — theme, plus a read-only view of the server's storage limits.
 * (The AI provider section is hidden for now; it is commented out below.)
 * Provider keys live in backend environment variables and are never shown.
 */
import { CheckCircle2, CircleAlert, ExternalLink, Moon, Sun } from 'lucide-react'
import { API_BASE } from '@/lib/api'
import { cn } from '@/lib/utils'
import { useSettings } from '@/lib/queries'
import { ErrorState, Panel, Skeleton, Tag } from '@/components/kit'
import { PageBody, PageHeader, useThemeMode } from '@/components/layout'

// eslint-disable-next-line no-unused-vars -- GitHub link hidden for now (see About section)
const REPO = 'https://github.com/webtriggers11-pixel/atlas-ai'

/** Titled settings block. */
function Section({ title, description, children }) {
  return (
    <Panel className="grid gap-4 p-5 md:grid-cols-[14rem_1fr]">
      <div>
        <h2 className="font-semibold">{title}</h2>
        {description && <p className="mt-1 text-sm text-muted">{description}</p>}
      </div>
      <div className="min-w-0">{children}</div>
    </Panel>
  )
}

/** Label/value row. */
const Row = ({ label, children }) => (
  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border py-2.5 text-sm last:border-b-0">
    <span className="text-muted">{label}</span>
    <span className="font-mono text-xs">{children}</span>
  </div>
)

export default function SettingsPage() {
  const { mode, setMode } = useThemeMode()
  const { data: s, isLoading, error, refetch } = useSettings()

  return (
    <>
      <PageHeader title="Settings" />
      <PageBody className="max-w-5xl space-y-4">
        <Section title="General" description="Saved in this browser.">
          <div className="flex gap-px border border-border bg-border">
            {[['dark', Moon], ['light', Sun]].map(([m, Icon]) => (
              <button key={m} type="button" onClick={() => setMode(m)} aria-pressed={mode === m}
                className={cn('flex flex-1 cursor-pointer items-center justify-center gap-2 py-2.5 text-sm capitalize', mode === m ? 'bg-surface font-semibold' : 'bg-background text-muted hover:text-foreground')}>
                <Icon className="size-4" /> {m}
              </button>
            ))}
          </div>
        </Section>

        {error ? <ErrorState error={error} onRetry={refetch} /> : isLoading ? <Skeleton className="h-64" /> : (
          <>
            {/* Hidden for now — server AI configuration (providers, models, prompt versions)
            <Section title="AI" description="Configured on the server through environment variables. Keys are never sent to the browser.">
              <div className="space-y-2">
                {s.providers.map((p) => (
                  <div key={p.name} className="flex flex-wrap items-center justify-between gap-2 border border-border px-3 py-2.5">
                    <span className="flex items-center gap-2 text-sm font-medium capitalize">
                      {p.name === 'ollama' ? <CircleAlert className="size-4 text-muted" />
                        : p.configured ? <CheckCircle2 className="size-4 text-success" /> : <CircleAlert className="size-4 text-muted" />}
                      {p.name}
                      {p.name === s.default_provider && <Tag>default</Tag>}
                    </span>
                    <span className="font-mono text-xs text-muted">
                      {p.name === 'ollama' ? `local · no key needed · ${p.model}` : p.configured ? p.model : 'no API key set'}
                    </span>
                  </div>
                ))}
              </div>
              <div className="mt-4">
                <Row label="Embedding model">{s.embedding_model}</Row>
                <Row label="Retrieval">{s.retrieval_mode}</Row>
                <Row label="Background jobs">{s.background_jobs === 'inline' ? 'inline (no worker)' : 'Celery worker'}</Row>
                {Object.entries(s.prompt_versions).map(([task, v]) => <Row key={task} label={`Prompt · ${task.replaceAll('_', ' ')}`}>{v}</Row>)}
              </div>
            </Section>
            */}

            <Section title="Storage" description="Upload limits enforced by the server.">
              <Row label="Max file size">{s.max_upload_mb} MB</Row>
              <Row label="Max PDF pages">{s.max_pdf_pages}</Row>
              <Row label="Accepted types">PDF · DOCX · TXT · MD</Row>
            </Section>

            <Section title="About">
              <Row label="Version">{s.version}</Row>
              <Row label="API">{API_BASE}</Row>
              {/* Hidden for now — source code link
              <Row label="Source code">
                <a href={REPO} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 hover:underline">GitHub <ExternalLink className="size-3" /></a>
              </Row>
              */}
              <Row label="License">not yet chosen</Row>
            </Section>
          </>
        )}
      </PageBody>
    </>
  )
}
