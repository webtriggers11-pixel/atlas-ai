---
name: Idea Atlas
colors:
  surface: '#111319'
  surface-dim: '#111319'
  surface-bright: '#373940'
  surface-container-lowest: '#0c0e14'
  surface-container-low: '#191b22'
  surface-container: '#1e1f26'
  surface-container-high: '#282a30'
  surface-container-highest: '#33343b'
  on-surface: '#e2e2eb'
  on-surface-variant: '#d8c3ad'
  inverse-surface: '#e2e2eb'
  inverse-on-surface: '#2e3037'
  outline: '#a08e7a'
  outline-variant: '#534434'
  surface-tint: '#ffb95f'
  primary: '#ffc174'
  on-primary: '#472a00'
  primary-container: '#f59e0b'
  on-primary-container: '#613b00'
  inverse-primary: '#855300'
  secondary: '#c2c5de'
  on-secondary: '#2b2f43'
  secondary-container: '#44485d'
  on-secondary-container: '#b4b7d0'
  tertiary: '#8fd5ff'
  on-tertiary: '#00344a'
  tertiary-container: '#1abdff'
  on-tertiary-container: '#004966'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#ffddb8'
  primary-fixed-dim: '#ffb95f'
  on-primary-fixed: '#2a1700'
  on-primary-fixed-variant: '#653e00'
  secondary-fixed: '#dee1fb'
  secondary-fixed-dim: '#c2c5de'
  on-secondary-fixed: '#161b2d'
  on-secondary-fixed-variant: '#42465a'
  tertiary-fixed: '#c5e7ff'
  tertiary-fixed-dim: '#7fd0ff'
  on-tertiary-fixed: '#001e2d'
  on-tertiary-fixed-variant: '#004c6a'
  background: '#111319'
  on-background: '#e2e2eb'
  surface-variant: '#33343b'
typography:
  display:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  2xl: 48px
  container-margin: 24px
  gutter: 16px
---

## Brand & Style

The design system is engineered for deep focus and cognitive clarity, targeting high-performance professionals and creative thinkers. It employs a refined **Modern Corporate** aesthetic with a lean toward **Minimalism**, prioritizing information density without visual noise. 

The emotional response is one of "quiet power"—calm, reliable, and premium. Taking inspiration from high-end developer tools, the system avoids decorative shadows in favor of structural integrity, crisp borders, and a disciplined use of accent colors to guide the eye toward meaningful actions. High-quality whitespace and rigid alignment ensure that complex ideas feel manageable and structured.

## Colors

The palette is anchored in a deep, midnight-blue foundation to reduce eye strain during long sessions. 

- **Foundation:** The base background is `#0F1117`, providing a sophisticated canvas that feels more premium than pure black.
- **Layers:** Surfaces utilize `#1A1D2E` and `#1E2235` to create clear semantic hierarchy through tonal shifts rather than shadows.
- **Accents:** The Amber (`#F59E0B`) is used sparingly for primary actions, focus states, and critical paths. 
- **Borders:** A consistent subtle border (`rgba(255,255,255,0.08)`) is required to define boundaries between dark surfaces.

## Typography

The typography system uses **Inter** exclusively to maintain a utilitarian, technical feel. 

- **Readability:** The base size is set to 16px to ensure clarity during information-heavy tasks. 
- **Rhythm:** For headings, use tighter letter spacing (`-0.02em`) to create a compact, modern appearance. 
- **Micro-copy:** Use `label-sm` in all-caps for metadata, tags, and section headers to provide clear visual distinction from body text. 
- **Hierarchy:** Primary content should remain `#F1F5F9`, while supporting text and descriptions should strictly use `#64748B`.

## Layout & Spacing

The layout operates on a strict 4px grid system. 

- **Grid:** Use a 12-column fluid grid for main dashboards. For tool-heavy views (like maps or canvases), use a "No Grid" approach with absolute positioning and smart snapping.
- **Margins:** Standard page margins are 24px on desktop and 16px on mobile. 
- **Density:** Maintain generous internal padding within panels (24px) to emphasize the "Atlas" feel—giving ideas room to breathe. Use tighter spacing (8px-12px) for list items and navigation components.

## Elevation & Depth

This design system eschews traditional drop shadows. Depth is communicated through **Tonal Layering** and **Subtle Outlines**:

1.  **Level 0 (Canvas):** `#0F1117` - The furthest back surface.
2.  **Level 1 (Panels):** `#1A1D2E` - Sidebar and footer areas, separated by a 1px border.
3.  **Level 2 (Cards/Nodes):** `#1E2235` - Floating interactive elements.
4.  **Level 3 (Popovers/Modals):** `#1E2235` - Use a slightly brighter border (`rgba(255,255,255,0.15)`) to indicate the highest level of z-index.

Interactive states (Hover/Active) should be indicated by a border color shift to the Primary Amber or a subtle lightening of the surface hex.

## Shapes

The shape language is varied to create a clear visual hierarchy between container types:

- **Nodes/Cards:** 12px (`rounded-lg`) to provide a friendly but structured feel for data chunks.
- **Buttons/Inputs:** 8px (`rounded-md`) for a precise, "clickable" tool appearance.
- **Main Panels/Sidebars:** 16px (`rounded-xl`) to frame the entire application interface.

Interactive elements like Checkboxes should remain slightly rounded (4px) to maintain the modern aesthetic without feeling "bubbly."

## Components

- **Buttons:** 
  - **Primary:** Amber background (`#F59E0B`), dark text (`#0F1117`), 8px radius. 
  - **Secondary:** Transparent background, 1px border (`rgba(255,255,255,0.08)`), text `#F1F5F9`.
- **Nodes (Ideas):** Background `#1E2235`, 12px radius, 1px border. On focus, the border changes to `#F59E0B`.
- **Input Fields:** Background `#1A1D2E`, 1px border, 8px radius. Text uses `body-md`. Placeholder text in `#64748B`.
- **Chips/Tags:** Background `rgba(255,255,255,0.04)`, 4px radius, `label-sm` typography.
- **Lists:** Clean rows with no vertical borders; use a 1px bottom border between items.
- **Command Palette:** A centered modal with 16px radius, heavy backdrop blur (20px), and `#1A1D2E` background. This is a core "Power User" component.