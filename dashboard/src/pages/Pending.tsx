// dashboard/src/pages/Pending.tsx
import { useEffect, useState } from 'react'
import { fetchVideos, updateVideoStatus } from '../api/client'
import type { Video } from '../api/client'
import { VideoCard } from '../components/VideoCard'

export function Pending() {
  const [videos, setVideos] = useState<Video[]>([])

  useEffect(() => { fetchVideos('pending_review').then(setVideos).catch(() => {}) }, [])

  const handleAction = async (id: number, status: 'approved' | 'rejected') => {
    await updateVideoStatus(id, status)
    setVideos(vs => vs.filter(v => v.id !== id))
  }

  return (
    <main style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', background: 'var(--bg)' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.75rem', marginBottom: '1.25rem' }}>
        <span style={{ fontFamily: 'var(--font-disp)', fontSize: '1rem', fontWeight: 700 }}>Pending Review</span>
        <span style={{
          fontFamily: 'var(--font-mono)', fontSize: '0.7rem', color: 'var(--warn)',
          background: 'rgba(232,160,32,0.1)', border: '1px solid rgba(232,160,32,0.25)',
          padding: '0.15rem 0.5rem', borderRadius: 20,
        }}>
          {videos.length} videos
        </span>
      </div>
      {videos.length === 0 && (
        <p style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>No videos pending review.</p>
      )}
      {videos.map(v => <VideoCard key={v.id} video={v} onAction={handleAction} />)}
    </main>
  )
}
