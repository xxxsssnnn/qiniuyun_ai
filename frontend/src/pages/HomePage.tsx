import { useEffect, useMemo, useState } from 'react'

import { StatusCard } from '../components/StatusCard'
import { addGlossaryEntry, deleteGlossaryEntry, fetchGlossary, updateGlossaryEntry, type GlossaryEntry } from '../services/api'
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

export function HomePage() {
  const sessionId = useMemo(() => 'demo-session', [])
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'connecting' | 'connected' | 'disconnected'>('idle')
  const [audioState, setAudioState] = useState<AudioCaptureState>('idle')
  const [messages, setMessages] = useState<RealtimeMessage[]>([])
  const [subtitles, setSubtitles] = useState<SubtitleItem[]>([])
  const [socket, setSocket] = useState<WebSocket | null>(null)
  const [audioSession, setAudioSession] = useState<{ stop: () => Promise<void> } | null>(null)
  const [glossary, setGlossary] = useState<GlossaryEntry[]>([])
  const [newSource, setNewSource] = useState('')
  const [newTarget, setNewTarget] = useState('')
  const [newNote, setNewNote] = useState('')
  const [editingSource, setEditingSource] = useState('')
  const [editingTarget, setEditingTarget] = useState('')
  const [editingNote, setEditingNote] = useState('')

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
              return next.slice(0, 8)
            })
          }
        }
      } catch {
        // ignore malformed payloads in the scaffold stage
      }
    }

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

  const handleStopAudio = async () => {
    await audioSession?.stop()
    setAudioSession(null)
    setAudioState('stopped')
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: 'stop_audio', session_id: sessionId }))
    }
    setMessages((prev) => [...prev.slice(-19), { type: 'audio', session_id: sessionId, payload: { message: 'microphone recording stopped' } }])
  }

  const handleAddGlossary = async () => {
    if (!newSource.trim() || !newTarget.trim()) return
    const created = await addGlossaryEntry({ source: newSource.trim(), target: newTarget.trim(), note: newNote.trim() })
    setGlossary((prev) => [created, ...prev])
    setNewSource('')
    setNewTarget('')
    setNewNote('')
  }

  const handleEditGlossary = async () => {
    if (!editingSource.trim() || !editingTarget.trim()) return
    const updated = await updateGlossaryEntry(editingSource.trim(), {
      source: editingSource.trim(),
      target: editingTarget.trim(),
      note: editingNote.trim(),
    })
    setGlossary((prev) => prev.map((item) => (item.source === editingSource.trim() ? updated : item)))
    setEditingSource('')
    setEditingTarget('')
    setEditingNote('')
  }

  const handleDeleteGlossary = async (source: string) => {
    await deleteGlossaryEntry(source)
    await refreshGlossary()
  }

  return (
    <main className="app-shell">
      <section className="hero hero-grid">
        <div className="hero-copy">
          <span className="badge">AI 同声传译助手</span>
          <h1>实时字幕翻译与音频流控制台</h1>
          <p>面向英语技术分享、国际会议和网课，实时把外语音频流转成更易理解的中文字幕与语音。</p>

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
            <div className="meta-chip">
              <span>连接状态</span>
              <strong>{connectionStatus}</strong>
            </div>
            <div className="meta-chip">
              <span>音频状态</span>
              <strong>{statusLabels[audioState]}</strong>
            </div>
            <div className="meta-chip">
              <span>会话</span>
              <strong>{sessionId}</strong>
            </div>
          </div>
        </div>

        <div className="hero-side panel">
          <div className="live-stat">
            <span>实时字幕</span>
            <strong>{subtitles.length}</strong>
          </div>
          <div className="live-stat">
            <span>实时消息</span>
            <strong>{messages.length}</strong>
          </div>
          <div className="live-stat">
            <span>术语条目</span>
            <strong>{glossary.length}</strong>
          </div>
        </div>
      </section>

      <section className="panel-grid stats-grid">
        <StatusCard title="连接状态" description={`WebSocket 会话：${sessionId} · 当前状态：${connectionStatus}`} />
        <StatusCard title="音频状态" description={`当前麦克风采集状态：${statusLabels[audioState]}`} />
        <StatusCard title="消息流" description={`最近接收 ${messages.length} 条实时消息。`} />
      </section>

      <section className="content-grid">
        <article className="panel subtitle-panel">
          <div className="panel-header">
            <div>
              <h2>实时字幕</h2>
              <p>显示原文、译文和修订状态，支持后续纠错回滚。</p>
            </div>
            <span className="panel-badge">Live</span>
          </div>
          <div className="subtitle-list">
            {subtitles.length === 0 ? (
              <div className="empty-state">
                <p>等待后端推送字幕片段…</p>
              </div>
            ) : (
              subtitles.map((item) => (
                <div key={item.id} className={`subtitle-item ${item.isFinal ? 'final' : 'draft'}`}>
                  <div className="subtitle-topline">
                    <span>{item.isFinal ? 'FINAL' : 'DRAFT'}</span>
                    <small>revision {item.revision}</small>
                  </div>
                  <p className="source">{item.sourceText || '暂无原文'}</p>
                  <p className="translation">{item.translatedText || '暂无译文'}</p>
                </div>
              ))
            )}
          </div>
        </article>

        <article className="panel glossary-panel">
          <div className="panel-header">
            <div>
              <h2>术语库</h2>
              <p>可添加、编辑、删除，修改后同步到后端数据库。</p>
            </div>
            <span className="panel-badge">Glossary</span>
          </div>

          <div className="glossary-form">
            <input placeholder="原文术语" value={newSource} onChange={(e) => setNewSource(e.target.value)} />
            <input placeholder="目标译法" value={newTarget} onChange={(e) => setNewTarget(e.target.value)} />
            <input placeholder="备注" value={newNote} onChange={(e) => setNewNote(e.target.value)} />
            <button className="primary-button" onClick={handleAddGlossary}>添加术语</button>
          </div>

          <div className="glossary-form glossary-edit-box">
            <input placeholder="编辑原文术语" value={editingSource} onChange={(e) => setEditingSource(e.target.value)} />
            <input placeholder="编辑目标译法" value={editingTarget} onChange={(e) => setEditingTarget(e.target.value)} />
            <input placeholder="编辑备注" value={editingNote} onChange={(e) => setEditingNote(e.target.value)} />
            <button className="secondary-button" onClick={handleEditGlossary}>保存修改</button>
          </div>

          <div className="glossary-list">
            {glossary.length === 0 ? (
              <div className="empty-state compact">
                <p>暂无术语，添加后会同步到后端数据库。</p>
              </div>
            ) : (
              glossary.map((item) => (
                <div key={item.source} className="glossary-item">
                  <div className="glossary-text">
                    <strong>{item.source}</strong>
                    <span>→ {item.target}</span>
                    {item.note ? <small>{item.note}</small> : null}
                  </div>
                  <div className="glossary-actions">
                    <button className="secondary-button" onClick={() => {
                      setEditingSource(item.source)
                      setEditingTarget(item.target)
                      setEditingNote(item.note ?? '')
                    }}>编辑</button>
                    <button className="danger-button" onClick={() => void handleDeleteGlossary(item.source)}>删除</button>
                  </div>
                </div>
              ))
            )}
          </div>
        </article>
      </section>

      <section className="panel-grid single-grid">
        <article className="panel message-panel">
          <div className="panel-header">
            <div>
              <h2>最近消息</h2>
              <p>用于观察 WebSocket 和字幕事件的实时流转。</p>
            </div>
            <span className="panel-badge">Stream</span>
          </div>
          <div className="message-list">
            {messages.length === 0 ? (
              <div className="empty-state compact">
                <p>等待 WebSocket 消息…</p>
              </div>
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
