/**
 * Documents inside an analysis (UI spec §18, §20): reference vs existing groups on the left,
 * the processed text of the selected document on the right with cited evidence highlighted.
 */
import { useMemo, useState } from 'react'
import { Plus } from 'lucide-react'
import { analysisType } from '@/lib/analysisTypes'
import { Button, Eyebrow, Panel } from '@/components/kit'
import { DocumentRow, DocumentUploader, DocumentViewer } from '@/features/documents'

export default function DocumentsTab({ project, documents, findings, selectedDocId, focusChunkId, onSelect }) {
  const [adding, setAdding] = useState(null)   // 'reference' | 'existing' | null
  const type = analysisType(project.preset)
  const selected = documents.find((d) => d.id === selectedDocId) || documents.find((d) => d.status === 'indexed')
  const evidence = useMemo(
    () => findings.flatMap((f) => f.evidence).filter((e) => e.document_id === selected?.id),
    [findings, selected],
  )

  return (
    <div className="grid gap-4 lg:grid-cols-[22rem_1fr]">
      <div className="space-y-4">
        {['reference', 'existing'].map((role) => {
          const docs = documents.filter((d) => d.role === role)
          return (
            <Panel key={role}>
              <div className="flex items-center justify-between gap-2 border-b border-border px-4 py-3">
                <div>
                  <Eyebrow>{role}</Eyebrow>
                  <p className="text-sm font-medium">{type[role].title}</p>
                </div>
                <Button variant="ghost" size="sm" icon={Plus} onClick={() => setAdding(adding === role ? null : role)}>Add</Button>
              </div>
              {adding === role && <div className="border-b border-border p-4"><DocumentUploader projectId={project.id} role={role} /></div>}
              {docs.length ? (
                <ul>
                  {docs.map((d) => (
                    <DocumentRow key={d.id} doc={d} projectId={project.id} selected={d.id === selected?.id} onOpen={(doc) => onSelect(doc.id)} />
                  ))}
                </ul>
              ) : <p className="px-4 py-4 text-sm text-muted">No {role} documents.</p>}
            </Panel>
          )
        })}
      </div>
      <Panel className="min-w-0 p-5">
        <DocumentViewer doc={selected} evidence={evidence} focusChunkId={focusChunkId} />
      </Panel>
    </div>
  )
}
