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
            width: 54,
            height: 96,
            flexShrink: 0,
            background: 'rgba(139,92,246,0.12)',
            border: '1px solid rgba(139,92,246,0.2)',
            borderRadius: 8,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
          }}
        >
          <div style={{
            width: 0,
            height: 0,
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
            fontSize: '0.82rem',
            fontWeight: 500,
            color: 'var(--text)',
            marginBottom: '0.35rem',
            lineHeight: 1.45,
          }}>
            {video.youtube_title}
          </div>
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '0.62rem',
            color: 'var(--text-muted)',
            display: 'flex',
            gap: '0.75rem',
            flexWrap: 'wrap',
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
              controls
              autoPlay
              style={{ width: '100%', maxWidth: 300, borderRadius: 6, marginBottom: '0.65rem' }}
            />
          )}

          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {([
              {
                label: 'Approve',
                status: 'approved' as const,
                bg: 'rgba(110,231,183,0.08)',
                color: 'var(--emerald)',
                border: 'rgba(110,231,183,0.25)',
              },
              {
                label: 'Reject',
                status: 'rejected' as const,
                bg: 'rgba(252,165,165,0.08)',
                color: 'var(--rose)',
                border: 'rgba(252,165,165,0.25)',
              },
            ]).map(({ label, status, bg, color, border }) => (
              <button
                key={label}
                onClick={() => onAction(video.id, status)}
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.68rem',
                  fontWeight: 500,
                  letterSpacing: '0.04em',
                  padding: '0.3rem 0.85rem',
                  borderRadius: 6,
                  border: `1px solid ${border}`,
                  background: bg,
                  color,
                  cursor: 'pointer',
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
                fontFamily: 'var(--font-mono)',
                fontSize: '0.68rem',
                fontWeight: 500,
                letterSpacing: '0.04em',
                padding: '0.3rem 0.85rem',
                borderRadius: 6,
                border: '1px solid rgba(255,255,255,0.10)',
                background: 'rgba(255,255,255,0.04)',
                color: 'var(--text-muted)',
                cursor: 'pointer',
                textTransform: 'uppercase',
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
