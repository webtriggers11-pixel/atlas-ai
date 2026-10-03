/**
 * App chrome — layout per the V2 UI spec (left sidebar + slim topbar), styled with the
 * WebTriggers 2.0 design language (NeoPOP palette, sharp edges, plunk buttons).
 */
import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/store/authStore'
import { AnimatePresence, motion } from 'framer-motion'
import { ChevronRight, Files, LayoutDashboard, ListChecks, LogOut, Menu, Moon, Network, PanelLeftClose, PanelLeft, Plus, Settings, Sun } from 'lucide-react'
import { applyMode, initialMode } from '@/config/theme'
import { cn } from '@/lib/utils'
import { Button } from '@/components/kit'

// ── Theme mode ───────────────────────────────────────────────────────────────

const ThemeContext = createContext({ mode: 'dark', toggle: () => {} })

/** Holds light/dark mode and writes it to <html data-theme>. */
export function ThemeProvider({ children }) {
  const [mode, setMode] = useState(initialMode)
  useEffect(() => applyMode(mode), [mode])
  const toggle = useCallback(() => setMode((m) => (m === 'dark' ? 'light' : 'dark')), [])
  return <ThemeContext.Provider value={{ mode, toggle, setMode }}>{children}</ThemeContext.Provider>
}

export const useThemeMode = () => useContext(ThemeContext)

/** Sun/moon button. */
export function ThemeToggle({ className }) {
  const { mode, toggle } = useThemeMode()
  const isDark = mode === 'dark'
  return (
    <button
      type="button"
      onClick={toggle}
      aria-label={`Switch to ${isDark ? 'light' : 'dark'} mode`}
      className={cn('grid size-9 cursor-pointer place-items-center border border-border text-muted transition-colors hover:bg-fill-strong hover:text-foreground', className)}
    >
      {isDark ? <Moon className="size-4" /> : <Sun className="size-4" />}
    </button>
  )
}

// ── Brand ────────────────────────────────────────────────────────────────────

/** Idea Atlas wordmark: a signal-colored NeoPOP square + name. */
export function Logo({ compact = false, className }) {
  return (
    <span className={cn('inline-flex items-center gap-2.5', className)}>
      <span className="relative mr-[3px] mb-[3px] grid size-7 shrink-0 place-items-center bg-accent text-accent-foreground">
        <span className="font-mono text-[11px] font-bold">IA</span>
        <span className="absolute top-0 -right-[3px] h-full w-[3px] origin-top-left skew-y-[45deg] bg-[var(--pop-right)]" />
        <span className="absolute -bottom-[3px] left-0 h-[3px] w-full origin-top-left skew-x-[45deg] bg-[var(--pop-bottom)]" />
      </span>
      {!compact && (
        <span className="text-sm font-semibold tracking-tight whitespace-nowrap">
          Idea <span className="font-serif text-base font-normal italic">Atlas</span>
        </span>
      )}
    </span>
  )
}

// ── Sidebar ──────────────────────────────────────────────────────────────────

const NAV = [
  { label: 'Dashboard', to: '/', icon: LayoutDashboard, end: true },
  { label: 'Analyses', to: '/analyses', icon: ListChecks },
  { label: 'Documents', to: '/documents', icon: Files },
  { label: 'Settings', to: '/settings', icon: Settings },
]

/** Navigation list used by both the desktop sidebar and the mobile drawer. */
function SidebarNav({ collapsed, onNavigate }) {
  const navigate = useNavigate()
  return (
    <div className="flex h-full flex-col">
      <div className={cn('flex h-14 items-center border-b border-border', collapsed ? 'justify-center' : 'px-4')}>
        <Link to="/" onClick={onNavigate} aria-label="Idea Atlas — dashboard"><Logo compact={collapsed} /></Link>
      </div>

      <div className={cn('p-3', collapsed && 'px-2')}>
        <Button
          className={cn('w-full justify-center', collapsed && 'px-0')}
          icon={Plus}
          title="New analysis"
          onClick={() => { onNavigate?.(); navigate('/analyses/new') }}
        >
          {!collapsed && 'New analysis'}
        </Button>
      </div>

      <nav className="flex-1 space-y-0.5 px-3" aria-label="Main">
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={onNavigate}
            title={collapsed ? item.label : undefined}
            className={({ isActive }) => cn(
              'flex items-center gap-3 border-l-2 px-3 py-2 text-sm transition-colors',
              collapsed && 'justify-center px-0',
              isActive ? 'border-secondary bg-fill-strong font-medium text-foreground' : 'border-transparent text-muted hover:bg-fill hover:text-foreground',
            )}
          >
            <item.icon className="size-4 shrink-0" />
            {!collapsed && item.label}
          </NavLink>
        ))}
      </nav>

      <div className={cn('border-t border-border p-3', collapsed && 'px-2')}>
        <SignedInAs collapsed={collapsed} />
        <NavLink
          to="/explore"
          onClick={onNavigate}
          title="Topic explorer (v1)"
          className={({ isActive }) => cn(
            'flex items-center gap-3 px-3 py-2 text-xs transition-colors',
            collapsed && 'justify-center px-0',
            isActive ? 'text-foreground' : 'text-muted hover:text-foreground',
          )}
        >
          <Network className="size-4 shrink-0" />
          {!collapsed && 'Topic explorer (v1)'}
        </NavLink>
      </div>
    </div>
  )
}

/** Signed-in email + sign-out, shown only when the server requires login. */
function SignedInAs({ collapsed }) {
  const { email, token, signOut } = useAuth()
  const queryClient = useQueryClient()
  if (!token) return null
  return (
    <div className={cn('mb-2 flex items-center gap-2 px-3 py-1 text-xs text-muted', collapsed && 'justify-center px-0')}>
      {!collapsed && <span className="min-w-0 flex-1 truncate" title={email}>{email}</span>}
      <button
        type="button"
        title="Sign out"
        aria-label="Sign out"
        className="grid size-7 cursor-pointer place-items-center hover:text-foreground"
        onClick={() => { signOut(); queryClient.clear() }}
      >
        <LogOut className="size-3.5" />
      </button>
    </div>
  )
}

// ── Shell ────────────────────────────────────────────────────────────────────

const COLLAPSE_KEY = 'atlas-sidebar-collapsed'

/** Sidebar + topbar + scrollable main area. The sidebar collapses on desktop and becomes a drawer on mobile. */
export function AppShell({ children }) {
  const location = useLocation()
  const navigate = useNavigate()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [collapsed, setCollapsed] = useState(() => {
    try { return localStorage.getItem(COLLAPSE_KEY) === '1' } catch { return false }
  })
  useEffect(() => {
    try { localStorage.setItem(COLLAPSE_KEY, collapsed ? '1' : '0') } catch { /* storage blocked */ }
  }, [collapsed])
  useEffect(() => setMobileOpen(false), [location.pathname])

  return (
    <div className="flex min-h-screen">
      <aside className={cn(
        'sticky top-0 hidden h-screen shrink-0 border-r border-border bg-surface transition-[width] duration-200 lg:block',
        collapsed ? 'w-16' : 'w-60',
      )}>
        <SidebarNav collapsed={collapsed} />
      </aside>

      <AnimatePresence>
        {mobileOpen && (
          <div className="fixed inset-0 z-50 lg:hidden">
            <motion.div className="absolute inset-0 bg-black/60" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setMobileOpen(false)} />
            <motion.aside
              className="absolute inset-y-0 left-0 w-64 border-r border-border bg-surface"
              initial={{ x: '-100%' }} animate={{ x: 0 }} exit={{ x: '-100%' }} transition={{ duration: 0.2 }}
            >
              <SidebarNav onNavigate={() => setMobileOpen(false)} />
            </motion.aside>
          </div>
        )}
      </AnimatePresence>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-40 flex h-14 items-center gap-3 border-b border-border bg-background/90 px-4 backdrop-blur sm:px-6">
          <button type="button" className="grid size-9 place-items-center border border-border lg:hidden" aria-label="Open menu" onClick={() => setMobileOpen(true)}>
            <Menu className="size-4" />
          </button>
          <button
            type="button"
            className="hidden size-9 cursor-pointer place-items-center text-muted hover:text-foreground lg:grid"
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            onClick={() => setCollapsed((c) => !c)}
          >
            {collapsed ? <PanelLeft className="size-4" /> : <PanelLeftClose className="size-4" />}
          </button>
          <span className="lg:hidden"><Logo compact /></span>
          <div className="ml-auto flex items-center gap-2">
            <ThemeToggle />
            {location.pathname !== '/analyses/new' && (
              <Button size="sm" icon={Plus} onClick={() => navigate('/analyses/new')} className="hidden sm:inline-flex">New analysis</Button>
            )}
          </div>
        </header>
        <main className="flex-1">{children}</main>
      </div>
    </div>
  )
}

// ── Page header ──────────────────────────────────────────────────────────────

/** Compact page header: breadcrumbs, eyebrow, title, description, actions. No hero, no decoration. */
export function PageHeader({ eyebrow, title, description, crumbs, actions, children }) {
  return (
    <div className="border-b border-border px-4 pt-6 pb-5 sm:px-8">
      {crumbs && (
        <nav aria-label="Breadcrumb" className="mb-3 flex flex-wrap items-center gap-1 text-xs text-muted">
          {crumbs.map((c, i) => (
            <span key={`${c.label}-${i}`} className="flex items-center gap-1">
              {i > 0 && <ChevronRight className="size-3" />}
              {c.to ? <Link to={c.to} className="hover:text-foreground">{c.label}</Link> : <span className="text-foreground">{c.label}</span>}
            </span>
          ))}
        </nav>
      )}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          {eyebrow && <p className="text-[11px] font-medium tracking-[0.2em] text-secondary uppercase">{eyebrow}</p>}
          <h1 className="mt-1 text-2xl font-semibold tracking-tight text-balance sm:text-3xl">{title}</h1>
          {description && <p className="mt-1.5 max-w-3xl text-sm text-pretty text-muted">{description}</p>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
      </div>
      {children}
    </div>
  )
}

/** Standard page body padding. */
export function PageBody({ className, children }) {
  return <div className={cn('px-4 py-6 sm:px-8', className)}>{children}</div>
}
