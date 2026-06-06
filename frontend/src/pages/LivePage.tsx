import { useEffect, useMemo, useState } from 'react'

import { StatusCard } from '../components/StatusCard'
import { addGlossaryEntry, deleteGlossaryEntry, fetchGlossary, updateGlossaryEntry, type GlossaryEntry, fetchLatestChunk } from '../services/api'
import { startAudioCapture, type AudioCaptureState } from '../services/audio'
import { closeRealtimeSocket, createRealtimeSocket, type RealtimeMessage } from '../services/ws'

type SubtitleItem = {
  id: string
  sourceText: string
  translatedText: string
  isFinal: boolean
  revision: number
}

const statusLabels = {
  idle: '空闲',
  starting: '启动中',
  recording: '采集中',
  stopped: '已停止',
  error: '异常',
} as const

export function LivePage() {
  const sessionId = useMemo(() => 'demo-session', [])
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'connecting' | 'connected' | 'disconnected'>('idle')
  const [audioState, setAudioState] = useState<AudioCaptureState>('idle')
  const [messages, setMessages] = useState<RealtimeMessage[]>([])
  const [subtitles, setSubtitles] = useState<SubtitleItem[]>([])
  const [socket, setSocket] = useState<WebSocket | null>(null)
  const [audioSession, setAudioSession] = useState<{ stop: () => void } | null>(null)
  const [glossary, setGlossary] = useState<GlossaryEntry[]>([])

  useEffect(() => {
    setConnectionStatus('connecting')
    const realtimeSocket = createRealtimeSocket(sessionId)
    setSocket(realtimeSocket)

    realtimeSocket.onopen = () => setConnectionStatus('connected')
    realtimeSocket.onclose = () => setConnectionStatus('disconnected')
    realtimeSocket.onerror = () => setConnectionStatus('disconnected')
    realtimeSocket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data as string) as RealtimeMessage & { payload?: any }
        setMessages((prev) => [...prev.slice(-29), message])

        if (message.type === 'chunk' || message.type === 'translated' || message.type === 'revision' || message.type === 'correction') {
          const payload = message.payload as Partial<SubtitleItem> & { chunk_id?: string }
          if (payload?.chunk_id) {
            setSubtitles((prev) => {
              const next = prev.filter((item) => item.id !== payload.chunk_id)
              next.unshift({
                id: payload.chunk_id!,
                sourceText: payload.sourceText ?? '',
                translatedText: payload.translatedText ?? '',
                isFinal: payload.isFinal ?? false,
                revision: payload.revision ?? 0,
              })
              return next.slice(0, 10)
            })
          }
        }
      } catch {
        // ignore malformed payloads in the scaffold stage
      }
    }

    void fetchLatestChunk().then((chunk) => {
      if (!chunk) return
      setSubtitles([
        {
          id: chunk.chunk_id,
          sourceText: chunk.source_text,
          translatedText: chunk.translated_text,
          isFinal: chunk.is_final,
          revision: chunk.revision,
        },
      ])
    })

    return () => closeRealtimeSocket(realtimeSocket)
  }, [sessionId])

  useEffect(() => {
    void fetchGlossary().then(setGlossary).catch(() => setGlossary([]))
  }, [])

  const refreshGlossary = async () => {
    const items = await fetchGlossary()
    setGlossary(items)
  }

  const handleStartDemo = () => {
    if (!socket || socket.readyState !== WebSocket.OPEN) return
    socket.send(JSON.stringify({ type: 'start_demo' }))
    setMessages((prev) => [...prev.slice(-29), { type: 'status', session_id: sessionId, payload: { message: 'demo requested' } }])
  }

  const handleStartAudio = async () => {
    if (!socket || socket.readyState !== WebSocket.OPEN || audioState === 'recording' || audioState === 'starting') return
    try {
      setAudioState('starting')
      socket.send(JSON.stringify({ type: 'start_audio', session_id: sessionId }))
      const session = await startAudioCapture((chunk) => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(chunk)
        }
      })
      setAudioSession(session)
      setAudioState('recording')
      setMessages((prev) => [...prev.slice(-29), { type: 'audio', session_id: sessionId, payload: { message: 'microphone recording started' } }])
    } catch {
      setAudioState('error')
      setMessages((prev) => [...prev.slice(-29), { type: 'error', session_id: sessionId, payload: { message: 'failed to start microphone' } }])
    }
  }

  const handleStopAudio = () => {
    audioSession?.stop()
    setAudioSession(null)
    setAudioState('stopped')
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: 'stop_audio', session_id: sessionId }))
    }
    setMessages((prev) => [...prev.slice(-29), { type: 'audio', session_id: sessionId, payload: { message: 'microphone recording stopped' } }])
  }

  return (
    <main className="page-shell">
      <section className="page-hero hero-grid">
        <div className="hero-copy">
          <span className="badge">Live</span>
          <h2>实时传译工作台</h2>
          <p>这里用于处理麦克风采集、演示字幕、实时字幕流和手动回滚，是系统的核心作业区。</p>
          <div className="hero-actions">
            <button className="primary-button" onClick={handleStartDemo} disabled={connectionStatus !== 'connected'}>开始演示字幕</button>
            <button className="secondary-button" onClick={handleStartAudio} disabled={connectionStatus !== 'connected' || audioState === 'recording' || audioState === 'starting'}>开始采集麦克风</button>
            <button className="secondary-button" onClick={handleStopAudio} disabled={audioState !== 'recording'}>停止采集</button>
          </div>
        </div>
        <div className="hero-side panel">
          <div className="live-stat"><span>连接</span><strong>{connectionStatus}</strong></div>
          <div className="live-stat"><span>音频</span><strong>{statusLabels[audioState]}</strong></div>
          <div className="live-stat"><span>字幕</span><strong>{subtitles.length}</strong></div>
          <div className="live-stat"><span>术语</span><strong>{glossary.length}</strong></div>
        </div>
      </section>

      <section className="panel-grid stats-grid">
        <StatusCard title="WebSocket" description={`会话：${sessionId} · 当前状态：${connectionStatus}`} />
        <StatusCard title="音频采集" description={`当前状态：${statusLabels[audioState]}`} />
        <StatusCard title="实时消息" description={`最近接收 ${messages.length} 条消息。`} />
      </section>

      <section className="content-grid">
        <article className="panel subtitle-panel">
          <div className="panel-header"><div><h2>实时字幕</h2><p>显示原文、译文和修订状态。</p></div><span className="panel-badge">Live</span></div>
          <div className="subtitle-list">
            {subtitles.length === 0 ? <div className="empty-state"><p>等待字幕流…</p></div> : subtitles.map((item) => (
              <div key={item.id} className={`subtitle-item ${item.isFinal ? 'final' : 'draft'}`}>
                <div className="subtitle-topline"><span>{item.isFinal ? 'FINAL' : 'DRAFT'}</span><small>revision {item.revision}</small></div>
                <p className="source">{item.sourceText}</p>
                <p className="translation">{item.translatedText}</p>
              </div>
            ))}
          </div>
        </article>

        <article className="panel glossary-panel">
          <div className="panel-header"><div><h2>术语快览</h2><p>这里展示当前术语库的简略列表。</p></div><span className="panel-badge">Glossary</span></div>
          <div className="glossary-list">
            {glossary.length === 0 ? <div className="empty-state compact"><p>暂无术语。</p></div> : glossary.slice(0, 5).map((item) => (
              <div className="glossary-item" key={item.source}>
                <div className="glossary-text"><strong>{item.source}</strong><span>→ {item.target}</span></div>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="panel-grid single-grid">
        <article className="panel message-panel">
          <div className="panel-header"><div><h2>最近消息</h2><p>查看 WebSocket 事件的实时流转。</p></div><span className="panel-badge">Stream</span></div>
          <div className="message-list">
            {messages.length === 0 ? <div className="empty-state compact"><p>等待 WebSocket 消息…</p></div> : messages.slice().reverse().map((message, index) => <pre key={`${message.type}-${index}`} className="message-item">{JSON.stringify(message, null, 2)}</pre>)}
          </div>
        </article>
      </section>
    </main>
  )
}
