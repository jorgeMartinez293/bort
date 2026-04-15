// dashboard/src/components/Sidebar.tsx
import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'

const NAV = [
  { to: '/',          label: 'Pending' },
  { to: '/published', label: 'Published' },
  { to: '/rejected',  label: 'Rejected' },
  { to: '/settings',  label: 'Settings' },
]

export function Sidebar() {
  return (
    <nav style={{
      width: 200, background: 'var(--bg2)',
      borderRight: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column',
      padding: '1.25rem 0', flexShrink: 0,
    }}>
      <Section label="Bots">
        <BotItem name="did-you-know" platforms="YT" active />
        <AddBot />
      </Section>
      <Section label="Services">
        {['Scraper','TTS Worker','Video Worker','Upload Worker','Redis'].map(s => (
          <ServiceRow key={s} name={s} up />
        ))}
      </Section>
      <Section label="Navigate">
        {NAV.map(({ to, label }) => (
          <NavLink key={to} to={to} end={to === '/'} style={({ isActive }) => ({
            display: 'block', padding: '0.45rem 0.75rem',
            fontSize: '0.8rem',
            color: isActive ? 'var(--accent)' : 'var(--muted)',
            borderLeft: isActive ? '2px solid var(--accent)' : '2px solid transparent',
            background: isActive ? 'rgba(79,126,247,0.07)' : 'transparent',
            paddingLeft: isActive ? '0.9rem' : '0.75rem',
            borderRadius: '6px', marginBottom: '0.1rem',
            textDecoration: 'none', transition: 'all 0.15s',
          })}>
            {label}
          </NavLink>
        ))}
      </Section>
    </nav>
  )
}

function Section({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div style={{ padding: '0 1rem', marginBottom: '1.5rem' }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.62rem', fontWeight: 500, color: 'var(--muted)', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '0.5rem', paddingLeft: '0.25rem' }}>
        {label}
      </div>
      {children}
    </div>
  )
}

function BotItem({ name, platforms, active }: { name: string; platforms: string; active: boolean }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.55rem 0.75rem', borderRadius: '6px', background: 'var(--bg3)', border: '1px solid var(--border2)', marginBottom: '0.2rem' }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: active ? 'var(--accent2)' : 'var(--muted)', flexShrink: 0, animation: active ? 'pulse 2s ease-in-out infinite' : 'none', display: 'inline-block' }} />
      <div>
        <div style={{ fontSize: '0.8rem', fontWeight: 500, color: 'var(--text)' }}>{name}</div>
        <div style={{ fontSize: '0.68rem', color: 'var(--muted)', fontFamily: 'var(--font-mono)' }}>{platforms}</div>
      </div>
    </div>
  )
}

function AddBot() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', padding: '0.45rem 0.75rem', marginTop: '0.2rem', fontSize: '0.75rem', color: 'var(--muted)', cursor: 'pointer', borderRadius: '6px', border: '1px dashed var(--border2)' }}>
      <span>+</span><span>New bot</span>
    </div>
  )
}

function ServiceRow({ name, up }: { name: string; up: boolean }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.25rem 0.25rem', fontSize: '0.75rem', color: 'var(--muted)' }}>
      <span style={{ width: 5, height: 5, borderRadius: '50%', background: up ? 'var(--accent2)' : 'var(--danger)', flexShrink: 0, display: 'inline-block' }} />
      {name}
    </div>
  )
}
