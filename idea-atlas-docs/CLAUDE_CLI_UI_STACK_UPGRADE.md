# UI STACK UPGRADE — Idea Atlas
# Paste this entire file into Claude Code.

You are upgrading the Idea Atlas frontend component layer. The current
stack (React 18 + Vite + React Flow + dagre + Zustand + Tailwind +
framer-motion + react-hot-toast + Plus Jakarta Sans) is CORRECT and
stays. Do not replace any of it. We are ADDING a base component system
on top.

I am learning while building. Explain each step in 2-3 plain English
sentences after completing it. One step at a time. Wait for my
"continue" after every step. If anything fails, explain why before
fixing.

---

## WHAT WE ARE ADDING AND WHY

1. shadcn/ui — copy-paste component system (buttons, inputs, dialogs,
   dropdowns, tabs, command palette). We own the code, it is accessible
   by default, and it is the 2026 industry standard base layer.
2. Three Magic UI components ONLY — shimmer skeleton, animated
   progress, text reveal. Tasteful polish, nothing flashy.
3. A Ctrl+K command palette — the feature every premium tool (Linear,
   Notion, Raycast) has. Search nodes and maps, jump anywhere.

## WHAT WE ARE EXPLICITLY NOT ADDING

- No Aceternity UI, no 3D cards, no spotlights, no particle or mesh
  backgrounds. This is a working tool, not a landing page.
- No new state library, no new styling system, no CSS-in-JS.
- No component that duplicates something React Flow already does.

## HARD CONSTRAINTS

- Keep our design tokens exactly: bg #FAFAFA, surface #FFFFFF, border
  #E4E4E7, text #09090B, muted #71717A, accent #7C3AED, accent-light
  #EDE9FE, accent-text #5B21B6, font Plus Jakarta Sans, radius 10/8/14.
- All existing features must still work after every step (topic flow,
  tree, expand/collapse, depth toggle, reading mode, sidebar,
  keyboard shortcuts).
- Bundle growth budget: max ~50KB gzipped total for this whole upgrade.
  Check with `npm run build` before and after and report the numbers.

---

## STEP 1 — Install and configure shadcn/ui

- Run the shadcn init flow for a Vite (NOT Next.js) React project.
  Follow current shadcn docs for Vite setup: tsconfig/jsconfig path
  alias "@/" → "./src", components.json, and Tailwind config updates.
- IMPORTANT: map shadcn's CSS variables to OUR tokens in index.css.
  --background → #FAFAFA, --foreground → #09090B,
  --primary → #7C3AED, --primary-foreground → #FFFFFF,
  --muted → #F4F4F5, --muted-foreground → #71717A,
  --border → #E4E4E7, --radius → 0.5rem.
  The app must look IDENTICAL after this step — shadcn adapts to us,
  not the other way around.
- Run the dev server, confirm zero visual changes and zero console
  errors.
- Explain to me: what does "copy-paste component library" mean and why
  is owning the component code better than installing a package?
Then wait.

## STEP 2 — Add the core shadcn components

Add via the shadcn CLI: button, input, dialog, dropdown-menu, tabs,
tooltip, badge, separator, scroll-area, skeleton.

Do not wire them anywhere yet. Just confirm they exist under
src/components/ui/ and compile.
Then wait.

## STEP 3 — Migrate our components to the shadcn base, one at a time

Order (stop after each, confirm visually identical or better):
  3a. TopBar: our Generate button → shadcn Button (styled to our
      violet), our input → shadcn Input with the same focus ring
      (#EDE9FE 3px) and the search icon + "/" hint preserved.
  3b. Sidebar: delete confirmation → shadcn Dialog ("Delete this map?"
      with Cancel/Delete buttons) instead of instant delete. Map count
      badge → shadcn Badge.
  3c. NodeDetailPanel: depth toggle → shadcn Tabs styled as our
      segmented pill (keep the framer-motion layoutId slide).
      "Expand" button → shadcn Button variant outline in violet.
      Panel scroll → shadcn ScrollArea.
  3d. All tooltips (depth labels "One line / A short paragraph / Full
      detail", node hints) → shadcn Tooltip.
Regression-check the full flow after 3d.
Explain to me: what did we gain from this migration that our hand-built
components did not have? (expected answer themes: accessibility,
keyboard handling, focus management, consistency)
Then wait.

## STEP 4 — Ctrl+K command palette

Add shadcn's command component (cmdk under the hood).

Behavior:
- Ctrl+K (and Cmd+K on Mac) opens it from anywhere. Esc closes.
- Group 1 "Concepts in this map": every node label of the current map.
  Selecting one → setSelectedNode + fitView centered on it.
- Group 2 "Recent maps": all maps from the sidebar list. Selecting one
  → loads that map.
- Group 3 "Actions": "New topic…" (focuses TopBar input),
  "Toggle Reading Mode", "Collapse all", "Run Gap Check" (only for
  document maps, if Phase C backend exists).
- Fuzzy search across all groups as the user types.
- Style: our surface white, border #E4E4E7, radius 14px, selected item
  background #EDE9FE with text #5B21B6.
- Add a subtle hint in the TopBar right side: "⌘K" chip in muted text.
Explain to me: why do premium tools all converge on the command
palette pattern?
Then wait.

## STEP 5 — Magic UI, exactly three components

From Magic UI (magicui.design — copy-paste, they are Tailwind +
framer-motion which we already have):

  5a. Shimmer/skeleton effect → apply to our LoadingSkeleton nodes and
      the explanation loading lines in NodeDetailPanel. Replace the
      plain opacity pulse with the shimmer sweep.
  5b. Animated progress bar → the document upload steps ("Reading
      document → Breaking into concepts → Building your map") if the
      document upload UI exists; otherwise apply to the "Explored X of
      N" progress line.
  5c. Text reveal / blur-in → Reading Mode H1 and H2 headings only.
      Body text must NOT animate (never animate what people are
      reading).

If any Magic UI snippet needs a dependency we don't have, tell me
before installing it.
Then wait.

## STEP 6 — Bundle check + final regression

- Run `npm run build`. Report gzipped bundle size before (from Step 1
  baseline) and after. If growth exceeds ~50KB gzipped, identify the
  heaviest addition and propose what to cut.
- Full regression pass, report each as pass/fail:
  1. Topic generate → tree renders
  2. Expand/collapse nodes, breadcrumb, collapse-all
  3. Node panel: depth tabs slide, explanation loads, expand works
  4. Reading mode toggle both directions, shared position preserved
  5. Ctrl+K: jump to node, switch map, run action
  6. Delete map now shows confirm dialog
  7. All keyboard shortcuts (/, arrows, E, R, Esc) still work with the
     command palette closed; palette Esc does not conflict
  8. Toasts still render
- Fix all failures before declaring done.

## INTERVIEW PREP — give after Step 6

Q&A format, plain English, 2-3 sentences each:
1. What is shadcn/ui and how is it different from MUI or Ant Design?
2. Why did you map shadcn's CSS variables to your existing tokens
   instead of adopting shadcn's default theme?
3. What accessibility features did the migration add for free?
4. What is cmdk and how does the command palette search work?
5. How did you keep the bundle size under control while adding
   component libraries?

---

START NOW with STEP 1. Show me the shadcn init plan for Vite before
running it. Then wait for my confirmation.
