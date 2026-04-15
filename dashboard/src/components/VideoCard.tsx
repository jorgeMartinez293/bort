// dashboard/src/components/VideoCard.tsx
import { useState } from 'react'
import type { Video } from '../api/client'

interface Props {
  video: Video
  onAction: (id: number, status: 'approved' | 'rejected') => void
}

export function VideoCard({ video, onAction }: Props) {
  const [previewing, setPreviewing] = useState(false)

  const age = () => {
    const diff = Date.now() - new Date(video.created_at).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 60) return `${mins}m ago`
    return `${Math.floor(mins / 60)}h ago`
  }

  return (
    <div
      style={{
        display: 'flex', gap: '1rem', alignItems: 'flex-start',
        background: 'var(--bg2)', border: '1px solid var(--border)',
        borderLeft: '3px solid transparent', borderRadius: '8px',
        padding: '1rem', marginBottom: '0.75rem',
        transition: 'border-color 0.2s, background 0.2s',
      }}
      onMouseEnter={e => (e.currentTarget.style.borderLeftColor = 'var(--accent)')}
      onMouseLeave={e => (e.currentTarget.style.borderLeftColor = 'transparent')}
    >
      <div style={{
        width: 54, height: 96, flexShrink: 0,
        background: 'var(--bg3)', border: '1px solid var(--border2)',
        borderRadius: 4, display: 'flex', alignItems: 'center', justifyContent: 'center',
        cursor: 'pointer',
      }} onClick={() => setPreviewing(v => !v)}>
        <div style={{ width: 0, height: 0, borderLeft: '14px solid var(--accent)', borderTop: '8px solid transparent', borderBottom: '8px solid transparent', opacity: 0.5, marginLeft: 3 }} />
      </div>

      <div style={{ flex: 1 }}>
        <div style={{ fontSize: '0.85rem', fontWeight: 500, color: 'var(--text)', marginBottom: '0.35rem', lineHeight: 1.4 }}>
          {video.cleaned_script.slice(0, 120)}{video.cleaned_script.length > 120 ? '…' : ''}
        </div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.68rem', color: 'var(--muted)', display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '0.65rem' }}>
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
            { label: 'Approve', status: 'approved' as const, color: 'rgba(0,201,167,0.12)', text: 'var(--accent2)', border: 'rgba(0,201,167,0.3)' },
            { label: 'Reject',  status: 'rejected' as const, color: 'rgba(232,64,74,0.1)',  text: 'var(--danger)', border: 'rgba(232,64,74,0.25)' },
          ] as const).map(({ label, status, color, text, border }) => (
            <button key={label} onClick={() => onAction(video.id, status)} style={{
              fontFamily: 'var(--font-mono)', fontSize: '0.7rem', fontWeight: 500,
              letterSpacing: '0.04em', padding: '0.35rem 0.85rem',
              borderRadius: 5, border: `1px solid ${border}`,
              background: color, color: text, cursor: 'pointer',
              textTransform: 'uppercase',
            }}>
              {label}
            </button>
          ))}
          <button onClick={() => setPreviewing(v => !v)} style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.7rem', fontWeight: 500,
            letterSpacing: '0.04em', padding: '0.35rem 0.85rem',
            borderRadius: 5, border: '1px solid var(--border2)',
            background: 'transparent', color: 'var(--muted)', cursor: 'pointer',
            textTransform: 'uppercase',
          }}>
            {previewing ? 'Hide' : 'Preview'}
          </button>
        </div>
      </div>
    </div>
  )
}
