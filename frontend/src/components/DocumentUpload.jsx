// "Understand a document" card — drag-drop / browse / paste-text upload flow
import { useState, useRef } from 'react'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import useAtlasStore from '../store/atlasStore'
import { Button } from '@/components/ui/button'
import { AnimatedProgress } from '@/components/ui/animated-progress'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const STEPS = ['Reading document', 'Breaking into concepts', 'Building your map']

export default function DocumentUpload() {
  const [dragActive, setDragActive] = useState(false)
  const [pasting, setPasting] = useState(false)
  const [pastedText, setPastedText] = useState('')
  const [uploading, setUploading] = useState(false)
  const [stepIndex, setStepIndex] = useState(0)
  const fileInputRef = useRef(null)

  const setCurrentMap   = useAtlasStore(s => s.setCurrentMap)
  const setNodes         = useAtlasStore(s => s.setNodes)
  const setEdges           = useAtlasStore(s => s.setEdges)
  const setRecentMaps       = useAtlasStore(s => s.setRecentMaps)
  const recentMaps            = useAtlasStore(s => s.recentMaps)
  const setSelectedNode         = useAtlasStore(s => s.setSelectedNode)

  function onMapBuilt(map) {
    setCurrentMap(map)
    setNodes(map.nodes)
    setEdges(map.edges)
    setRecentMaps([
      { id: map.id, topic: map.topic, title: map.title, created_at: map.created_at },
      ...recentMaps.filter(m => m.id !== map.id),
    ])
  }

  // Optimistic step progression — the backend does the real work in one request,
  // but showing the three stages as they'd realistically occur keeps the wait legible.
  function runOptimisticSteps() {
    setStepIndex(0)
    const t1 = setTimeout(() => setStepIndex(1), 900)
    const t2 = setTimeout(() => setStepIndex(2), 2200)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }

  async function uploadFile(file) {
    if (uploading) return
    setSelectedNode(null)
    setUploading(true)
    const stopSteps = runOptimisticSteps()
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch(`${API}/documents`, { method: 'POST', body: form })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'Upload failed')
      }
      const map = await res.json()
      onMapBuilt(map)
      toast.success(`Map built from ${file.name}`)
    } catch (err) {
      toast.error(err.message || 'Could not process document')
    } finally {
      stopSteps()
      setUploading(false)
    }
  }

  async function uploadPastedText() {
    const text = pastedText.trim()
    if (!text || uploading) return
    setSelectedNode(null)
    setUploading(true)
    const stopSteps = runOptimisticSteps()
    try {
      const res = await fetch(`${API}/documents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, filename: 'pasted-text' }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'Upload failed')
      }
      const map = await res.json()
      onMapBuilt(map)
      setPastedText('')
      setPasting(false)
      toast.success('Map built from your pasted text')
    } catch (err) {
      toast.error(err.message || 'Could not process document')
    } finally {
      stopSteps()
      setUploading(false)
    }
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragActive(false)
    const file = e.dataTransfer.files?.[0]
    if (file) uploadFile(file)
  }

  const cardStyle = {
    flex: 1, minWidth: 260, maxWidth: 320,
    border: `1.5px dashed ${dragActive ? 'var(--accent)' : 'var(--border)'}`,
    borderRadius: 'var(--radius-panel)',
    background: dragActive ? 'var(--accent-light)' : 'var(--surface)',
    padding: 24,
    display: 'flex', flexDirection: 'column', alignItems: 'center',
    textAlign: 'center', gap: 10,
    transition: 'border-color 0.15s, background 0.15s',
    position: 'relative', overflow: 'hidden',
  }

  return (
    <div style={cardStyle}
      onDragOver={e => { e.preventDefault(); setDragActive(true) }}
      onDragLeave={() => setDragActive(false)}
      onDrop={handleDrop}
    >
      <div style={{
        width: 48, height: 48, borderRadius: '50%',
        background: 'var(--accent-light)', display: 'flex',
        alignItems: 'center', justifyContent: 'center', flexShrink: 0,
      }}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
        </svg>
      </div>

      <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--text)' }}>Understand a document</h3>
      <p style={{ fontSize: 13, color: 'var(--text-muted)', lineHeight: 1.5 }}>
        Upload an SDD, spec, or any .docx / .pdf — get a map grounded ONLY in that document.
      </p>

      {uploading ? (
        <div style={{ width: '100%', marginTop: 8 }}>
          <AnimatedProgress value={((stepIndex + 1) / STEPS.length) * 100} style={{ height: 4, borderRadius: 2 }} />
          <p style={{ fontSize: 12, color: 'var(--accent-text)', marginTop: 10, fontWeight: 500 }}>
            {STEPS[stepIndex]}…
          </p>
        </div>
      ) : pasting ? (
        <div style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 8, marginTop: 4 }}>
          <textarea
            autoFocus
            value={pastedText}
            onChange={e => setPastedText(e.target.value)}
            placeholder="Paste document text here…"
            rows={5}
            style={{
              width: '100%', resize: 'vertical', fontSize: 13, fontFamily: 'inherit',
              border: '1px solid var(--border)', borderRadius: 'var(--radius-btn)',
              padding: 10, outline: 'none', color: 'var(--text)', background: 'var(--surface)',
            }}
          />
          <div style={{ display: 'flex', gap: 8 }}>
            <Button size="sm" variant="ghost" onClick={() => { setPasting(false); setPastedText('') }} style={{ flex: 1 }}>
              Cancel
            </Button>
            <Button size="sm" onClick={uploadPastedText} disabled={!pastedText.trim()} style={{ flex: 1 }}>
              Build map
            </Button>
          </div>
        </div>
      ) : (
        <>
          <Button
            variant="outline"
            onClick={() => fileInputRef.current?.click()}
            style={{ width: '100%', marginTop: 4 }}
          >
            Browse files
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".docx,.pdf,.txt,.md"
            style={{ display: 'none' }}
            onChange={e => { const f = e.target.files?.[0]; if (f) uploadFile(f) }}
          />
          <button
            onClick={() => setPasting(true)}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: 'var(--accent-text)', fontSize: 13, fontFamily: 'inherit',
              textDecoration: 'underline', marginTop: 2,
            }}
          >
            paste text instead
          </button>
        </>
      )}

      {dragActive && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }}
          style={{
            position: 'absolute', inset: 0, display: 'flex',
            alignItems: 'center', justifyContent: 'center',
            background: 'var(--accent-light)', fontSize: 14,
            fontWeight: 600, color: 'var(--accent-text)', pointerEvents: 'none',
          }}
        >
          Drop to upload
        </motion.div>
      )}
    </div>
  )
}
