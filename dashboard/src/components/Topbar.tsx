// dashboard/src/components/Topbar.tsx
import { useEffect, useState } from 'react'
import { fetchSystemStatus, useWebSocket } from '../api/client'
import type { SystemStatus } from '../api/client'

export function Topbar() {
  const [status, setStatus] = useState<SystemStatus | null>(null)

  useEffect(() => {
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

  const queueTotal = (status?.queues.tts ?? 0) + (status?.queues.render ?? 0)

  return (
    <header style={{
      display: 'flex', alignItems: 'center', gap: '2rem',
      padding: '0 1.5rem', height: '52px',
      background: 'rgba(7,8,15,0.9)',
      borderBottom: '1px solid var(--border)',
      backdropFilter: 'blur(8px)',
      flexShrink: 0, position: 'sticky', top: 0, zIndex: 100,
    }}>
      <div style={{
        fontFamily: 'var(--font-disp)', fontWeight: 800, fontSize: '1.1rem',
        letterSpacing: '0.12em', color: 'var(--accent)', textTransform: 'uppercase',
        display: 'flex', alignItems: 'center', gap: '0.5rem',
      }}>
        <span style={{
          width: 6, height: 6, borderRadius: '50%', background: 'var(--accent2)',
          animation: 'pulse 2s ease-in-out infinite',
          display: 'inline-block',
        }} />
        Bort
      </div>
      <div style={{ display: 'flex', gap: '1.5rem', marginLeft: 'auto' }}>
        {[
          { label: 'In Queue',  value: queueTotal,                          color: 'var(--text)' },
          { label: 'Review',    value: status?.counts.pending_review ?? 0,  color: 'var(--warn)' },
          { label: 'Published', value: status?.counts.published_today ?? 0, color: 'var(--accent2)' },
        ].map(({ label, value, color }) => (
          <div key={label} style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.62rem', color: 'var(--muted)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>{label}</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.95rem', fontWeight: 500, color }}>{value}</span>
          </div>
        ))}
      </div>
    </header>
  )
}
