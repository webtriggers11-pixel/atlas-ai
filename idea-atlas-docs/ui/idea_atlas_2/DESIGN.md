---
name: Idea Atlas
colors:
  surface: '#fef7ff'
  surface-dim: '#dfd7e6'
  surface-bright: '#fef7ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f9f1ff'
  surface-container: '#f3ebfa'
  surface-container-high: '#ede5f4'
  surface-container-highest: '#e8dfee'
  on-surface: '#1d1a24'
  on-surface-variant: '#4a4455'
  inverse-surface: '#332f39'
  inverse-on-surface: '#f6eefc'
  outline: '#7b7487'
  outline-variant: '#ccc3d8'
  surface-tint: '#732ee4'
  primary: '#630ed4'
  on-primary: '#ffffff'
  primary-container: '#7c3aed'
  on-primary-container: '#ede0ff'
  inverse-primary: '#d2bbff'
  secondary: '#5f5e60'
  on-secondary: '#ffffff'
  secondary-container: '#e5e1e4'
  on-secondary-container: '#656466'
  tertiary: '#7d3d00'
  on-tertiary: '#ffffff'
  tertiary-container: '#a15100'
  on-tertiary-container: '#ffe0cd'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#eaddff'
  primary-fixed-dim: '#d2bbff'
  on-primary-fixed: '#25005a'
  on-primary-fixed-variant: '#5a00c6'
  secondary-fixed: '#e5e1e4'
  secondary-fixed-dim: '#c8c6c8'
  on-secondary-fixed: '#1c1b1d'
  on-secondary-fixed-variant: '#474649'
  tertiary-fixed: '#ffdcc6'
  tertiary-fixed-dim: '#ffb784'
  on-tertiary-fixed: '#301400'
  on-tertiary-fixed-variant: '#713700'
  background: '#fef7ff'
  on-background: '#1d1a24'
  surface-variant: '#e8dfee'
typography:
  display:
    fontFamily: Plus Jakarta Sans
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Plus Jakarta Sans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.2'
  headline-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: '1.4'
  body-lg:
    fontFamily: Plus Jakarta Sans
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.5'
  label-md:
    fontFamily: Plus Jakarta Sans
    fontSize: 13px
    fontWeight: '500'
    lineHeight: '1'
  label-sm:
    fontFamily: Plus Jakarta Sans
    fontSize: 11px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 40px
  container-max: 1200px
  gutter: 20px
  sidebar-width: 260px
---

## Brand & Style
The design system is engineered for high-density knowledge work, prioritizing cognitive clarity and rapid navigation. It targets power users, researchers, and builders who require a workspace that feels sophisticated yet invisible—allowing the content to remain the primary focus.

The style is **Minimalist-Professional**, drawing inspiration from modern productivity tools like Linear and Perplexity. It utilizes a restrained color palette, precise geometry, and meaningful whitespace to create a sense of organized calm. Visual complexity is strictly limited to functional elements, using subtle borders and intentional typography rather than heavy shadows or decorative gradients to establish hierarchy.

## Colors
The palette is rooted in a high-contrast foundation for maximum legibility. The primary background uses a subtle off-white to reduce eye strain during long sessions, while surfaces use pure white to denote interactable or elevated content. 

The **Violet Accent (#7C3AED)** is used surgically: for primary actions, active states, and highlighting key nodes in the knowledge graph. Neutral tones follow a strict scale from the near-black text to soft zinc-colored borders, ensuring that the interface feels grounded and institutional.

## Typography
**Plus Jakarta Sans** is the sole typeface, chosen for its modern, geometric construction and high x-height which excels in technical interfaces. 

Headlines utilize tighter letter-spacing and heavier weights to provide strong structural anchors. Body text is optimized for readability with a generous line height. The "Label" styles are used for metadata, tags, and small UI affordances, often employing a medium or semi-bold weight to maintain legibility at small scales.

## Layout & Spacing
The layout follows a **Fixed-Fluid hybrid grid**. Sidebars and navigation panels are fixed-width to ensure tool consistency, while the central workspace (the "Atlas") is fluid to maximize the visualization area.

A 4px baseline grid governs all spacing. Vertical rhythm is maintained through standard increments (8, 16, 24, 40). 
- **Desktop:** 12-column grid within a 1200px max-width container for content-heavy pages.
- **Tablet:** 8-column grid with 16px margins.
- **Mobile:** Single column with 16px safe-area margins; horizontal navigation is typically collapsed into a bottom bar or drawer.

## Elevation & Depth
Depth is communicated through **Tonal Layering** and **Low-Contrast Outlines** rather than dramatic shadows. 

1.  **Level 0 (Background):** #FAFAFA.
2.  **Level 1 (Panels/Cards):** #FFFFFF with a 1px border (#E4E4E7). A singular, subtle shadow `0 1px 3px rgba(0,0,0,0.08)` is permitted for floating cards to provide just enough separation from the background.
3.  **Level 2 (Modals/Popovers):** #FFFFFF with a slightly more pronounced border and a backdrop blur (12px) on the obscured layer to focus attention.

Avoid using shadows on buttons or input fields to maintain the flat, professional aesthetic.

## Shapes
The design system uses a sophisticated variable radius strategy to distinguish between different types of UI containers:
- **Buttons & Inputs (8px):** Tightest radius for compact, actionable elements.
- **Nodes/Cards (10px):** Balanced radius for content blocks and graph elements.
- **Panels/Modals (14px):** Softest radius for major layout sections and structural containers.

This tiered approach ensures that smaller elements feel precise, while larger containers feel approachable and modern.

## Components
- **Buttons:** Primary buttons use #7C3AED background with white text. Ghost buttons use no background and #09090B text, appearing only on hover to reduce visual noise.
- **Input Fields:** 1px solid border (#E4E4E7). On focus, the border shifts to #7C3AED with a 2px outer ring of the same color at 10% opacity.
- **Nodes (Graph):** 10px rounded corners, white surface, 1px border. Active nodes feature a 2px violet border.
- **Chips/Tags:** Small (label-sm), subtle grey background (#F4F4F5), and 4px radius.
- **Lists:** Clean lines with 1px bottom borders. Hover states use #FAFAFA.
- **Panels:** Use the 14px radius. Sidebars should be separated by a 1px vertical divider rather than a shadow.
- **Progress/Status Indicators:** Use 2px tall bars for subtle progress tracking at the top of cards or panels.