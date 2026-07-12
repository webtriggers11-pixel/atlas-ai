import * as React from 'react'
import { cn } from '@/lib/utils'

const Input = React.forwardRef(({ className, type, ...props }, ref) => {
  return (
    <input
      type={type}
      className={cn(
        'flex h-[38px] w-full border border-border bg-card px-3 py-2 text-sm text-foreground',
        'placeholder:text-muted-foreground outline-none transition-[border-color,box-shadow]',
        'focus:border-primary focus:shadow-[0_0_0_3px_var(--accent-light)]',
        'disabled:cursor-not-allowed disabled:opacity-50',
        className
      )}
      style={{ fontFamily: 'inherit', borderRadius: 'var(--radius-btn)' }}
      ref={ref}
      {...props}
    />
  )
})
Input.displayName = 'Input'

export { Input }
