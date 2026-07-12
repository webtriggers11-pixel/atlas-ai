// Magic UI text-reveal — words blur/fade in in sequence. Headings only; never wrap body copy.
import { motion } from 'framer-motion'

export function TextReveal({ as: Tag = 'span', text, style, className, delayStart = 0 }) {
  const words = text.split(' ')
  return (
    <Tag className={className} style={{ ...style, display: 'block' }}>
      {words.map((word, i) => (
        <motion.span
          key={i}
          initial={{ opacity: 0, filter: 'blur(6px)', y: 6 }}
          animate={{ opacity: 1, filter: 'blur(0px)', y: 0 }}
          transition={{ duration: 0.35, delay: delayStart + i * 0.03, ease: 'easeOut' }}
          style={{ display: 'inline-block', marginRight: '0.25em' }}
        >
          {word}
        </motion.span>
      ))}
    </Tag>
  )
}
