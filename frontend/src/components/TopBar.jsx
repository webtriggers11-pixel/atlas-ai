// Top navigation bar — logo, topic input, generate button
import { useState, useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import toast from 'react-hot-toast'
import useAtlasStore from '../store/atlasStore'

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function TopBar() {
  const [topic, setTopic] = useState('')
  const [focused, setFocused] = useState(false)
  const inputRef = useRef(null)

  const isGenerating  = useAtlasStore(s => s.isGenerating)
  const depth         = useAtlasStore(s => s.depth)
  const setCurrentMap = useAtlasStore(s => s.setCurrentMap)
  const setNodes      = useAtlasStore(s => s.setNodes)
  const setEdges      = useAtlasStore(s => s.setEdges)
  const setIsGenerating = useAtlasStore(s => s.setIsGenerating)
  const setRecentMaps   = useAtlasStore(s => s.setRecentMaps)
  const recentMaps      = useAtlasStore(s => s.recentMaps)
  const setSelectedNode = useAtlasStore(s => s.setSelectedNode)

  // Press "/" anywhere to focus the input
  useEffect(() => {
    const onKey = (e) => {
      if (e.key === '/' && document.activeElement !== inputRef.current) {
        e.preventDefault()
        inputRef.current?.focus()
      }
      if (e.key === 'Escape') inputRef.current?.blur()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  async function generate(topicOverride) {
    const t = (topicOverride ?? topic).trim()
    if (!t || isGenerating) return
    setIsGenerating(true)
    setSelectedNode(null)
    try {
      const res = await fetch(`${API}/maps`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: t, depth }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'Request failed')
      }
      const map = await res.json()
      setCurrentMap(map)
      setNodes(map.nodes)
      setEdges(map.edges)
      setRecentMaps([
        { id: map.id, topic: map.topic, title: map.title, created_at: map.created_at },
        ...recentMaps.filter(m => m.id !== map.id),
      ])
      setTopic('')
    } catch (err) {
      toast.error('Could not generate — try again')
    } finally {
      setIsGenerating(false)
    }
  }

  // Exposed so EmptyState chips can call it
  TopBar.generate = generate

  return (
    <div style={{
      height: 56,
      background: 'var(--surface)',
      borderBottom: '1px solid var(--border)',
      display: 'flex',
      alignItems: 'center',
      padding: '0 20px',
      gap: 16,
      flexShrink: 0,
      zIndex: 20,
    }}>

      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
        <div style={{
          width: 8, height: 8,
          background: 'var(--accent)',
          borderRadius: 3,
        }} />
        <span style={{ fontSize: 18, fontWeight: 600, color: 'var(--text)', whiteSpace: 'nowrap' }}>
          Idea Atlas
        </span>
      </div>

      {/* Search input */}
      <div style={{ flex: 1, maxWidth: 480, margin: '0 auto', position: 'relative' }}>
        {/* Search icon */}
        <svg
          width="14" height="14" viewBox="0 0 24 24" fill="none"
          stroke="var(--text-muted)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
          style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }}
        >
          <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>

        <input
          ref={inputRef}
          type="text"
          value={topic}
          onChange={e => setTopic(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && generate()}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          placeholder="Explore any topic..."
          disabled={isGenerating}
          style={{
            width: '100%',
            height: 38,
            paddingLeft: 36,
            paddingRight: topic ? 12 : 100,
            border: `1px solid ${focused ? 'var(--accent)' : 'var(--border)'}`,
            borderRadius: 'var(--radius-btn)',
            fontSize: 14,
            fontFamily: 'inherit',
            background: 'var(--surface)',
            color: 'var(--text)',
            outline: 'none',
            boxShadow: focused ? '0 0 0 3px var(--accent-light)' : 'none',
            transition: 'border-color 0.15s, box-shadow 0.15s',
          }}
        />

        {/* Spinner when generating */}
        {isGenerating && (
          <div style={{
            position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
            width: 14, height: 14,
            border: '2px solid var(--accent-light)',
            borderTopColor: 'var(--accent)',
            borderRadius: '50%',
            animation: 'spin 0.7s linear infinite',
          }} />
        )}

        {/* Keyboard hint */}
        {!topic && !focused && !isGenerating && (
          <span style={{
            position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
            fontSize: 11, color: 'var(--text-muted)', pointerEvents: 'none',
          }}>
            Press / to focus
          </span>
        )}
      </div>

      {/* Generate button */}
      <motion.button
        whileTap={{ scale: 0.97 }}
        onClick={() => generate()}
        disabled={!topic.trim() || isGenerating}
        style={{
          height: 38,
          padding: '0 18px',
          background: 'var(--accent)',
          color: '#fff',
          border: 'none',
          borderRadius: 'var(--radius-btn)',
          fontSize: 14,
          fontWeight: 500,
          fontFamily: 'inherit',
          cursor: !topic.trim() || isGenerating ? 'not-allowed' : 'pointer',
          opacity: !topic.trim() || isGenerating ? 0.4 : 1,
          flexShrink: 0,
          transition: 'background 0.15s, opacity 0.15s',
        }}
        onMouseEnter={e => { if (topic.trim() && !isGenerating) e.target.style.background = '#6D28D9' }}
        onMouseLeave={e => { e.target.style.background = 'var(--accent)' }}
      >
        Generate
      </motion.button>

      <style>{`@keyframes spin { to { transform: translateY(-50%) rotate(360deg); } }`}</style>
    </div>
  )
}
