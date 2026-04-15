// dashboard/src/api/client.ts
const BASE = '/api'

export interface Video {
  id: number
  content_id: number
  bot_id: number
  video_path: string
  duration_secs: number
  status: string
  created_at: string
  cleaned_script: string
  subreddit: string
  upvotes: number
}

export interface SystemStatus {
  redis: boolean
  queues: { tts: number; render: number; upload: number }
  counts: { pending_review: number; published_today: number }
}

export async function fetchVideos(status: string): Promise<Video[]> {
  const res = await fetch(`${BASE}/videos?status=${status}`)
  if (!res.ok) throw new Error('Failed to fetch videos')
  return res.json()
}

export async function updateVideoStatus(id: number, status: string): Promise<void> {
  await fetch(`${BASE}/videos/${id}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ status }),
  })
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const res = await fetch(`${BASE}/system/status`)
  return res.json()
}

export function useWebSocket(onMessage: (data: unknown) => void): WebSocket {
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
  const ws = new WebSocket(`${protocol}://${location.host}/ws`)
  ws.onmessage = (e) => onMessage(JSON.parse(e.data))
  return ws
}
