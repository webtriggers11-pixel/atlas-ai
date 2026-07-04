import { useState } from 'react'
import useAtlasStore from '../store/atlasStore'

/**
 * Persistent top bar with the topic search field.
 * Enter / button → generateMap; shows error banner when store.error is set.
 */
export default function TopicInput() {
  const [topic, setTopic]   = useState('')
  const isGenerating        = useAtlasStore(s => s.isGenerating)
  const error               = useAtlasStore(s => s.error)
  const generateMap         = useAtlasStore(s => s.generateMap)
  const clearError          = useAtlasStore(s => s.clearError)

  const handleSubmit = e => {
    e.preventDefault()
    if (topic.trim() && !isGenerating) {
      generateMap(topic)
      setTopic('')
    }
  }

  return (
    <div
      className="flex-shrink-0 z-20"
      style={{ background: '#1f2937', borderBottom: '1px solid #374151' }}
    >
      <form onSubmit={handleSubmit} className="flex items-center gap-3 px-4 py-3">
        {/* App name */}
        <span className="text-indigo-400 font-bold text-sm tracking-wide flex-shrink-0">
          Idea Atlas
        </span>

        {/* Input */}
        <input
          type="text"
          value={topic}
          onChange={e => { setTopic(e.target.value); clearError() }}
          placeholder="Type a topic to explore… (e.g. quantum computing)"
          disabled={isGenerating}
          className="flex-1 bg-gray-900 border border-gray-600 rounded-lg px-4 py-2 text-sm text-gray-100 placeholder-gray-500 outline-none focus:border-indigo-500 transition-colors"
          style={{ minWidth: 0 }}
        />

        {/* Generate button */}
        <button
          type="submit"
          disabled={!topic.trim() || isGenerating}
          className="px-4 py-2 rounded-lg text-sm font-medium flex-shrink-0 transition-colors"
          style={{
            background: !topic.trim() || isGenerating ? '#374151' : '#6366f1',
            color:      !topic.trim() || isGenerating ? '#6b7280' : '#fff',
          }}
        >
          {isGenerating ? (
            <span className="flex items-center gap-2">
              <span className="inline-block w-3 h-3 rounded-full border-2 border-white border-t-transparent animate-spin" />
              Generating…
            </span>
          ) : 'Generate'}
        </button>
      </form>

      {/* Inline error banner */}
      {error && (
        <div className="px-4 pb-3 flex items-center gap-2">
          <span className="text-red-400 text-xs flex-1">{error}</span>
          <button onClick={clearError} className="text-gray-500 hover:text-white text-xs">✕</button>
        </div>
      )}

      {/* Loading skeleton hint */}
      {isGenerating && (
        <div className="px-4 pb-2">
          <p className="text-xs text-gray-500 animate-pulse">
            Asking the AI — this takes a few seconds…
          </p>
        </div>
      )}
    </div>
  )
}
