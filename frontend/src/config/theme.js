/**
 * ─── COLORS & SHAPE ──────────────────────────────────────────────────────────
 * The single place to change the app's look (ported from the WebTriggers 2.0 site).
 *
 *  1. Pick a palette:        set `activePalette` to a key of `palettes`
 *  2. Pick the default mode: `defaultMode` = "system" | "light" | "dark"
 *  3. Pick the shape:        `shape` = "sharp" (NeoPOP, square edges) | "rounded"
 *
 * Roles
 *  primary / onPrimary   main buttons, active states
 *  secondary             labels, eyebrows, icons
 *  accent / onAccent     loud highlight fills (badges, markers) — use sparingly
 *  glow                  soft background glows and button shadows
 *  popRight/popBottom    3D "plunk" edge colors for primary buttons (NeoPOP)
 *  status: covered/partial/missing/conflict/unclear — the five finding colors
 *
 * The NeoPOP palettes follow CRED's open-source NeoPOP design system
 * (github.com/CRED-CLUB/neopop-web, Apache-2.0). "electricBlue" is Idea Atlas's own brand;
 * "neopop" (black + signal yellow) is the WebTriggers brand, kept for reference.
 * ─────────────────────────────────────────────────────────────────────────────
 */

const neutrals = {
  light: {
    background: '#fafafa', surface: '#ffffff', surface2: '#f4f4f5', foreground: '#0a0a0a',
    muted: '#525252', border: '#e5e5e5', fill: 'rgb(0 0 0 / 0.04)', fillStrong: 'rgb(0 0 0 / 0.07)',
    success: '#16a34a', warning: '#d97706', danger: '#dc2626',
    popRight: '#8a8a8a', popBottom: '#3d3d3d', popRight2: '#e0e0e0', popBottom2: '#8a8a8a',
  },
  dark: {
    background: '#121212', surface: '#1c1c1c', surface2: '#262626', foreground: '#f5f5f5',
    muted: '#a3a3a3', border: 'rgb(255 255 255 / 0.1)', fill: 'rgb(255 255 255 / 0.05)',
    fillStrong: 'rgb(255 255 255 / 0.09)',
    success: '#4ade80', warning: '#fbbf24', danger: '#f87171',
    popRight: '#e0e0e0', popBottom: '#8a8a8a', popRight2: '#e0e0e0', popBottom2: '#8a8a8a',
  },
}

// Finding-status colors, tuned per mode for contrast on the surfaces above
const statusColors = {
  light: { covered: '#06a35f', partial: '#c77700', missing: '#e0402b', conflict: '#b4237a', unclear: '#6b6b6b' },
  dark:  { covered: '#3bffad', partial: '#ffb444', missing: '#ff5a4a', conflict: '#ff6fcf', unclear: '#a0a0a0' },
}

export const palettes = {
  // Idea Atlas brand: NeoPOP structure, electric-blue signal (blue is never a finding-status colour)
  electricBlue: {
    label: 'Electric Blue',
    light: {
      background: '#f6f8fc', surface: '#ffffff', surface2: '#edf1f8', foreground: '#07090f',
      muted: '#566070', border: '#dfe4ee', primary: '#07090f', onPrimary: '#ffffff', secondary: '#1f5bff',
      accent: '#1f5bff', onAccent: '#ffffff', glow: '#9fbcff',
      success: '#06c270', warning: '#f08d32', danger: '#ee4d37',
    },
    dark: {
      background: '#07090f', surface: '#0d1119', surface2: '#131824', foreground: '#ebeef5',
      muted: '#9aa3b5', border: 'rgb(255 255 255 / 0.1)', primary: '#ffffff', onPrimary: '#07090f',
      secondary: '#5b8fff', accent: '#3d7bff', onAccent: '#ffffff', glow: '#3d7bff',
      success: '#3bffad', warning: '#ff8744', danger: '#ff426f',
    },
  },
  // Web Triggers brand: Ink #0D0D0D, Signal #EAFD66 (dark) / #CDE52B (light), Paper #F8F8F8
  neopop: {
    label: 'NeoPOP',
    light: {
      background: '#f8f8f8', surface: '#ffffff', surface2: '#efefef', foreground: '#0d0d0d',
      muted: '#5c5c5c', border: '#e0e0e0', primary: '#0d0d0d', onPrimary: '#ffffff', secondary: '#0d0d0d',
      accent: '#cde52b', onAccent: '#0d0d0d', glow: '#c7c7c7',
      success: '#06c270', warning: '#f08d32', danger: '#ee4d37',
    },
    dark: {
      background: '#0d0d0d', surface: '#121212', surface2: '#161616', foreground: '#ebebeb',
      muted: '#a0a0a0', border: 'rgb(255 255 255 / 0.1)', primary: '#ffffff', onPrimary: '#0d0d0d',
      secondary: '#eafd66', accent: '#eafd66', onAccent: '#0d0d0d', glow: '#eafd66',
      success: '#3bffad', warning: '#ff8744', danger: '#ff426f',
    },
  },
  mono: {
    label: 'Monochrome',
    light: { primary: '#0a0a0a', onPrimary: '#ffffff', secondary: '#525252', accent: '#0a0a0a', onAccent: '#ffffff', glow: '#a3a3a3' },
    dark: { primary: '#fafafa', onPrimary: '#0a0a0a', secondary: '#a3a3a3', accent: '#fafafa', onAccent: '#0a0a0a', glow: '#ffffff' },
  },
}

export const themeConfig = {
  activePalette: 'electricBlue',
  defaultMode: 'dark',
  shape: 'sharp',
}

/** Resolved colors for one mode (neutrals overridden by the active palette). */
export function colorsFor(mode) {
  return { ...neutrals[mode], ...statusColors[mode], ...palettes[themeConfig.activePalette][mode] }
}

/** CSS custom properties for both modes plus corner radii — injected once at startup. */
export function themeCss() {
  const vars = (mode) =>
    Object.entries(colorsFor(mode))
      .map(([k, v]) => `--${k.replace(/[A-Z0-9]/g, (c) => `-${c.toLowerCase()}`)}:${v};`)
      .join('')

  // "sharp" squares off cards, buttons and tags; true circles (dots, avatars) stay round
  const radii = themeConfig.shape === 'sharp'
    ? '--radius-sm:0;--radius-md:0;--radius-lg:0;--radius-xl:0;--radius-2xl:0;--radius-3xl:0;--shape-pill:0;'
    : '--shape-pill:9999px;'

  return `:root{${radii}}:root,[data-theme=light]{color-scheme:light;${vars('light')}}[data-theme=dark]{color-scheme:dark;${vars('dark')}}`
}

const STORAGE_KEY = 'atlas-theme'

/** The saved mode, else the configured default ("system" follows the OS). */
export function initialMode() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved === 'light' || saved === 'dark') return saved
  } catch { /* storage blocked (private mode) — fall through to the default */ }
  if (themeConfig.defaultMode === 'system') {
    return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }
  return themeConfig.defaultMode
}

/** Apply a mode to <html data-theme> and remember it. */
export function applyMode(mode) {
  document.documentElement.dataset.theme = mode
  try { localStorage.setItem(STORAGE_KEY, mode) } catch { /* ignore */ }
}

/** Inject the theme variables and set the initial mode — call once before React renders. */
export function installTheme() {
  const style = document.createElement('style')
  style.id = 'atlas-theme-vars'
  style.textContent = themeCss()
  document.head.prepend(style)
  applyMode(initialMode())
}
