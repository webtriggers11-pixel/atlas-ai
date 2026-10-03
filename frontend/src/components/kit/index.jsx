/**
 * UI kit for the V2 app — Ink & Cobalt look: rounded hairline panels, calm sentence-case
 * buttons, small uppercase micro-labels, and the five status colors.
 */
import { forwardRef, useEffect } from 'react'
import { createPortal } from 'react-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { AlertTriangle, CheckCircle2, CircleAlert, CircleHelp, Contrast, Loader2, RotateCw, X } from 'lucide-react'
import { cn } from '@/lib/utils'

// ── Buttons ───────────────────────────────────────────────────────────────────

const buttonVariants = {
  primary: 'bg-primary text-primary-foreground shadow-sm hover:brightness-110 active:brightness-95',
  outline: 'border border-border bg-surface text-foreground hover:bg-surface-2',
  accent: 'bg-accent text-accent-foreground shadow-sm hover:brightness-110 active:brightness-95',
  ghost: 'text-muted hover:bg-fill-strong hover:text-foreground',
  danger: 'border border-danger/40 text-danger hover:bg-danger/10',
}
const buttonSizes = {
  sm: 'h-8 px-3 text-xs',
  md: 'h-10 px-4 text-sm',
  lg: 'h-12 px-6 text-base',
  icon: 'size-9 justify-center',
}

/** Button. `loading` swaps the icon for a spinner and disables the button. */
export const Button = forwardRef(function Button(
  { variant = 'primary', size = 'md', loading = false, icon: Icon, className, children, disabled, ...props }, ref,
) {
  return (
    <button
      ref={ref}
      type="button"
      disabled={disabled || loading}
      className={cn(
        'inline-flex shrink-0 cursor-pointer items-center gap-2 rounded-lg font-medium transition-[background-color,filter,color]',
        'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-secondary disabled:cursor-not-allowed disabled:opacity-45',
        buttonVariants[variant], buttonSizes[size], className,
      )}
      {...props}
    >
      {loading ? <Loader2 className="size-4 animate-spin" /> : Icon ? <Icon className="size-4" /> : null}
      {children}
    </button>
  )
})

// ── Surfaces & text ───────────────────────────────────────────────────────────

/** Hairline-bordered surface — the basic card. */
export function Panel({ className, children, ...props }) {
  return <div className={cn('rounded-xl border border-border bg-surface', className)} {...props}>{children}</div>
}

/** Small uppercase label used above titles ("eyebrow"). */
export function Eyebrow({ className, children }) {
  return <p className={cn('text-[11px] font-medium tracking-[0.2em] text-secondary uppercase', className)}>{children}</p>
}

/** Neutral tag — presets, sections, origins. */
export function Tag({ className, children }) {
  return (
    <span className={cn('inline-flex items-center gap-1 rounded-md border border-border px-2 py-0.5 font-mono text-[10px] tracking-wide text-muted uppercase', className)}>
      {children}
    </span>
  )
}

// ── Status ────────────────────────────────────────────────────────────────────

const STATUS_STYLES = {
  covered: 'text-covered border-covered/40 bg-covered/10',
  partial: 'text-partial border-partial/40 bg-partial/10',
  missing: 'text-missing border-missing/40 bg-missing/10',
  conflict: 'text-conflict border-conflict/40 bg-conflict/10',
  unclear: 'text-unclear border-unclear/40 bg-unclear/10',
  indexed: 'text-success border-success/40 bg-success/10',
  completed: 'text-success border-success/40 bg-success/10',
  approved: 'text-success border-success/40 bg-success/10',
  failed: 'text-danger border-danger/40 bg-danger/10',
  rejected: 'text-muted border-border bg-fill',
  draft: 'text-secondary border-secondary/40 bg-secondary/10',
  uploaded: 'text-warning border-warning/40 bg-warning/10',
  processing: 'text-warning border-warning/40 bg-warning/10',
  queued: 'text-warning border-warning/40 bg-warning/10',
  running: 'text-warning border-warning/40 bg-warning/10',
}
const PULSING = new Set(['uploaded', 'processing', 'queued', 'running'])

// Finding statuses get a distinct icon as well as a color — never rely on color alone
export const STATUS_ICONS = {
  covered: CheckCircle2,
  partial: Contrast,
  missing: CircleAlert,
  conflict: AlertTriangle,
  unclear: CircleHelp,
}

/** Colored status label (icon for finding statuses, dot otherwise); in-progress statuses pulse. */
export function StatusPill({ status, className, children }) {
  const Icon = STATUS_ICONS[status]
  return (
    <span className={cn(
      'inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 font-mono text-[10px] font-medium tracking-wider whitespace-nowrap uppercase',
      STATUS_STYLES[status] || STATUS_STYLES.unclear, className,
    )}>
      {Icon
        ? <Icon className="size-3" aria-hidden />
        : <span className={cn('size-1.5 rounded-full bg-current', PULSING.has(status) && 'animate-pulse')} />}
      {children || status}
    </span>
  )
}

export const FINDING_STATUSES = ['covered', 'partial', 'missing', 'conflict', 'unclear']

export const STATUS_HELP = {
  covered: 'Supported by the existing documents',
  partial: 'Partly supported — a required detail was not found or is vaguer',
  missing: 'No supporting evidence found in the existing documents',
  conflict: 'The existing documents state something different',
  unclear: 'Related text found, but it needs a human decision',
}

// ── Form fields ───────────────────────────────────────────────────────────────

const fieldClass =
  'w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted/70 ' +
  'focus:border-primary/60 focus:ring-2 focus:ring-primary/15 focus:outline-none disabled:opacity-60'

export const Input = forwardRef(function Input({ className, ...props }, ref) {
  return <input ref={ref} className={cn(fieldClass, 'h-10', className)} {...props} />
})

export const Textarea = forwardRef(function Textarea({ className, ...props }, ref) {
  return <textarea ref={ref} className={cn(fieldClass, 'min-h-24 resize-y leading-relaxed', className)} {...props} />
})

/** Label + control + optional hint. */
export function Field({ label, hint, children }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-[11px] font-medium tracking-wider text-muted uppercase">{label}</span>
      {children}
      {hint && <span className="block text-xs text-muted">{hint}</span>}
    </label>
  )
}

// ── Feedback ──────────────────────────────────────────────────────────────────

/** Thin progress bar; `value` is 0–100. */
export function Progress({ value, className, barClassName }) {
  return (
    <div className={cn('h-1.5 w-full overflow-hidden bg-fill-strong', className)}>
      <motion.div
        className={cn('h-full bg-secondary', barClassName)}
        initial={false}
        animate={{ width: `${Math.max(0, Math.min(100, value))}%` }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      />
    </div>
  )
}

/** Placeholder shown while data loads. */
export function Skeleton({ className }) {
  return <div className={cn('shimmer bg-fill', className)} />
}

/** Centered empty-state block with an icon, a title, text and an optional action. */
export function Empty({ icon: Icon, title, children, action, className }) {
  return (
    <div className={cn('flex flex-col items-center justify-center gap-3 border border-dashed border-border px-6 py-12 text-center', className)}>
      {Icon && <Icon className="size-6 text-muted" />}
      <p className="font-medium">{title}</p>
      {children && <div className="max-w-md text-sm text-muted">{children}</div>}
      {action}
    </div>
  )
}

/** Inline error/notice box. */
export function Notice({ tone = 'danger', icon: Icon, children, className }) {
  const tones = {
    danger: 'border-danger/40 bg-danger/5 text-danger',
    warning: 'border-warning/40 bg-warning/5 text-warning',
    info: 'border-border bg-fill text-muted',
  }
  return (
    <div className={cn('flex items-start gap-2 border px-3 py-2 text-sm', tones[tone], className)}>
      {Icon && <Icon className="mt-0.5 size-4 shrink-0" />}
      <div className="min-w-0">{children}</div>
    </div>
  )
}

/** Standard error block with a retry button (UI spec: never hide failures). */
export function ErrorState({ error, onRetry, className }) {
  return (
    <div className={cn('flex flex-col items-center gap-3 border border-danger/30 bg-danger/5 px-6 py-10 text-center', className)}>
      <AlertTriangle className="size-6 text-danger" />
      <p className="font-medium">Something went wrong.</p>
      <p className="max-w-md text-sm text-muted">{error?.message || 'Unexpected error.'}</p>
      {onRetry && <Button variant="outline" size="sm" icon={RotateCw} onClick={onRetry}>Try again</Button>}
    </div>
  )
}

/** Underlined tab bar. `tabs` = [{ id, label, count?, icon? }]. */
export function Tabs({ tabs, value, onChange, className }) {
  return (
    <div role="tablist" className={cn('flex gap-1 overflow-x-auto overflow-y-hidden border-b border-border', className)}>
      {tabs.map((t) => {
        const active = t.id === value
        return (
          <button
            key={t.id} role="tab" type="button" aria-selected={active} onClick={() => onChange(t.id)}
            className={cn(
              '-mb-px flex shrink-0 cursor-pointer items-center gap-2 border-b-2 px-4 py-2.5 text-sm transition-colors',
              active ? 'border-secondary font-semibold text-foreground' : 'border-transparent text-muted hover:text-foreground',
            )}
          >
            {t.icon && <t.icon className="size-4" />}
            {t.label}
            {t.count != null && <span className="font-mono text-[11px] text-muted">{t.count}</span>}
          </button>
        )
      })}
    </div>
  )
}

// ── Overlays ──────────────────────────────────────────────────────────────────

/** Close on Escape and lock page scroll while an overlay is open. */
function useOverlay(open, onClose) {
  useEffect(() => {
    if (!open) return undefined
    const onKey = (e) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = overflow
    }
  }, [open, onClose])
}

/** Centered dialog. */
export function Modal({ open, onClose, title, description, children, footer, className }) {
  useOverlay(open, onClose)
  return createPortal(
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[60] grid place-items-center p-4" role="dialog" aria-modal="true" aria-label={title}>
          <motion.div
            className="absolute inset-0 bg-black/60 backdrop-blur-sm"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            className={cn('relative w-full max-w-lg rounded-xl border border-border bg-surface p-6 shadow-xl', className)}
            initial={{ opacity: 0, y: 16, scale: 0.98 }} animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 16, scale: 0.98 }} transition={{ duration: 0.2 }}
          >
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
                {description && <p className="mt-1 text-sm text-muted">{description}</p>}
              </div>
              <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close"><X className="size-4" /></Button>
            </div>
            {children}
            {footer && <div className="mt-6 flex justify-end gap-2">{footer}</div>}
          </motion.div>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  )
}

/** Right-hand side panel for details (evidence, chunks). */
export function Drawer({ open, onClose, title, eyebrow, children, width = 'max-w-xl' }) {
  useOverlay(open, onClose)
  return createPortal(
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[60]" role="dialog" aria-modal="true" aria-label={title}>
          <motion.div
            className="absolute inset-0 bg-black/50 backdrop-blur-[2px]"
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.aside
            className={cn('absolute inset-y-0 right-0 flex w-full flex-col border-l border-border bg-background', width)}
            initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 32, stiffness: 320 }}
          >
            <div className="flex items-start justify-between gap-4 border-b border-border px-6 py-5">
              <div className="min-w-0">
                {eyebrow && <Eyebrow>{eyebrow}</Eyebrow>}
                <h2 className="mt-1 text-lg font-semibold tracking-tight">{title}</h2>
              </div>
              <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close"><X className="size-4" /></Button>
            </div>
            <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>
          </motion.aside>
        </div>
      )}
    </AnimatePresence>,
    document.body,
  )
}
