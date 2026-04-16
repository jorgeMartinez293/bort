# Bort Dashboard — Glassmorphism Redesign

**Date:** 2026-04-16  
**Status:** Approved  
**Scope:** Full visual redesign of the dashboard frontend (no backend changes)

---

## Goal

Replace the current dark-blue flat theme with a Glassmorphism Dark style: translucent frosted-glass panels over a fixed violet radial-gradient background. The layout mirrors the approved preview exactly, with two additions: a bot-selector pill at the bottom of the sidebar and no services section.

---

## Design Tokens

```css
/* Background (fixed, does not scroll) */
--bg-gradient: radial-gradient(ellipse 80% 60% at 70% 30%, rgba(139,92,246,0.35) 0%, transparent 60%),
               radial-gradient(ellipse 60% 50% at 20% 80%,  rgba(99,102,241,0.25)  0%, transparent 55%),
               radial-gradient(ellipse 50% 40% at 90% 90%,  rgba(168,85,247,0.20)  0%, transparent 50%),
               #0f0a1e;

/* Glass surfaces */
--glass-bg:        rgba(255,255,255,0.06);
--glass-bg-hover:  rgba(139,92,246,0.08);
--glass-bg-active: rgba(139,92,246,0.18);
--glass-border:    rgba(255,255,255,0.10);
--glass-border-active: rgba(139,92,246,0.30);
--glass-blur:      20px;
--glass-blur-sm:   12px;

/* Palette */
--violet:       #8b5cf6;
--violet-light: #a78bfa;
--violet-dim:   rgba(139,92,246,0.18);
--violet-glow:  rgba(139,92,246,0.40);
--emerald:      #6ee7b7;   /* approve */
--rose:         #fca5a5;   /* reject  */
--text:         rgba(255,255,255,0.90);
--text-muted:   rgba(255,255,255,0.35);

/* Typography */
--font-body: 'Inter', system-ui, sans-serif;
--font-mono: 'Fira Code', monospace;

/* Fonts loaded via Google Fonts in globals.css */
```

---

## Layout

No hay Topbar. La información de estado (In Queue, Review, Today) aparece dentro del `<main>` de cada página de listado, en la misma fila que el heading de la página.

```
┌─ Sidebar (glass, w=200px) ──┬─ Main (transparent) ───────────────────────┐
│                             │                                              │
│  bort  (logo, violet)       │  Pending Review  [12]  ·  [Queue 3]  [Today 5] │
│                             │  ─────────────────────────────────────────  │
│  Queue          nav pill    │  ┌─ glass card ──────────────────────────┐  │
│  Published      nav pill    │  │ thumb | título | meta                 │  │
│  Rejected       nav pill    │  │ [Approve]  [Reject]  [Preview]        │  │
│  Settings       nav pill    │  └───────────────────────────────────────┘  │
│                             │  ┌─ glass card ──────────────────────────┐  │
│  [spacer, flex-grow]        │  │ ...                                   │  │
│                             │  └───────────────────────────────────────┘  │
│  ┌─ bot pill (bottom) ──┐   │                                              │
│  │ ● did-you-know  ▾   │   │                                              │
│  └────────────────────┘   │                                              │
└─────────────────────────────┴──────────────────────────────────────────────┘
```

---

## Component Specs

### `globals.css`

- Remove current font imports (Syne, DM Sans, JetBrains Mono)
- Add Google Fonts: Inter (300/400/500/600/700) + Fira Code (400/500/600/700)
- Replace all CSS custom properties with the glass token set above
- `body`: `background: var(--bg-gradient); background-attachment: fixed;`
- Scrollbar: 4px, `rgba(139,92,246,0.3)` thumb
- Keep the `@keyframes pulse` animation

### `App.tsx`

- Remove `<Topbar />` from the JSX entirely
- Remove inline `background` from the outer div — body gradient shows through
- The layout becomes `display: flex; height: 100vh` with only `<Sidebar>` + `<Routes>` side by side (no column flex needed)

### `Topbar.tsx`

- **Deleted** — component no longer used. File can be removed.

### `Pending.tsx` stat pills (moved from Topbar)

The WebSocket status data (`fetchSystemStatus` + `useWebSocket`) moves into `Pending.tsx`, since that is the primary landing page and the natural home for queue stats.

Stats appear as a row of glass pills in the page header, right-aligned next to the page title:
```
Pending Review  [12 videos]              [Queue 3]  [Review 12]  [Today 5]
```
- Each stat pill: `background: rgba(255,255,255,0.05)`, `border: 1px solid rgba(255,255,255,0.08)`, `border-radius: 999px`, padding `0.2rem 0.75rem`
- Label: `var(--font-mono)`, 0.6rem, `var(--text-muted)`
- Value: `var(--font-mono)`, 0.85rem, color varies (text / amber / emerald)
- Published, Rejected, Settings pages show no stat pills (they don't need them)

### `Sidebar.tsx`

Complete rewrite of styles (logic unchanged except bot-selector).

**Structure:**
```
<nav>
  <Logo>bort</Logo>

  <NavSection>           ← no label, just the 4 nav pills
    NavPill x4
  </NavSection>

  <spacer flex-grow />

  <BotSelector />        ← bottom of sidebar
</nav>
```

**NavPill** (replaces current NavLink style):
- Inactive: `background: transparent`, `color: var(--text-muted)`, no border
- Active: `background: var(--glass-bg-active)`, `border: 1px solid var(--glass-border-active)`, `color: #c4b5fd`, `border-radius: 8px`
- Hover (inactive): `background: rgba(255,255,255,0.04)`
- Transition: `all 0.18s`
- Active dot: 6px circle, `background: var(--violet)`, only visible when active

**BotSelector:**
- Single pill at the bottom: `background: var(--glass-bg)`, `border: 1px solid var(--glass-border)`, `border-radius: 8px`, padding `0.55rem 0.75rem`
- Shows: active dot (animated pulse, emerald) + bot name + `▾` chevron
- On click: toggles a popover **above** the pill (CSS `position: absolute; bottom: 100%`) listing other bots and a "+ New bot" row
- Popover: `background: rgba(15,10,30,0.92)`, `backdrop-filter: blur(20px)`, `border: 1px solid var(--glass-border)`, `border-radius: 10px`
- Popover items: bot name rows + a dashed "+ New bot" row at bottom
- State: `useState` for open/close; close on outside click (`useEffect` with document listener)
- No localStorage needed (ephemeral open/close state is fine)

**Remove entirely:** the Services section and the AddBot/BotItem/ServiceRow sub-components (replaced by BotSelector).

### `VideoCard.tsx`

- Card: `background: var(--glass-bg)`, `backdrop-filter: blur(var(--glass-blur))`, `border: 1px solid var(--glass-border)`, `border-radius: 12px`
- Top shimmer via `::before` pseudoelement — cannot use `::before` in inline styles in React, so implement as a positioned inner `<div>` with `height: 1px`, `background: linear-gradient(90deg, transparent, var(--violet-glow), transparent)` at the top of the card
- Hover: `background: var(--glass-bg-hover)`, `border-color: rgba(139,92,246,0.25)`
- Thumbnail placeholder: `background: rgba(139,92,246,0.12)`, violet play triangle
- Title: `var(--font-body)`, 0.78rem, `var(--text)`
- YT title: `var(--font-mono)`, 0.62rem, `var(--violet-light)`
- Meta row: `var(--font-mono)`, 0.6rem, `var(--text-muted)`
- Buttons:
  - Approve: `background: rgba(110,231,183,0.08)`, `border: 1px solid rgba(110,231,183,0.25)`, `color: var(--emerald)`
  - Reject: `background: rgba(252,165,165,0.08)`, `border: 1px solid rgba(252,165,165,0.25)`, `color: var(--rose)`
  - Preview: `background: rgba(255,255,255,0.04)`, `border: 1px solid rgba(255,255,255,0.10)`, `color: var(--text-muted)`

### `Pending.tsx`

- `<main>` background: `transparent`
- Header row: flex, space-between — left side has page title + video count pill; right side has the 3 stat pills (Queue, Review, Today) pulled from WebSocket
- Page heading: `var(--font-body)`, 1rem, weight 600, `var(--text)`
- Count badge (video count): glass pill — `background: rgba(139,92,246,0.15)`, `border: 1px solid rgba(139,92,246,0.3)`, `color: var(--violet-light)`, `border-radius: 999px`

### `Published.tsx` / `Rejected.tsx`

- `<main>` background: `transparent`
- Page heading + video count pill only (no stat pills)

### `Settings.tsx`

- `<main>` background: `transparent`
- Each bot card: `background: var(--glass-bg)`, `backdrop-filter: blur(var(--glass-blur))`, `border: 1px solid var(--glass-border)`, `border-radius: 12px`
- Section dividers: `border-bottom: 1px solid rgba(255,255,255,0.06)`
- `<textarea>` / `<input>`: `background: rgba(255,255,255,0.04)`, `border: 1px solid rgba(255,255,255,0.10)`, focus `border-color: rgba(139,92,246,0.5)`, outline none, `color: var(--text)`, `font-family: var(--font-body)`
- Privacy toggle buttons: same glass pill pattern as nav pills
- Save button: `background: rgba(139,92,246,0.15)`, `border: 1px solid rgba(139,92,246,0.35)`, `color: var(--violet-light)`

---

## Files Changed

| File | Type of change |
|---|---|
| `dashboard/src/styles/globals.css` | Full rewrite |
| `dashboard/src/App.tsx` | Remove Topbar + inline bg color |
| `dashboard/src/components/Topbar.tsx` | **Deleted** |
| `dashboard/src/components/Sidebar.tsx` | Full rewrite (new BotSelector component) |
| `dashboard/src/components/VideoCard.tsx` | Style rewrite |
| `dashboard/src/pages/Pending.tsx` | bg transparent + stat pills (absorbe WebSocket de Topbar) |
| `dashboard/src/pages/Published.tsx` | bg transparent + count pill |
| `dashboard/src/pages/Rejected.tsx` | bg transparent + count pill |
| `dashboard/src/pages/Settings.tsx` | Style rewrite |

**No backend changes. No API changes. No new dependencies.**

---

## Out of Scope

- Animations beyond hover transitions and the existing pulse
- Dark/light mode toggle (dark only, as per design)
- Mobile/responsive layout (dashboard is desktop-only)
- Any logic changes outside BotSelector open/close state
