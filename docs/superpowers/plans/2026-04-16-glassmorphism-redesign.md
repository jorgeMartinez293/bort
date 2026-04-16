# Glassmorphism Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace el tema dark-blue plano del dashboard por un estilo Glassmorphism Dark con paneles de vidrio esmerilado sobre un fondo de gradiente radial violet fijo.

**Architecture:** Todos los cambios son visuales (CSS + inline styles en React). El fondo radial vive en `body` con `background-attachment: fixed` para que los paneles semitransparentes muestren el gradiente a través del blur. La lógica WebSocket que estaba en `Topbar` se mueve a `Pending.tsx`. `Topbar.tsx` se elimina.

**Tech Stack:** React, React Router, inline styles + CSS custom properties, Google Fonts (Inter + Fira Code)

---

## File Map

| File | Acción |
|---|---|
| `dashboard/src/styles/globals.css` | Reescritura completa — tokens glass, fuentes, body gradient |
| `dashboard/src/App.tsx` | Eliminar `<Topbar>`, simplificar layout |
| `dashboard/src/components/Topbar.tsx` | Eliminar archivo |
| `dashboard/src/components/Sidebar.tsx` | Reescritura completa — nav pills, BotSelector |
| `dashboard/src/components/VideoCard.tsx` | Reescritura de estilos — glass card, shimmer, botones |
| `dashboard/src/pages/Pending.tsx` | Transparente + stat pills (absorbe WebSocket) |
| `dashboard/src/pages/Published.tsx` | Transparente + count pill |
| `dashboard/src/pages/Rejected.tsx` | Transparente + count pill |
| `dashboard/src/pages/Settings.tsx` | Glass cards + textarea/button styles |

---

### Task 1: globals.css — tokens glass y fuentes

**Files:**
- Modify: `dashboard/src/styles/globals.css`

- [ ] **Step 1: Reemplazar globals.css completo**

```css
/* dashboard/src/styles/globals.css */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Fira+Code:wght@400;500;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  /* Glass surfaces */
  --glass-bg:            rgba(255,255,255,0.06);
  --glass-bg-hover:      rgba(139,92,246,0.08);
  --glass-bg-active:     rgba(139,92,246,0.18);
  --glass-border:        rgba(255,255,255,0.10);
  --glass-border-active: rgba(139,92,246,0.30);
  --glass-blur:          20px;
  --glass-blur-sm:       12px;

  /* Palette */
  --violet:       #8b5cf6;
  --violet-light: #a78bfa;
  --violet-glow:  rgba(139,92,246,0.40);
  --emerald:      #6ee7b7;
  --rose:         #fca5a5;
  --amber:        #fbbf24;
  --text:         rgba(255,255,255,0.90);
  --text-muted:   rgba(255,255,255,0.35);

  /* Typography */
  --font-body: 'Inter', system-ui, sans-serif;
  --font-mono: 'Fira Code', monospace;
}

body {
  background:
    radial-gradient(ellipse 80% 60% at 70% 30%, rgba(139,92,246,0.35) 0%, transparent 60%),
    radial-gradient(ellipse 60% 50% at 20% 80%,  rgba(99,102,241,0.25)  0%, transparent 55%),
    radial-gradient(ellipse 50% 40% at 90% 90%,  rgba(168,85,247,0.20)  0%, transparent 50%),
    #0f0a1e;
  background-attachment: fixed;
  color: var(--text);
  font-family: var(--font-body);
  min-height: 100vh;
}

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(139,92,246,0.3); border-radius: 2px; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.4; }
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/src/styles/globals.css
git commit -m "style: replace globals.css with glass design tokens and Inter/Fira Code fonts"
```

---

### Task 2: App.tsx — eliminar Topbar, simplificar layout

**Files:**
- Modify: `dashboard/src/App.tsx`

- [ ] **Step 1: Reescribir App.tsx**

```tsx
// dashboard/src/App.tsx
import './styles/globals.css'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Sidebar }   from './components/Sidebar'
import { Pending }   from './pages/Pending'
import { Published } from './pages/Published'
import { Rejected }  from './pages/Rejected'
import { Settings }  from './pages/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
        <Sidebar />
        <Routes>
          <Route path="/"           element={<Pending />} />
          <Route path="/published"  element={<Published />} />
          <Route path="/rejected"   element={<Rejected />} />
          <Route path="/settings"   element={<Settings />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
```

- [ ] **Step 2: Eliminar Topbar.tsx**

```bash
rm dashboard/src/components/Topbar.tsx
```

- [ ] **Step 3: Commit**

```bash
git add dashboard/src/App.tsx
git add -u dashboard/src/components/Topbar.tsx
git commit -m "feat: remove Topbar component, simplify App layout to sidebar + routes"
```

---

### Task 3: Sidebar.tsx — nav pills + BotSelector

**Files:**
- Modify: `dashboard/src/components/Sidebar.tsx`

Nota: `Bot.active` es `number` (0 | 1) en la API, no boolean.

- [ ] **Step 1: Reescribir Sidebar.tsx**

```tsx
// dashboard/src/components/Sidebar.tsx
import { useEffect, useRef, useState } from 'react'
import { NavLink } from 'react-router-dom'
import { fetchBots } from '../api/client'
import type { Bot } from '../api/client'

const NAV = [
  { to: '/',          label: 'Queue' },
  { to: '/published', label: 'Published' },
  { to: '/rejected',  label: 'Rejected' },
  { to: '/settings',  label: 'Settings' },
]

export function Sidebar() {
  const [bots, setBots] = useState<Bot[]>([])
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetchBots().then(setBots).catch(() => {})
  }, [])

  useEffect(() => {
    if (!open) return
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  const activeBot = bots.find(b => b.active === 1) ?? bots[0]

  return (
    <nav style={{
      width: 200,
      flexShrink: 0,
      display: 'flex',
      flexDirection: 'column',
      padding: '1.5rem 1rem',
      background: 'rgba(255,255,255,0.04)',
      backdropFilter: 'blur(16px)',
      WebkitBackdropFilter: 'blur(16px)',
      borderRight: '1px solid rgba(255,255,255,0.08)',
    }}>
      {/* Logo */}
      <div style={{
        fontFamily: 'var(--font-body)',
        fontWeight: 700,
        fontSize: '1.2rem',
        letterSpacing: '-0.03em',
        color: 'var(--violet-light)',
        marginBottom: '2rem',
        paddingLeft: '0.25rem',
      }}>
        bort
      </div>

      {/* Nav pills */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.2rem' }}>
        {NAV.map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              padding: '0.55rem 0.75rem',
              borderRadius: 8,
              fontSize: '0.82rem',
              fontWeight: 500,
              textDecoration: 'none',
              transition: 'all 0.18s',
              background: isActive ? 'var(--glass-bg-active)' : 'transparent',
              border: isActive
                ? '1px solid var(--glass-border-active)'
                : '1px solid transparent',
              color: isActive ? '#c4b5fd' : 'var(--text-muted)',
            })}
          >
            {({ isActive }) => (
              <>
                <span style={{
                  width: 6, height: 6, borderRadius: '50%',
                  background: 'var(--violet)',
                  flexShrink: 0,
                  opacity: isActive ? 1 : 0,
                  transition: 'opacity 0.18s',
                }} />
                {label}
              </>
            )}
          </NavLink>
        ))}
      </div>

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* Bot selector */}
      <div ref={ref} style={{ position: 'relative' }}>
        {open && (
          <div style={{
            position: 'absolute',
            bottom: 'calc(100% + 8px)',
            left: 0, right: 0,
            background: 'rgba(15,10,30,0.92)',
            backdropFilter: 'blur(20px)',
            WebkitBackdropFilter: 'blur(20px)',
            border: '1px solid var(--glass-border)',
            borderRadius: 10,
            overflow: 'hidden',
            zIndex: 50,
          }}>
            {bots.map(bot => (
              <div
                key={bot.id}
                style={{
                  display: 'flex', alignItems: 'center', gap: '0.5rem',
                  padding: '0.55rem 0.75rem',
                  fontSize: '0.78rem',
                  color: bot.active === 1 ? 'var(--text)' : 'var(--text-muted)',
                  cursor: 'pointer',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={e => (e.currentTarget.style.background = 'rgba(139,92,246,0.1)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                <span style={{
                  width: 5, height: 5, borderRadius: '50%',
                  background: bot.active === 1 ? 'var(--emerald)' : 'var(--text-muted)',
                  flexShrink: 0,
                  animation: bot.active === 1 ? 'pulse 2s ease-in-out infinite' : 'none',
                }} />
                {bot.name}
              </div>
            ))}
            <div
              style={{
                display: 'flex', alignItems: 'center', gap: '0.5rem',
                padding: '0.55rem 0.75rem',
                fontSize: '0.78rem',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                borderTop: '1px dashed rgba(255,255,255,0.08)',
                transition: 'background 0.15s',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.04)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              <span style={{ fontSize: '0.9rem', lineHeight: 1 }}>+</span>
              New bot
            </div>
          </div>
        )}

        <button
          onClick={() => setOpen(v => !v)}
          style={{
            width: '100%',
            display: 'flex', alignItems: 'center', gap: '0.5rem',
            padding: '0.55rem 0.75rem',
            background: 'var(--glass-bg)',
            border: '1px solid var(--glass-border)',
            borderRadius: 8,
            color: 'var(--text)',
            fontSize: '0.78rem',
            fontWeight: 500,
            fontFamily: 'var(--font-body)',
            cursor: 'pointer',
            textAlign: 'left',
            transition: 'background 0.18s',
          }}
        >
          <span style={{
            width: 5, height: 5, borderRadius: '50%',
            background: 'var(--emerald)',
            flexShrink: 0,
            animation: 'pulse 2s ease-in-out infinite',
          }} />
          <span style={{
            flex: 1,
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }}>
            {activeBot?.name ?? 'No bots'}
          </span>
          <span style={{
            fontSize: '0.65rem',
            color: 'var(--text-muted)',
            display: 'inline-block',
            transform: open ? 'rotate(180deg)' : 'none',
            transition: 'transform 0.18s',
          }}>▾</span>
        </button>
      </div>
    </nav>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/src/components/Sidebar.tsx
git commit -m "feat: redesign Sidebar with glass nav pills and BotSelector popover"
```

---

### Task 4: VideoCard.tsx — glass card con shimmer

**Files:**
- Modify: `dashboard/src/components/VideoCard.tsx`

- [ ] **Step 1: Reescribir VideoCard.tsx**

```tsx
// dashboard/src/components/VideoCard.tsx
import { useState } from 'react'
import type { Video } from '../api/client'

interface Props {
  video: Video
  onAction: (id: number, status: 'approved' | 'rejected') => void
}

export function VideoCard({ video, onAction }: Props) {
  const [previewing, setPreviewing] = useState(false)
  const [hovered, setHovered] = useState(false)

  const age = () => {
    const diff = Date.now() - new Date(video.created_at).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 60) return `${mins}m ago`
    return `${Math.floor(mins / 60)}h ago`
  }

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        position: 'relative',
        background: hovered ? 'var(--glass-bg-hover)' : 'var(--glass-bg)',
        backdropFilter: 'blur(var(--glass-blur))',
        WebkitBackdropFilter: 'blur(var(--glass-blur))',
        border: `1px solid ${hovered ? 'rgba(139,92,246,0.25)' : 'var(--glass-border)'}`,
        borderRadius: 12,
        overflow: 'hidden',
        marginBottom: '0.75rem',
        transition: 'background 0.2s, border-color 0.2s',
      }}
    >
      {/* Top shimmer line */}
      <div style={{
        height: 1,
        background: 'linear-gradient(90deg, transparent, var(--violet-glow), transparent)',
      }} />

      <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-start', padding: '1rem' }}>
        {/* Thumbnail */}
        <div
          onClick={() => setPreviewing(v => !v)}
          style={{
            width: 54, height: 96, flexShrink: 0,
            background: 'rgba(139,92,246,0.12)',
            border: '1px solid rgba(139,92,246,0.2)',
            borderRadius: 8,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer',
          }}
        >
          <div style={{
            width: 0, height: 0,
            borderLeft: '14px solid var(--violet-light)',
            borderTop: '8px solid transparent',
            borderBottom: '8px solid transparent',
            marginLeft: 3,
            opacity: 0.7,
          }} />
        </div>

        {/* Content */}
        <div style={{ flex: 1 }}>
          <div style={{
            fontSize: '0.82rem', fontWeight: 500, color: 'var(--text)',
            marginBottom: '0.2rem', lineHeight: 1.45,
          }}>
            {video.raw_title}
          </div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.65rem',
            color: 'var(--violet-light)', marginBottom: '0.35rem',
          }}>
            yt: {video.youtube_title}
          </div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.62rem',
            color: 'var(--text-muted)',
            display: 'flex', gap: '0.75rem', flexWrap: 'wrap',
            marginBottom: '0.65rem',
          }}>
            <span>r/{video.subreddit}</span>
            <span>·</span>
            <span>{video.upvotes.toLocaleString()} upvotes</span>
            <span>·</span>
            <span>{Math.round(video.duration_secs)}s</span>
            <span>·</span>
            <span>{age()}</span>
          </div>

          {previewing && (
            <video
              src={`/api/videos/${video.id}/stream`}
              controls autoPlay
              style={{ width: '100%', maxWidth: 300, borderRadius: 6, marginBottom: '0.65rem' }}
            />
          )}

          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {([
              {
                label: 'Approve', status: 'approved' as const,
                bg: 'rgba(110,231,183,0.08)', color: 'var(--emerald)',
                border: 'rgba(110,231,183,0.25)',
              },
              {
                label: 'Reject', status: 'rejected' as const,
                bg: 'rgba(252,165,165,0.08)', color: 'var(--rose)',
                border: 'rgba(252,165,165,0.25)',
              },
            ]).map(({ label, status, bg, color, border }) => (
              <button
                key={label}
                onClick={() => onAction(video.id, status)}
                style={{
                  fontFamily: 'var(--font-mono)', fontSize: '0.68rem', fontWeight: 500,
                  letterSpacing: '0.04em', padding: '0.3rem 0.85rem',
                  borderRadius: 6, border: `1px solid ${border}`,
                  background: bg, color, cursor: 'pointer',
                  textTransform: 'uppercase',
                  backdropFilter: 'blur(8px)',
                  transition: 'opacity 0.15s',
                }}
              >
                {label}
              </button>
            ))}
            <button
              onClick={() => setPreviewing(v => !v)}
              style={{
                fontFamily: 'var(--font-mono)', fontSize: '0.68rem', fontWeight: 500,
                letterSpacing: '0.04em', padding: '0.3rem 0.85rem',
                borderRadius: 6, border: '1px solid rgba(255,255,255,0.10)',
                background: 'rgba(255,255,255,0.04)', color: 'var(--text-muted)',
                cursor: 'pointer', textTransform: 'uppercase',
              }}
            >
              {previewing ? 'Hide' : 'Preview'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/src/components/VideoCard.tsx
git commit -m "style: redesign VideoCard with glass surface, shimmer line, and frosted buttons"
```

---

### Task 5: Pending.tsx — transparente + stat pills con WebSocket

**Files:**
- Modify: `dashboard/src/pages/Pending.tsx`

La lógica de `fetchSystemStatus` + `useWebSocket` que estaba en el Topbar eliminado se mueve aquí.

- [ ] **Step 1: Reescribir Pending.tsx**

```tsx
// dashboard/src/pages/Pending.tsx
import { useEffect, useState } from 'react'
import { fetchVideos, updateVideoStatus, fetchSystemStatus, useWebSocket } from '../api/client'
import type { Video, SystemStatus } from '../api/client'
import { VideoCard } from '../components/VideoCard'

function StatPill({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      background: 'rgba(255,255,255,0.05)',
      border: '1px solid rgba(255,255,255,0.08)',
      borderRadius: 999,
      padding: '0.2rem 0.75rem',
    }}>
      <span style={{
        fontFamily: 'var(--font-mono)', fontSize: '0.55rem',
        color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase',
      }}>
        {label}
      </span>
      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', fontWeight: 500, color }}>
        {value}
      </span>
    </div>
  )
}

export function Pending() {
  const [videos, setVideos] = useState<Video[]>([])
  const [status, setStatus] = useState<SystemStatus | null>(null)

  useEffect(() => {
    fetchVideos('pending_review').then(setVideos).catch(() => {})
    fetchSystemStatus().then(setStatus).catch(() => {})
    const ws = useWebSocket((data: unknown) => {
      const msg = data as { type: string; queues: { tts: number; render: number }; pending_review: number }
      if (msg.type === 'status') {
        setStatus(prev => prev ? {
          ...prev,
          queues: { ...prev.queues, tts: msg.queues.tts, render: msg.queues.render },
          counts: { ...prev.counts, pending_review: msg.pending_review },
        } : prev)
      }
    })
    return () => ws.close()
  }, [])

  const handleAction = async (id: number, newStatus: 'approved' | 'rejected') => {
    await updateVideoStatus(id, newStatus)
    setVideos(vs => vs.filter(v => v.id !== id))
  }

  const queueTotal = (status?.queues.tts ?? 0) + (status?.queues.render ?? 0)

  return (
    <main style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', background: 'transparent' }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: '0.75rem',
        marginBottom: '1.25rem', flexWrap: 'wrap',
      }}>
        <span style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text)' }}>
          Pending Review
        </span>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '0.68rem', color: 'var(--violet-light)',
          background: 'rgba(139,92,246,0.15)', border: '1px solid rgba(139,92,246,0.3)',
          padding: '0.15rem 0.6rem', borderRadius: 999,
        }}>
          {videos.length} videos
        </span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.5rem' }}>
          <StatPill label="Queue"  value={queueTotal}                         color="var(--text)" />
          <StatPill label="Review" value={status?.counts.pending_review ?? 0} color="var(--amber)" />
          <StatPill label="Today"  value={status?.counts.published_today ?? 0} color="var(--emerald)" />
        </div>
      </div>
      {videos.length === 0 && (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No videos pending review.</p>
      )}
      {videos.map(v => <VideoCard key={v.id} video={v} onAction={handleAction} />)}
    </main>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/src/pages/Pending.tsx
git commit -m "feat: move WebSocket stats to Pending page as glass stat pills"
```

---

### Task 6: Published.tsx — transparente + count pill

**Files:**
- Modify: `dashboard/src/pages/Published.tsx`

- [ ] **Step 1: Reescribir Published.tsx**

```tsx
// dashboard/src/pages/Published.tsx
import { useEffect, useState } from 'react'
import { fetchVideos } from '../api/client'
import type { Video } from '../api/client'
import { VideoCard } from '../components/VideoCard'

export function Published() {
  const [videos, setVideos] = useState<Video[]>([])
  useEffect(() => { fetchVideos('uploaded').then(setVideos).catch(() => {}) }, [])

  return (
    <main style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', background: 'transparent' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
        <span style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text)' }}>Published</span>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '0.68rem', color: 'var(--violet-light)',
          background: 'rgba(139,92,246,0.15)', border: '1px solid rgba(139,92,246,0.3)',
          padding: '0.15rem 0.6rem', borderRadius: 999,
        }}>
          {videos.length} videos
        </span>
      </div>
      {videos.length === 0 && (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No published videos yet.</p>
      )}
      {videos.map(v => <VideoCard key={v.id} video={v} onAction={() => {}} />)}
    </main>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/src/pages/Published.tsx
git commit -m "style: Published page — transparent bg, glass count pill"
```

---

### Task 7: Rejected.tsx — transparente + count pill

**Files:**
- Modify: `dashboard/src/pages/Rejected.tsx`

- [ ] **Step 1: Reescribir Rejected.tsx**

```tsx
// dashboard/src/pages/Rejected.tsx
import { useEffect, useState } from 'react'
import { fetchVideos } from '../api/client'
import type { Video } from '../api/client'
import { VideoCard } from '../components/VideoCard'

export function Rejected() {
  const [videos, setVideos] = useState<Video[]>([])
  useEffect(() => { fetchVideos('rejected').then(setVideos).catch(() => {}) }, [])

  return (
    <main style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', background: 'transparent' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
        <span style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text)' }}>Rejected</span>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '0.68rem', color: 'var(--violet-light)',
          background: 'rgba(139,92,246,0.15)', border: '1px solid rgba(139,92,246,0.3)',
          padding: '0.15rem 0.6rem', borderRadius: 999,
        }}>
          {videos.length} videos
        </span>
      </div>
      {videos.length === 0 && (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No rejected videos.</p>
      )}
      {videos.map(v => <VideoCard key={v.id} video={v} onAction={() => {}} />)}
    </main>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/src/pages/Rejected.tsx
git commit -m "style: Rejected page — transparent bg, glass count pill"
```

---

### Task 8: Settings.tsx — glass cards + form styles

**Files:**
- Modify: `dashboard/src/pages/Settings.tsx`

Los textareas necesitan gestión de focus via `onFocus`/`onBlur` porque los inline styles no soportan `:focus`. Se usa un helper `useTextareaFocus`.

- [ ] **Step 1: Reescribir Settings.tsx**

```tsx
// dashboard/src/pages/Settings.tsx
import { useEffect, useState } from 'react'
import type { Bot } from '../api/client'
import { fetchBots, updateBotYouTube } from '../api/client'

interface BotDraft {
  description: string
  tagsRaw: string
  privacy: 'private' | 'public'
}

interface SaveState {
  saving: boolean
  saved: boolean
  error: string | null
}

function parseTags(yt_tags: string): string {
  try {
    const arr: string[] = JSON.parse(yt_tags || '[]')
    return arr.join('\n')
  } catch {
    return ''
  }
}

function GlassTextarea({
  rows, placeholder, value, onChange,
}: {
  rows: number
  placeholder: string
  value: string
  onChange: (v: string) => void
}) {
  const [focused, setFocused] = useState(false)
  return (
    <textarea
      rows={rows}
      placeholder={placeholder}
      value={value}
      onChange={e => onChange(e.target.value)}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
      style={{
        width: '100%',
        background: 'rgba(255,255,255,0.04)',
        border: `1px solid ${focused ? 'rgba(139,92,246,0.5)' : 'rgba(255,255,255,0.10)'}`,
        borderRadius: 8,
        color: 'var(--text)',
        fontFamily: 'var(--font-body)',
        fontSize: '0.82rem',
        padding: '0.6rem 0.75rem',
        resize: 'vertical',
        outline: 'none',
        lineHeight: 1.5,
        transition: 'border-color 0.18s',
      }}
    />
  )
}

export function Settings() {
  const [bots, setBots] = useState<Bot[]>([])
  const [drafts, setDrafts] = useState<Record<number, BotDraft>>({})
  const [saveState, setSaveState] = useState<Record<number, SaveState>>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchBots().then(data => {
      setBots(data)
      const initial: Record<number, BotDraft> = {}
      data.forEach(b => {
        initial[b.id] = {
          description: b.yt_description || '',
          tagsRaw: parseTags(b.yt_tags),
          privacy: (b.yt_privacy as 'private' | 'public') || 'private',
        }
      })
      setDrafts(initial)
      setLoading(false)
    })
  }, [])

  function updateDraft(botId: number, patch: Partial<BotDraft>) {
    setDrafts(prev => ({ ...prev, [botId]: { ...prev[botId], ...patch } }))
  }

  async function save(bot: Bot) {
    const draft = drafts[bot.id]
    if (!draft) return
    setSaveState(prev => ({ ...prev, [bot.id]: { saving: true, saved: false, error: null } }))
    try {
      const tags = draft.tagsRaw.split('\n').map(t => t.trim()).filter(Boolean)
      await updateBotYouTube(bot.id, {
        yt_description: draft.description,
        yt_tags: tags,
        yt_privacy: draft.privacy,
      })
      setSaveState(prev => ({ ...prev, [bot.id]: { saving: false, saved: true, error: null } }))
      setTimeout(() => {
        setSaveState(prev => ({ ...prev, [bot.id]: { ...prev[bot.id], saved: false } }))
      }, 2000)
    } catch (e) {
      setSaveState(prev => ({ ...prev, [bot.id]: { saving: false, saved: false, error: String(e) } }))
    }
  }

  const labelStyle: React.CSSProperties = {
    fontFamily: 'var(--font-mono)',
    fontSize: '0.65rem',
    color: 'var(--text-muted)',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    marginBottom: '0.4rem',
    display: 'block',
  }

  return (
    <main style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', background: 'transparent' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
        <span style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text)' }}>Settings</span>
      </div>

      {loading && (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>Loading bots…</p>
      )}
      {!loading && bots.length === 0 && (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>No bots found.</p>
      )}

      {bots.map(bot => {
        const draft = drafts[bot.id]
        const ss = saveState[bot.id] || { saving: false, saved: false, error: null }
        if (!draft) return null

        return (
          <div
            key={bot.id}
            style={{
              background: 'var(--glass-bg)',
              backdropFilter: 'blur(var(--glass-blur))',
              WebkitBackdropFilter: 'blur(var(--glass-blur))',
              border: '1px solid var(--glass-border)',
              borderRadius: 12,
              overflow: 'hidden',
              marginBottom: '1rem',
            }}
          >
            {/* Shimmer line */}
            <div style={{
              height: 1,
              background: 'linear-gradient(90deg, transparent, var(--violet-glow), transparent)',
            }} />

            <div style={{ padding: '1.25rem' }}>
              {/* Bot header */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
                <span style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text)' }}>
                  {bot.name}
                </span>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '0.62rem', letterSpacing: '0.05em',
                  background: 'rgba(139,92,246,0.12)', color: 'var(--violet-light)',
                  border: '1px solid rgba(139,92,246,0.25)', borderRadius: 4,
                  padding: '0.15rem 0.5rem', textTransform: 'uppercase',
                }}>
                  {bot.niche}
                </span>
                <span style={{
                  fontFamily: 'var(--font-mono)', fontSize: '0.62rem', marginLeft: 'auto',
                  color: bot.active === 1 ? 'var(--emerald)' : 'var(--text-muted)',
                }}>
                  {bot.active === 1 ? '● active' : '○ inactive'}
                </span>
              </div>

              {/* Section label */}
              <div style={{
                fontFamily: 'var(--font-mono)', fontSize: '0.6rem', letterSpacing: '0.08em',
                color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '1rem',
                borderBottom: '1px solid rgba(255,255,255,0.06)', paddingBottom: '0.4rem',
              }}>
                YouTube
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {/* Description */}
                <div>
                  <label style={labelStyle}>Description</label>
                  <GlassTextarea
                    rows={4}
                    placeholder="Leave empty for no description…"
                    value={draft.description}
                    onChange={v => updateDraft(bot.id, { description: v })}
                  />
                </div>

                {/* Tags */}
                <div>
                  <label style={labelStyle}>Tags — one per line</label>
                  <GlassTextarea
                    rows={4}
                    placeholder={'funny\nreddit\nshorts'}
                    value={draft.tagsRaw}
                    onChange={v => updateDraft(bot.id, { tagsRaw: v })}
                  />
                </div>

                {/* Privacy */}
                <div>
                  <label style={labelStyle}>Privacy</label>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    {(['private', 'public'] as const).map(option => (
                      <button
                        key={option}
                        onClick={() => updateDraft(bot.id, { privacy: option })}
                        style={{
                          fontFamily: 'var(--font-mono)', fontSize: '0.7rem', fontWeight: 500,
                          letterSpacing: '0.04em', padding: '0.35rem 1rem',
                          borderRadius: 6, textTransform: 'uppercase', cursor: 'pointer',
                          border: draft.privacy === option
                            ? '1px solid var(--glass-border-active)'
                            : '1px solid rgba(255,255,255,0.10)',
                          background: draft.privacy === option
                            ? 'var(--glass-bg-active)'
                            : 'rgba(255,255,255,0.04)',
                          color: draft.privacy === option ? '#c4b5fd' : 'var(--text-muted)',
                          transition: 'all 0.18s',
                        }}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Save */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <button
                    onClick={() => save(bot)}
                    disabled={ss.saving}
                    style={{
                      fontFamily: 'var(--font-mono)', fontSize: '0.7rem', fontWeight: 500,
                      letterSpacing: '0.04em', padding: '0.4rem 1.25rem',
                      borderRadius: 6, textTransform: 'uppercase',
                      cursor: ss.saving ? 'default' : 'pointer',
                      border: '1px solid rgba(139,92,246,0.35)',
                      background: 'rgba(139,92,246,0.15)', color: 'var(--violet-light)',
                      opacity: ss.saving ? 0.6 : 1,
                      transition: 'opacity 0.15s',
                    }}
                  >
                    {ss.saving ? 'Saving…' : 'Save'}
                  </button>
                  {ss.saved && (
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.68rem', color: 'var(--emerald)' }}>
                      ✓ Saved
                    </span>
                  )}
                  {ss.error && (
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.68rem', color: 'var(--rose)' }}>
                      Error: {ss.error}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )
      })}
    </main>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add dashboard/src/pages/Settings.tsx
git commit -m "style: redesign Settings with glass bot cards, focused textarea, glass buttons"
```

---

## Self-Review

**Spec coverage:**
- ✅ globals.css — tokens glass, Inter+Fira Code, body gradient fixed — Task 1
- ✅ Topbar eliminada — Task 2
- ✅ App.tsx simplificado — Task 2
- ✅ Sidebar — logo, nav pills, spacer, BotSelector con popover — Task 3
- ✅ BotSelector — fetchBots, active===1, popover encima, outside click — Task 3
- ✅ VideoCard — glass card, shimmer top, hover, botones frosted — Task 4
- ✅ Pending — transparente, stat pills, WebSocket absorbido — Task 5
- ✅ Published — transparente, count pill — Task 6
- ✅ Rejected — transparente, count pill — Task 7
- ✅ Settings — glass cards, shimmer, GlassTextarea con focus, privacy pills, save violet — Task 8

**Placeholder scan:** Sin TBD ni TODO. Código completo en todos los steps.

**Type consistency:**
- `Bot.active` usado como `=== 1` en Tasks 3, 8 (coincide con tipo `number` en client.ts)
- `useWebSocket` llamado dentro de `useEffect` (es factory, no hook de React — correcto)
- `SystemStatus` importado desde `../api/client` — definido en client.ts línea 34
- `StatPill` definido en Task 5 y usado solo en Task 5 — sin conflictos
- `GlassTextarea` definido y usado solo dentro de Settings.tsx — sin conflictos
- Tokens CSS: `--violet-glow`, `--glass-bg`, `--glass-bg-active`, `--glass-border`, `--glass-border-active`, `--glass-blur`, `--emerald`, `--rose`, `--amber`, `--violet-light`, `--text`, `--text-muted`, `--font-mono`, `--font-body` — todos definidos en Task 1
