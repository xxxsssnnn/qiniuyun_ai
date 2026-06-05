import { useEffect, useMemo, useState } from 'react'

import { StatusCard } from '../components/StatusCard'
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
  const [messages, setMessages] = useState<RealtimeMessage[]>([])
  const [subtitles, setSubtitles] = useState<SubtitleItem[]>([])

  useEffect(() => {
    setConnectionStatus('connecting')
    const socket = createRealtimeSocket(sessionId)

    socket.onopen = () => setConnectionStatus('connected')
    socket.onclose = () => setConnectionStatus('disconnected')
    socket.onerror = () => setConnectionStatus('disconnected')
    socket.onmessage = (event) => {
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

    return () => socket.close()
  }, [sessionId])

  return (
    <main className="app-shell">
      <section className="hero">
        <span className="badge">AI 同声传译助手</span>
        <h1>实时字幕翻译与修正控制台</h1>
        <p>
          当前是前端实时接入骨架，后续可以直接对接音频流、识别结果、翻译结果和修正事件。
        </p>
      </section>

      <section className="panel-grid">
        <StatusCard title="连接状态" description={`WebSocket 会话：${sessionId} · 当前状态：${connectionStatus}`} />
        <StatusCard title="消息流" description={`最近接收 ${messages.length} 条实时消息。`} />
        <StatusCard title="字幕缓冲" description={`当前保留 ${subtitles.length} 条字幕片段。`} />
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
