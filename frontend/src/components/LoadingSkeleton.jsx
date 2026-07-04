// Animated skeleton shown while Ollama is generating the concept map
import { motion } from 'framer-motion'

// Root center point and child positions inside a 500×470 container
const ROOT = { x: 250, y: 235 }

const CHILDREN = [
  { cx: 390, cy: 235 },   // right
  { cx: 320, cy: 356 },   // bottom-right
  { cx: 180, cy: 356 },   // bottom-left
  { cx: 110, cy: 235 },   // left
  { cx: 180, cy: 114 },   // top-left
  { cx: 320, cy: 114 },   // top-right
]

const pulse = {
  animate: { opacity: [0.4, 0.85, 0.4] },
  transition: { duration: 1.3, repeat: Infinity, ease: 'easeInOut' },
}

export default function LoadingSkeleton() {
  return (
    <div style={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
    }}>
      {/* Fixed-size stage so SVG lines and node divs share the same coordinate space */}
      <div style={{ position: 'relative', width: 500, height: 470 }}>

        {/* SVG lines from root center to each child center — drawn behind the nodes */}
        <svg
          width="500" height="470"
          style={{ position: 'absolute', top: 0, left: 0, pointerEvents: 'none' }}
        >
          {CHILDREN.map((c, i) => (
            <line
              key={i}
              x1={ROOT.x} y1={ROOT.y}
              x2={c.cx}   y2={c.cy}
              stroke="#E4E4E7"
              strokeWidth="1"
            />
          ))}
        </svg>

        {/* Root skeleton */}
        <motion.div
          {...pulse}
          transition={{ ...pulse.transition }}
          style={{
            position: 'absolute',
            left: ROOT.x - 100,   // center the 200px-wide box
            top:  ROOT.y - 32,    // center the 64px-tall box
            width: 200, height: 64,
            borderRadius: 10,
            background: '#E4E4E7',
          }}
        />

        {/* Child skeletons */}
        {CHILDREN.map((c, i) => (
          <motion.div
            key={i}
            animate={pulse.animate}
            transition={{ ...pulse.transition, delay: i * 0.15 }}
            style={{
              position: 'absolute',
              left: c.cx - 90,    // center the 180px-wide box
              top:  c.cy - 30,    // center the 60px-tall box
              width: 180, height: 60,
              borderRadius: 10,
              background: '#F4F4F5',
            }}
          />
        ))}
      </div>

      <p style={{ marginTop: 32, fontSize: 13, color: 'var(--text-muted)' }}>
        Building your concept map…
      </p>
    </div>
  )
}
