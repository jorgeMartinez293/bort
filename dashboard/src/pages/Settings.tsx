// dashboard/src/pages/Settings.tsx
import { useEffect, useState } from 'react'
import type { Bot } from '../api/client'
import { fetchBots, updateBotYouTube } from '../api/client'

interface BotDraft {
  description: string
  tagsRaw: string
  privacy: 'private' | 'public'
}

interface SaveState {
  saving: boolean
  saved: boolean
  error: string | null
}

function parseTags(yt_tags: string): string {
  try {
    const arr: string[] = JSON.parse(yt_tags || '[]')
    return arr.join('\n')
  } catch {
    return ''
  }
}

function GlassTextarea({
  rows,
  placeholder,
  value,
  onChange,
}: {
  rows: number
  placeholder: string
  value: string
  onChange: (v: string) => void
}) {
  const [focused, setFocused] = useState(false)
  return (
    <textarea
      rows={rows}
      placeholder={placeholder}
      value={value}
      onChange={e => onChange(e.target.value)}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
      style={{
        width: '100%',
        background: 'rgba(255,255,255,0.04)',
        border: `1px solid ${focused ? 'rgba(139,92,246,0.5)' : 'rgba(255,255,255,0.10)'}`,
        borderRadius: 8,
        color: 'var(--text)',
        fontFamily: 'var(--font-body)',
        fontSize: '0.82rem',
        padding: '0.6rem 0.75rem',
        resize: 'vertical',
        outline: 'none',
        lineHeight: 1.5,
        transition: 'border-color 0.18s',
      }}
    />
  )
}

export function Settings() {
  const [bots, setBots] = useState<Bot[]>([])
  const [drafts, setDrafts] = useState<Record<number, BotDraft>>({})
  const [saveState, setSaveState] = useState<Record<number, SaveState>>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchBots().then(data => {
      setBots(data)
      const initial: Record<number, BotDraft> = {}
      data.forEach(b => {
        initial[b.id] = {
          description: b.yt_description || '',
          tagsRaw: parseTags(b.yt_tags),
          privacy: (b.yt_privacy as 'private' | 'public') || 'private',
        }
      })
      setDrafts(initial)
      setLoading(false)
    })
  }, [])

  function updateDraft(botId: number, patch: Partial<BotDraft>) {
    setDrafts(prev => ({ ...prev, [botId]: { ...prev[botId], ...patch } }))
  }

  async function save(bot: Bot) {
    const draft = drafts[bot.id]
    if (!draft) return
    setSaveState(prev => ({ ...prev, [bot.id]: { saving: true, saved: false, error: null } }))
    try {
      const tags = draft.tagsRaw.split('\n').map(t => t.trim()).filter(Boolean)
      await updateBotYouTube(bot.id, {
        yt_description: draft.description,
        yt_tags: tags,
        yt_privacy: draft.privacy,
      })
      setSaveState(prev => ({ ...prev, [bot.id]: { saving: false, saved: true, error: null } }))
      setTimeout(() => {
        setSaveState(prev => ({ ...prev, [bot.id]: { ...prev[bot.id], saved: false } }))
      }, 2000)
    } catch (e) {
      setSaveState(prev => ({ ...prev, [bot.id]: { saving: false, saved: false, error: String(e) } }))
    }
  }

  const labelStyle: React.CSSProperties = {
    fontFamily: 'var(--font-mono)',
    fontSize: '0.65rem',
    color: 'var(--text-muted)',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
    marginBottom: '0.4rem',
    display: 'block',
  }

  return (
    <main style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', background: 'transparent' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
        <span style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text)' }}>Settings</span>
      </div>

      {loading && (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>Loading bots…</p>
      )}
      {!loading && bots.length === 0 && (
        <p style={{ color: 'var(--text-muted)', fontSize: '0.82rem' }}>No bots found.</p>
      )}

      {bots.map(bot => {
        const draft = drafts[bot.id]
        const ss = saveState[bot.id] || { saving: false, saved: false, error: null }
        if (!draft) return null

        return (
          <div
            key={bot.id}
            style={{
              background: 'var(--glass-bg)',
              backdropFilter: 'blur(var(--glass-blur))',
              WebkitBackdropFilter: 'blur(var(--glass-blur))',
              border: '1px solid var(--glass-border)',
              borderRadius: 12,
              overflow: 'hidden',
              marginBottom: '1rem',
            }}
          >
            {/* Shimmer line */}
            <div style={{
              height: 1,
              background: 'linear-gradient(90deg, transparent, var(--violet-glow), transparent)',
            }} />

            <div style={{ padding: '1.25rem' }}>
              {/* Bot header */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem' }}>
                <span style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--text)' }}>
                  {bot.name}
                </span>
                <span style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.62rem',
                  letterSpacing: '0.05em',
                  background: 'rgba(139,92,246,0.12)',
                  color: 'var(--violet-light)',
                  border: '1px solid rgba(139,92,246,0.25)',
                  borderRadius: 4,
                  padding: '0.15rem 0.5rem',
                  textTransform: 'uppercase',
                }}>
                  {bot.niche}
                </span>
                <span style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: '0.62rem',
                  marginLeft: 'auto',
                  color: bot.active === 1 ? 'var(--emerald)' : 'var(--text-muted)',
                }}>
                  {bot.active === 1 ? '● active' : '○ inactive'}
                </span>
              </div>

              {/* Section label */}
              <div style={{
                fontFamily: 'var(--font-mono)',
                fontSize: '0.6rem',
                letterSpacing: '0.08em',
                color: 'var(--text-muted)',
                textTransform: 'uppercase',
                marginBottom: '1rem',
                borderBottom: '1px solid rgba(255,255,255,0.06)',
                paddingBottom: '0.4rem',
              }}>
                YouTube
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {/* Description */}
                <div>
                  <label style={labelStyle}>Description</label>
                  <GlassTextarea
                    rows={4}
                    placeholder="Leave empty for no description…"
                    value={draft.description}
                    onChange={v => updateDraft(bot.id, { description: v })}
                  />
                </div>

                {/* Tags */}
                <div>
                  <label style={labelStyle}>Tags — one per line</label>
                  <GlassTextarea
                    rows={4}
                    placeholder={'funny\nreddit\nshorts'}
                    value={draft.tagsRaw}
                    onChange={v => updateDraft(bot.id, { tagsRaw: v })}
                  />
                </div>

                {/* Privacy */}
                <div>
                  <label style={labelStyle}>Privacy</label>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    {(['private', 'public'] as const).map(option => (
                      <button
                        key={option}
                        onClick={() => updateDraft(bot.id, { privacy: option })}
                        style={{
                          fontFamily: 'var(--font-mono)',
                          fontSize: '0.7rem',
                          fontWeight: 500,
                          letterSpacing: '0.04em',
                          padding: '0.35rem 1rem',
                          borderRadius: 6,
                          textTransform: 'uppercase',
                          cursor: 'pointer',
                          border: draft.privacy === option
                            ? '1px solid var(--glass-border-active)'
                            : '1px solid rgba(255,255,255,0.10)',
                          background: draft.privacy === option
                            ? 'var(--glass-bg-active)'
                            : 'rgba(255,255,255,0.04)',
                          color: draft.privacy === option ? '#c4b5fd' : 'var(--text-muted)',
                          transition: 'all 0.18s',
                        }}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Save */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <button
                    onClick={() => save(bot)}
                    disabled={ss.saving}
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: '0.7rem',
                      fontWeight: 500,
                      letterSpacing: '0.04em',
                      padding: '0.4rem 1.25rem',
                      borderRadius: 6,
                      textTransform: 'uppercase',
                      cursor: ss.saving ? 'default' : 'pointer',
                      border: '1px solid rgba(139,92,246,0.35)',
                      background: 'rgba(139,92,246,0.15)',
                      color: 'var(--violet-light)',
                      opacity: ss.saving ? 0.6 : 1,
                      transition: 'opacity 0.15s',
                    }}
                  >
                    {ss.saving ? 'Saving…' : 'Save'}
                  </button>
                  {ss.saved && (
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.68rem', color: 'var(--emerald)' }}>
                      ✓ Saved
                    </span>
                  )}
                  {ss.error && (
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.68rem', color: 'var(--rose)' }}>
                      Error: {ss.error}
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )
      })}
    </main>
  )
}
