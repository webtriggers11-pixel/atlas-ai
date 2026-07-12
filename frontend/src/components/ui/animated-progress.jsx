// Magic UI animated progress bar. `value` (0-100) renders a determinate fill;
// omitting it renders an indeterminate sliding bar for open-ended waits.
import { motion } from 'framer-motion'

export function AnimatedProgress({ value, className, style }) {
  const indeterminate = value == null

  return (
    <div
      className={className}
      style={{ height: 2, width: '100%', background: 'var(--accent-light)', overflow: 'hidden', ...style }}
    >
      {indeterminate ? (
        <motion.div
          style={{ height: '100%', width: '35%', background: 'var(--accent)' }}
          animate={{ x: ['-100%', '340%'] }}
          transition={{ duration: 1.1, repeat: Infinity, ease: 'easeInOut' }}
        />
      ) : (
        <motion.div
          style={{ height: '100%', background: 'var(--accent)' }}
          animate={{ width: `${Math.max(0, Math.min(100, value))}%` }}
          transition={{ duration: 0.3, ease: 'easeOut' }}
        />
      )}
    </div>
  )
}
