import { cn } from '@/lib/utils'

// Magic UI shimmer — a light sweep across a muted block, replacing the plain opacity pulse.
// Pure CSS (background-position keyframe), so it adds no JS bundle weight.
function Skeleton({ className, style, ...props }) {
  return (
    <div
      className={cn('shimmer', className)}
      style={{ borderRadius: 6, background: '#F4F4F5', ...style }}
      {...props}
    />
  )
}

export { Skeleton }
