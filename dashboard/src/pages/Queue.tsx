// dashboard/src/pages/Queue.tsx
import { useEffect, useState, useCallback, useRef } from 'react'
import type { QueuedVideo, NextUploadInfo } from '../api/client'
import { fetchQueue, triggerUpload, dequeueVideo, fetchNextUpload } from '../api/client'

function fmt(secs: number): string {
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  return [h, m, s].map(n => String(n).padStart(2, '0')).join(':')
}

function UploadCountdown({ info }: { info: NextUploadInfo }) {
  const [remaining, setRemaining] = useState(info.seconds_until)
  const ref = useRef(info.seconds_until)

  useEffect(() => {
    ref.current = info.seconds_until
    setRemaining(info.seconds_until)
  }, [info.seconds_until])

  useEffect(() => {
    if (info.uploading || ref.current === 0) return
    const id = setInterval(() => {
      ref.current = Math.max(0, ref.current - 1)
      setRemaining(ref.current)
    }, 1000)
    return () => clearInterval(id)
  }, [info.uploading])

  const SCHEDULE_LABEL: Record<string, string> = {
    hourly: '1h', every_6h: '6h', daily: '24h',
  }

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '0.6rem',
      padding: '0.45rem 0.75rem',
      borderRadius: 8,
      background: 'rgba(255,255,255,0.04)',
      border: '1px solid rgba(255,255,255,0.08)',
    }}>
      <span style={{
        width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
        background: info.uploading ? 'var(--emerald)' : remaining === 0 ? '#fbbf24' : 'var(--violet)',
        animation: info.uploading ? 'pulse 2s ease-in-out infinite' : 'none',
      }} />
      <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontWeight: 500 }}>
        {info.bot_name}
      </span>
      <span style={{
        fontSize: '0.62rem',
        color: 'var(--text-muted)',
        background: 'rgba(255,255,255,0.06)',
        border: '1px solid rgba(255,255,255,0.08)',
        borderRadius: 4,
        padding: '0.05rem 0.35rem',
      }}>
        {SCHEDULE_LABEL[info.schedule] ?? info.schedule}
      </span>
      <span style={{
        marginLeft: 'auto',
        fontFamily: 'var(--font-mono)',
        fontSize: '0.82rem',
        fontWeight: 600,
        color: info.uploading ? 'var(--emerald)' : remaining === 0 ? '#fbbf24' : 'var(--text)',
        letterSpacing: '0.04em',
      }}>
        {info.uploading ? 'Subiendo…' : remaining === 0 ? 'Listo' : fmt(remaining)}
      </span>
    </div>
  )
}

function QueueCard({
  video,
  onUpload,
}: {
  video: QueuedVideo
  onUpload: (id: number) => void
}) {
  const [previewing, setPreviewing] = useState(false)
  const [hovered, setHovered] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [dequeuing, setDequeuing] = useState(false)
  const [expanded, setExpanded] = useState(false)

  const age = () => {
    const diff = Date.now() - new Date(video.created_at).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 60) return `${mins}m ago`
    return `${Math.floor(mins / 60)}h ago`
  }

  async function handleUpload() {
    setUploading(true)
    try {
      await triggerUpload(video.id)
      onUpload(video.id)
    } catch {
      setUploading(false)
    }
  }

  async function handleDequeue() {
    setDequeuing(true)
    try {
      await dequeueVideo(video.id)
      onUpload(video.id)
    } catch {
      setDequeuing(false)
    }
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
      <div style={{ height: 1, background: 'linear-gradient(90deg, transparent, var(--violet-glow), transparent)' }} />

      {/* Header row — tap to expand */}
      <div
        onClick={handleToggle}
        style={{ display: 'flex', gap: '1rem', alignItems: 'center', padding: '0.85rem 1rem', cursor: 'pointer' }}
      >
        {/* Position badge + thumb */}
        <div style={{ width: 54, height: 96, flexShrink: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
          <div style={{
            width: 40, height: 40,
            background: 'rgba(139,92,246,0.12)', border: '1px solid rgba(139,92,246,0.2)',
            borderRadius: 8, overflow: 'hidden',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            position: 'relative', flexShrink: 0,
          }}>
            <img
              src={`/api/videos/${video.id}/thumbnail`}
              alt=""
              onError={e => { (e.currentTarget as HTMLImageElement).style.display = 'none' }}
              style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', borderRadius: 8 }}
            />
            <div style={{
              position: 'relative', width: 0, height: 0,
              borderLeft: '10px solid white', borderTop: '6px solid transparent', borderBottom: '6px solid transparent',
              marginLeft: 2, opacity: 0.85, filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.6))',
            }} />
          </div>
          <span style={{
            fontFamily: 'var(--font-mono)', fontSize: '0.7rem', fontWeight: 600,
            color: 'var(--violet-light)', background: 'rgba(139,92,246,0.15)',
            border: '1px solid rgba(139,92,246,0.3)', borderRadius: 999,
            padding: '0.1rem 0.5rem', lineHeight: 1.6,
          }}>#{video.queue_position}</span>
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
            <span style={{ color: 'var(--violet-light)' }}>{video.bot_name}</span>
            <span>·</span>
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

      {/* Expanded area */}
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
            <button
              onClick={e => { e.stopPropagation(); handleUpload() }}
              disabled={uploading}
              style={{
                fontFamily: 'var(--font-mono)', fontSize: '0.68rem', fontWeight: 500,
                letterSpacing: '0.04em', padding: '0.3rem 0.85rem', borderRadius: 6,
                border: '1px solid rgba(110,231,183,0.25)', background: 'rgba(110,231,183,0.08)',
                color: 'var(--emerald)', cursor: uploading ? 'default' : 'pointer',
                textTransform: 'uppercase', opacity: uploading ? 0.5 : 1, transition: 'opacity 0.15s',
              }}
            >{uploading ? 'Starting…' : 'Upload Now'}</button>
            <button
              onClick={e => { e.stopPropagation(); handleDequeue() }}
              disabled={dequeuing}
              style={{
                fontFamily: 'var(--font-mono)', fontSize: '0.68rem', fontWeight: 500,
                letterSpacing: '0.04em', padding: '0.3rem 0.85rem', borderRadius: 6,
                border: '1px solid rgba(252,165,165,0.25)', background: 'rgba(252,165,165,0.08)',
                color: 'var(--rose)', cursor: dequeuing ? 'default' : 'pointer',
                textTransform: 'uppercase', opacity: dequeuing ? 0.5 : 1, transition: 'opacity 0.15s',
              }}
            >{dequeuing ? '…' : 'Back to Review'}</button>
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

export function Queue() {
  const [videos, setVideos] = useState<QueuedVideo[]>([])
  const [loading, setLoading] = useState(true)
  const [nextUploads, setNextUploads] = useState<NextUploadInfo[]>([])

  const load = useCallback(() => {
    fetchQueue()
      .then(setVideos)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
    const id = setInterval(load, 10_000)
    return () => clearInterval(id)
  }, [load])

  useEffect(() => {
    fetchNextUpload().then(setNextUploads).catch(() => {})
    const id = setInterval(() => fetchNextUpload().then(setNextUploads).catch(() => {}), 60_000)
    return () => clearInterval(id)
  }, [])

  function removeVideo(id: number) {
    setVideos(prev =>
      prev
        .filter(v => v.id !== id)
        .map((v, i) => ({ ...v, queue_position: i + 1 }))
    )
  }

  return (
    <main style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', background: 'transparent' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
        <span style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text)' }}>Upload Queue</span>
        {videos.length > 0 && (
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '0.68rem',
            color: 'var(--violet-light)',
            background: 'rgba(139,92,246,0.15)',
            border: '1px solid rgba(139,92,246,0.3)',
            padding: '0.15rem 0.6rem',
            borderRadius: 999,
          }}>
            {videos.length} waiting
          </span>
        )}
      </div>

      {nextUploads.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginBottom: '1.25rem' }}>
          {nextUploads.map(info => <UploadCountdown key={info.bot_id} info={info} />)}
        </div>
      )}

      {loading && (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Loading…</p>
      )}
      {!loading && videos.length === 0 && (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>Queue is empty.</p>
      )}

      {videos.map(v => (
        <QueueCard key={v.id} video={v} onUpload={removeVideo} />
      ))}
    </main>
  )
}
