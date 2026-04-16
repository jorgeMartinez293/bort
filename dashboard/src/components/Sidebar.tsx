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
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
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
            left: 0,
            right: 0,
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
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
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
                  width: 5,
                  height: 5,
                  borderRadius: '50%',
                  background: bot.active === 1 ? 'var(--emerald)' : 'var(--text-muted)',
                  flexShrink: 0,
                  animation: bot.active === 1 ? 'pulse 2s ease-in-out infinite' : 'none',
                }} />
                {bot.name}
              </div>
            ))}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
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
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
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
            width: 5,
            height: 5,
            borderRadius: '50%',
            background: 'var(--emerald)',
            flexShrink: 0,
            animation: 'pulse 2s ease-in-out infinite',
          }} />
          <span style={{
            flex: 1,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
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
