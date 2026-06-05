import { useEffect, useMemo, useState } from 'react'

import { StatusCard } from '../components/StatusCard'
import { startAudioCapture, type AudioCaptureState } from '../services/audio'
import { createRealtimeSocket, type RealtimeMessage } from '../services/ws'

type SubtitleItem = {
  id: string
  sourceText: string
  translatedText: string
  isFinal: boolean
  revision: number
}

export function HomePage() {
  const sessionId = useMemo(() => 'demo-session', [])
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'connecting' | 'connected' | 'disconnected'>('idle')
  const [audioState, setAudioState] = useState<AudioCaptureState>('idle')
  const [messages, setMessages] = useState<RealtimeMessage[]>([])
  const [subtitles, setSubtitles] = useState<SubtitleItem[]>([])
  const [socket, setSocket] = useState<WebSocket | null>(null)
  const [audioSession, setAudioSession] = useState<{ stop: () => void } | null>(null)

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
        setMessages((prev) => [...prev.slice(-19), message])

        if (message.type === 'chunk' || message.type === 'translated' || message.type === 'revision') {
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
              return next.slice(0, 6)
            })
          }
        }
      } catch {
        // ignore malformed payloads in the scaffold stage
      }
    }

    return () => realtimeSocket.close()
  }, [sessionId])

  const handleStartDemo = () => {
    if (!socket || socket.readyState !== WebSocket.OPEN) return
    socket.send(JSON.stringify({ type: 'start_demo' }))
    setMessages((prev) => [...prev.slice(-19), { type: 'status', session_id: sessionId, payload: { message: 'demo requested' } }])
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
      setMessages((prev) => [...prev.slice(-19), { type: 'audio', session_id: sessionId, payload: { message: 'microphone recording started' } }])
    } catch {
      setAudioState('error')
      setMessages((prev) => [...prev.slice(-19), { type: 'error', session_id: sessionId, payload: { message: 'failed to start microphone' } }])
    }
  }

  const handleStopAudio = () => {
    audioSession?.stop()
    setAudioSession(null)
    setAudioState('stopped')
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: 'stop_audio', session_id: sessionId }))
    }
    setMessages((prev) => [...prev.slice(-19), { type: 'audio', session_id: sessionId, payload: { message: 'microphone recording stopped' } }])
  }

  return (
    <main className="app-shell">
      <section className="hero">
        <span className="badge">AI 同声传译助手</span>
        <h1>实时字幕翻译与音频流控制台</h1>
        <p>先把核心链路做通：麦克风采集 → WebSocket 传输 → 后端处理 → 实时字幕输出。</p>
        <div className="hero-actions">
          <button className="primary-button" onClick={handleStartDemo} disabled={connectionStatus !== 'connected'}>
            开始演示字幕
          </button>
          <button className="secondary-button" onClick={handleStartAudio} disabled={connectionStatus !== 'connected' || audioState === 'recording' || audioState === 'starting'}>
            开始采集麦克风
          </button>
          <button className="secondary-button" onClick={handleStopAudio} disabled={audioState !== 'recording'}>
            停止采集
          </button>
        </div>
        <div className="hero-meta">
          <span className="hint">连接状态：{connectionStatus}</span>
          <span className="hint">音频状态：{audioState}</span>
        </div>
      </section>

      <section className="panel-grid">
        <StatusCard title="连接状态" description={`WebSocket 会话：${sessionId} · 当前状态：${connectionStatus}`} />
        <StatusCard title="音频状态" description={`当前麦克风采集状态：${audioState}`} />
        <StatusCard title="消息流" description={`最近接收 ${messages.length} 条实时消息。`} />
      </section>

      <section className="panel-grid two-cols">
        <article className="panel">
          <h2>实时字幕</h2>
          <div className="subtitle-list">
            {subtitles.length === 0 ? (
              <p className="muted">等待后端推送字幕片段…</p>
            ) : (
              subtitles.map((item) => (
                <div key={item.id} className={`subtitle-item ${item.isFinal ? 'final' : 'draft'}`}>
                  <p className="source">{item.sourceText || '暂无原文'}</p>
                  <p className="translation">{item.translatedText || '暂无译文'}</p>
                  <small>revision {item.revision}</small>
                </div>
              ))
            )}
          </div>
        </article>

        <article className="panel">
          <h2>最近消息</h2>
          <div className="message-list">
            {messages.length === 0 ? (
              <p className="muted">等待 WebSocket 消息…</p>
            ) : (
              messages
                .slice()
                .reverse()
                .map((message, index) => (
                  <pre key={`${message.type}-${index}`} className="message-item">
                    {JSON.stringify(message, null, 2)}
                  </pre>
                ))
            )}
          </div>
        </article>
      </section>
    </main>
  )
}
