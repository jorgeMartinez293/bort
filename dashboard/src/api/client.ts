// dashboard/src/api/client.ts
const BASE = '/api'

export interface Bot {
  id: number
  name: string
  niche: string
  subreddits: string   // JSON string
  platforms: string    // JSON string
  schedule_cron: string
  background_mode: string
  active: number
  created_at: string
  yt_description: string
  yt_tags: string      // JSON string e.g. '["tag1","tag2"]'
  yt_privacy: string   // 'private' | 'public'
  upload_schedule: 'manual' | 'hourly' | 'every_6h' | 'daily'
}

export interface QueuedVideo extends Video {
  bot_name: string
  queue_position: number
}

export interface Video {
  id: number
  content_id: number
  bot_id: number
  video_path: string
  duration_secs: number
  status: string
  created_at: string
  raw_title: string
  youtube_title: string
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

export async function fetchBots(): Promise<Bot[]> {
  const res = await fetch(`${BASE}/bots`)
  if (!res.ok) throw new Error('Failed to fetch bots')
  return res.json()
}

export async function updateBotYouTube(
  id: number,
  config: { yt_description?: string; yt_tags?: string[]; yt_privacy?: string; upload_schedule?: string }
): Promise<void> {
  const res = await fetch(`${BASE}/bots/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  })
  if (!res.ok) throw new Error('Failed to update bot')
}

export async function fetchQueue(): Promise<QueuedVideo[]> {
  const res = await fetch(`${BASE}/queue`)
  if (!res.ok) throw new Error('Failed to fetch queue')
  return res.json()
}

export async function triggerUpload(videoId: number): Promise<void> {
  const res = await fetch(`${BASE}/queue/${videoId}/trigger`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to trigger upload')
}

export async function dequeueVideo(videoId: number): Promise<void> {
  const res = await fetch(`${BASE}/queue/${videoId}/dequeue`, { method: 'POST' })
  if (!res.ok) throw new Error('Failed to dequeue video')
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
