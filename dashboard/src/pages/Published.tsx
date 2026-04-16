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
      </div>
      {videos.length === 0 && (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>No published videos yet.</p>
      )}
      {videos.map(v => <VideoCard key={v.id} video={v} onAction={() => {}} />)}
    </main>
  )
}
