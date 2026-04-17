// dashboard/src/pages/Pending.tsx
import { useEffect, useState } from 'react'
import { fetchVideos, updateVideoStatus, fetchSystemStatus, fetchGeminiStatus, useWebSocket } from '../api/client'
import type { Video, SystemStatus, GeminiStatus } from '../api/client'
import { VideoCard } from '../components/VideoCard'

function StatPill({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      background: 'rgba(255,255,255,0.05)',
      border: '1px solid rgba(255,255,255,0.08)',
      borderRadius: 999,
      padding: '0.2rem 0.75rem',
    }}>
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '0.55rem',
        color: 'var(--text-muted)',
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
      }}>
        {label}
      </span>
      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '0.85rem',
        fontWeight: 500,
        color,
      }}>
        {value}
      </span>
    </div>
  )
}

export function Pending() {
  const [videos, setVideos] = useState<Video[]>([])
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [gemini, setGemini] = useState<GeminiStatus>({ key_missing: false, expand_pending_count: 0 })

  useEffect(() => {
    fetchVideos('pending_review').then(setVideos).catch(() => {})
    fetchSystemStatus().then(setStatus).catch(() => {})
    fetchGeminiStatus().then(setGemini).catch(() => {})
    const geminiId = setInterval(() => fetchGeminiStatus().then(setGemini).catch(() => {}), 30_000)
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
    return () => { ws.close(); clearInterval(geminiId) }
  }, [])

  const handleAction = async (id: number, newStatus: 'approved' | 'rejected') => {
    await updateVideoStatus(id, newStatus)
    setVideos(vs => vs.filter(v => v.id !== id))
  }

  const queueTotal = status?.queues.upload ?? 0

  return (
    <main style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', background: 'transparent' }}>
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
        marginBottom: '1.25rem',
        flexWrap: 'wrap',
      }}>
        <span style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text)' }}>
          Pending Review
        </span>
        <span style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '0.68rem',
          color: 'var(--violet-light)',
          background: 'rgba(139,92,246,0.15)',
          border: '1px solid rgba(139,92,246,0.3)',
          padding: '0.15rem 0.6rem',
          borderRadius: 999,
        }}>
          {videos.length} videos
        </span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: '0.5rem' }}>
          <StatPill label="Queue"   value={queueTotal}                          color="var(--text)" />
          <StatPill label="Review"  value={status?.counts.pending_review ?? 0}  color="var(--amber)" />
          <StatPill label="Today"   value={status?.counts.published_today ?? 0} color="var(--emerald)" />
          {gemini.expand_pending_count > 0 && (
            <StatPill label="Waiting" value={gemini.expand_pending_count} color="#fbbf24" />
          )}
        </div>
      </div>
      {videos.length === 0 && (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No videos pending review.</p>
      )}
      {videos.map(v => <VideoCard key={v.id} video={v} onAction={handleAction} />)}
    </main>
  )
}
