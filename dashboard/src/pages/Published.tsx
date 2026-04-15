import { useEffect, useState } from 'react'
import { fetchVideos } from '../api/client'
import type { Video } from '../api/client'
import { VideoCard } from '../components/VideoCard'

export function Published() {
  const [videos, setVideos] = useState<Video[]>([])
  useEffect(() => { fetchVideos('uploaded').then(setVideos).catch(() => {}) }, [])
  return (
    <main style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', background: 'var(--bg)' }}>
      <div style={{ fontFamily: 'var(--font-disp)', fontSize: '1rem', fontWeight: 700, marginBottom: '1.25rem' }}>Published</div>
      {videos.length === 0 && <p style={{ color: 'var(--muted)', fontSize: '0.85rem' }}>No published videos yet.</p>}
      {videos.map(v => <VideoCard key={v.id} video={v} onAction={() => {}} />)}
    </main>
  )
}
