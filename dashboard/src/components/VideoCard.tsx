// dashboard/src/components/VideoCard.tsx
import { useState } from 'react'
import type { Video } from '../api/client'

interface Props {
  video: Video
  onAction: (id: number, status: 'approved' | 'rejected') => void
}

export function VideoCard({ video, onAction }: Props) {
  const [expanded, setExpanded] = useState(false)
  const [previewing, setPreviewing] = useState(false)
  const [hovered, setHovered] = useState(false)

  const age = () => {
    const diff = Date.now() - new Date(video.created_at).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 60) return `${mins}m ago`
    return `${Math.floor(mins / 60)}h ago`
  }

  function handleToggle() {
    if (expanded) setPreviewing(false)
    setExpanded(v => !v)
  }

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        position: 'relative',
        background: expanded
          ? 'rgba(139,92,246,0.07)'
          : hovered ? 'var(--glass-bg-hover)' : 'var(--glass-bg)',
        backdropFilter: 'blur(var(--glass-blur))',
        WebkitBackdropFilter: 'blur(var(--glass-blur))',
        border: `1px solid ${expanded || hovered ? 'rgba(139,92,246,0.25)' : 'var(--glass-border)'}`,
        borderRadius: 12, overflow: 'hidden', marginBottom: '0.75rem',
        transition: 'background 0.2s, border-color 0.2s',
      }}
    >
      {/* Top shimmer line */}
      <div style={{ height: 1, background: 'linear-gradient(90deg, transparent, var(--violet-glow), transparent)' }} />

      {/* Header row — tap/click to expand or collapse */}
      <div
        onClick={handleToggle}
        style={{ display: 'flex', gap: '1rem', alignItems: 'center', padding: '0.85rem 1rem', cursor: 'pointer' }}
      >
        {/* Thumbnail */}
        <div style={{
          width: 54, height: 96, flexShrink: 0,
          background: 'rgba(139,92,246,0.12)', border: '1px solid rgba(139,92,246,0.2)',
          borderRadius: 8, overflow: 'hidden',
          display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative',
        }}>
          <img
            src={`/api/videos/${video.id}/thumbnail`}
            alt=""
            onError={e => { (e.currentTarget as HTMLImageElement).style.display = 'none' }}
            style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', borderRadius: 8 }}
          />
          <div style={{
            position: 'relative', width: 0, height: 0,
            borderLeft: '14px solid white', borderTop: '8px solid transparent', borderBottom: '8px solid transparent',
            marginLeft: 3, opacity: 0.85, filter: 'drop-shadow(0 1px 3px rgba(0,0,0,0.6))',
          }} />
        </div>

        {/* Title + meta */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: '0.82rem', fontWeight: 500, color: 'var(--text)', marginBottom: '0.35rem', lineHeight: 1.45 }}>
            {video.youtube_title}
          </div>
          <div style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.62rem', color: 'var(--text-muted)',
            display: 'flex', gap: '0.75rem', flexWrap: 'wrap',
          }}>
            <span>r/{video.subreddit}</span>
            <span>·</span>
            <span>{video.upvotes.toLocaleString()} upvotes</span>
            <span>·</span>
            <span>{Math.round(video.duration_secs)}s</span>
            <span>·</span>
            <span>{age()}</span>
          </div>
        </div>

        {/* Chevron */}
        <span style={{
          fontSize: '0.7rem', color: 'var(--text-muted)', flexShrink: 0, opacity: 0.6,
          transform: expanded ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s',
        }}>▾</span>
      </div>

      {/* Expanded area — buttons and optional preview */}
      {expanded && (
        <div style={{ padding: '0 1rem 0.85rem' }}>
          {previewing && (
            <video
              src={`/api/videos/${video.id}/stream`}
              controls autoPlay
              style={{ width: '100%', height: 230, objectFit: 'contain', borderRadius: 8, marginBottom: '0.65rem', background: '#000' }}
            />
          )}
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {([
              { label: 'Approve', status: 'approved' as const, bg: 'rgba(110,231,183,0.08)', color: 'var(--emerald)', border: 'rgba(110,231,183,0.25)' },
              { label: 'Reject',  status: 'rejected' as const, bg: 'rgba(252,165,165,0.08)', color: 'var(--rose)',    border: 'rgba(252,165,165,0.25)' },
            ]).map(({ label, status, bg, color, border }) => (
              <button
                key={label}
                onClick={e => { e.stopPropagation(); onAction(video.id, status) }}
                style={{
                  fontFamily: 'var(--font-mono)', fontSize: '0.68rem', fontWeight: 500,
                  letterSpacing: '0.04em', padding: '0.3rem 0.85rem', borderRadius: 6,
                  border: `1px solid ${border}`, background: bg, color,
                  cursor: 'pointer', textTransform: 'uppercase',
                  backdropFilter: 'blur(8px)', transition: 'opacity 0.15s',
                }}
              >{label}</button>
            ))}
            <button
              onClick={e => { e.stopPropagation(); setPreviewing(v => !v) }}
              style={{
                fontFamily: 'var(--font-mono)', fontSize: '0.68rem', fontWeight: 500,
                letterSpacing: '0.04em', padding: '0.3rem 0.85rem', borderRadius: 6,
                border: previewing ? '1px solid rgba(139,92,246,0.3)' : '1px solid rgba(255,255,255,0.10)',
                background: previewing ? 'rgba(139,92,246,0.1)' : 'rgba(255,255,255,0.04)',
                color: previewing ? 'var(--violet-light)' : 'var(--text-muted)',
                cursor: 'pointer', textTransform: 'uppercase',
              }}
            >{previewing ? 'Hide' : 'Preview'}</button>
          </div>
        </div>
      )}
    </div>
  )
}
