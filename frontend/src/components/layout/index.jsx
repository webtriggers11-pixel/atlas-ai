/**
 * App chrome — floating pill navbar, theme toggle, logo and page header,
 * following the WebTriggers 2.0 site's layout components.
 */
import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { AnimatePresence, motion } from 'framer-motion'
import { ChevronRight, Menu, Moon, Sun, X } from 'lucide-react'
import { applyMode, initialMode } from '@/config/theme'
import { cn } from '@/lib/utils'
import { Reveal } from '@/components/kit'

// ── Theme mode ───────────────────────────────────────────────────────────────

const ThemeContext = createContext({ mode: 'dark', toggle: () => {} })

/** Holds light/dark mode and writes it to <html data-theme>. */
export function ThemeProvider({ children }) {
  const [mode, setMode] = useState(initialMode)
  useEffect(() => applyMode(mode), [mode])
  const toggle = useCallback(() => setMode((m) => (m === 'dark' ? 'light' : 'dark')), [])
  return <ThemeContext.Provider value={{ mode, toggle }}>{children}</ThemeContext.Provider>
}

export const useThemeMode = () => useContext(ThemeContext)

/** Sun/moon button with a small rotate animation. */
export function ThemeToggle() {
  const { mode, toggle } = useThemeMode()
  const isDark = mode === 'dark'
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={`Switch to ${isDark ? 'light' : 'dark'} mode`}
      className="relative grid size-9 cursor-pointer place-items-center overflow-hidden rounded-pill border border-border text-muted transition-colors hover:bg-fill-strong hover:text-foreground"
    >
      <AnimatePresence mode="wait" initial={false}>
        <motion.span
          key={isDark ? 'moon' : 'sun'}
          initial={{ y: 12, opacity: 0, rotate: -45 }}
          animate={{ y: 0, opacity: 1, rotate: 0 }}
          exit={{ y: -12, opacity: 0, rotate: 45 }}
          transition={{ duration: 0.2 }}
        >
          {isDark ? <Moon className="size-4" /> : <Sun className="size-4" />}
        </motion.span>
      </AnimatePresence>
    </button>
  )
}

// ── Brand ────────────────────────────────────────────────────────────────────

/** Idea Atlas wordmark: a signal-colored square mark + name. */
export function Logo({ className }) {
  return (
    <span className={cn('inline-flex items-center gap-2.5', className)}>
      <span className="relative grid size-7 place-items-center bg-accent text-accent-foreground">
        <span className="font-mono text-[11px] font-bold">IA</span>
        <span className="absolute -right-[3px] top-0 h-full w-[3px] origin-top-left skew-y-[45deg] bg-[var(--pop-right)]" />
        <span className="absolute -bottom-[3px] left-0 h-[3px] w-full origin-top-left skew-x-[45deg] bg-[var(--pop-bottom)]" />
      </span>
      <span className="text-sm font-semibold tracking-tight">
        Idea <span className="font-serif text-base font-normal italic">Atlas</span>
      </span>
    </span>
  )
}

// ── Navbar ───────────────────────────────────────────────────────────────────

const NAV = [
  { label: 'Projects', to: '/' },
  { label: 'Explore topics', to: '/explore' },
]

/** Floating pill navbar that gains a blurred background once the page scrolls. */
export function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const [open, setOpen] = useState(false)
  const location = useLocation()

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])
  useEffect(() => setOpen(false), [location.pathname])

  return (
    <header className="fixed inset-x-0 top-0 z-50 px-4 pt-4">
      <nav className={cn(
        'mx-auto flex max-w-6xl items-center justify-between rounded-pill border px-5 py-3 transition-all duration-500',
        scrolled || open
          ? 'border-border bg-background/75 shadow-lg shadow-black/5 backdrop-blur-xl dark:shadow-black/30'
          : 'border-transparent bg-transparent',
      )}>
        <Link to="/" aria-label="Idea Atlas — projects"><Logo /></Link>

        <ul className="hidden items-center gap-1 md:flex">
          {NAV.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) => cn(
                  'rounded-pill px-4 py-2 text-sm transition-colors hover:bg-fill-strong hover:text-foreground',
                  isActive ? 'text-foreground' : 'text-muted',
                )}
              >
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>

        <div className="flex items-center gap-2">
          <ThemeToggle />
          <button
            type="button"
            aria-label={open ? 'Close menu' : 'Open menu'}
            aria-expanded={open}
            onClick={() => setOpen((o) => !o)}
            className="grid size-9 place-items-center rounded-pill border border-border md:hidden"
          >
            {open ? <X className="size-4" /> : <Menu className="size-4" />}
          </button>
        </div>
      </nav>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.25 }}
            className="mx-auto mt-2 max-w-6xl border border-border bg-background/90 p-3 backdrop-blur-xl md:hidden"
          >
            {NAV.map((item) => (
              <Link key={item.to} to={item.to} className="block px-4 py-3 text-base hover:bg-fill-strong">{item.label}</Link>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  )
}

// ── Page header ──────────────────────────────────────────────────────────────

/** Top section of a page: breadcrumbs, glow + grid background, eyebrow, title, intro, actions. */
export function PageHeader({ eyebrow, title, intro, crumbs, actions, children }) {
  return (
    <section className="relative isolate overflow-hidden px-6 pt-32 pb-10">
      <div aria-hidden className="absolute inset-0 -z-10">
        <div className="absolute -top-40 left-1/4 size-[36rem] rounded-full bg-glow/10 blur-[120px] dark:bg-glow/[0.07]" />
        <div className="absolute inset-0 bg-grid [mask-image:radial-gradient(ellipse_at_top,black_10%,transparent_65%)]" />
      </div>
      <div className="mx-auto max-w-6xl">
        {crumbs && (
          <nav aria-label="Breadcrumb" className="mb-6 flex flex-wrap items-center gap-1 text-xs text-muted">
            {crumbs.map((c, i) => (
              <span key={c.label} className="flex items-center gap-1">
                {i > 0 && <ChevronRight className="size-3" />}
                {c.to ? <Link to={c.to} className="hover:text-foreground">{c.label}</Link> : <span>{c.label}</span>}
              </span>
            ))}
          </nav>
        )}
        <Reveal>
          <div className="flex flex-wrap items-end justify-between gap-6">
            <div className="min-w-0">
              {eyebrow && <p className="text-[11px] font-medium tracking-[0.2em] text-secondary uppercase">{eyebrow}</p>}
              <h1 className="mt-3 max-w-4xl text-4xl leading-[1.05] font-semibold tracking-tighter text-balance sm:text-5xl">
                {title}
              </h1>
              {intro && <p className="mt-4 max-w-2xl text-base text-pretty text-muted">{intro}</p>}
            </div>
            {actions && <div className="flex flex-wrap items-center gap-3">{actions}</div>}
          </div>
          {children}
        </Reveal>
      </div>
    </section>
  )
}
