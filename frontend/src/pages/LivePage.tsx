import { useEffect, useRef, useState } from 'react'

import {
  createTranscriptSession,
  fetchGlossary,
  fetchSettings,
  type GlossaryEntry,
  fetchLatestChunk,
  fetchSessionChunks,
  fetchTranscriptSessions,
  getSessionExportUrl,
  type TranscriptSessionSummary,
} from '../services/api'
import { startAudioCapture, type AudioCaptureState } from '../services/audio'
import { speakText, stopSpeaking } from '../services/speech'
import { createRealtimeSocketWithFallback, type RealtimeMessage } from '../services/ws'

type SubtitleItem = {
  id: string
  sourceText: string
  translatedText: string
  isFinal: boolean
  revision: number
  correctionCount: number
  updatedAt: number
  autoCorrection?: boolean
  correctionReasons?: string[]
  translationError?: boolean
}

type SourceTranscriptItem = {
  id: string
  text: string
  isFinal: boolean
  updatedAt: number
}

const audioLabels = {
  idle: '待机',
  starting: '启动中',
  recording: '实时传译中',
  stopped: '已停止',
  error: '麦克风异常',
} as const

const connectionLabels = {
  idle: '准备连接',
  connecting: '连接中',
  connected: '链路在线',
  disconnected: '链路离线',
} as const

function isProviderError(sourceText: string, translatedText: string) {
  return /^\[(Qwen|OpenAI|Whisper|.*error|.*unavailable)/i.test(sourceText.trim()) || /^\[(Qwen|OpenAI|Whisper|.*error|.*unavailable)/i.test(translatedText.trim())
}

function getProviderErrorMessage(text: string) {
  if (/unavailable/i.test(text)) return '翻译服务未配置，已保留最新原文'
  return '翻译服务暂时异常，已保留最新原文'
}

type LivePageProps = {
  sessionId: string
  onSessionChange: (sessionId: string) => void
}

export function LivePage({ sessionId, onSessionChange }: LivePageProps) {
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'connecting' | 'connected' | 'disconnected'>('idle')
  const [audioState, setAudioState] = useState<AudioCaptureState>('idle')
  const [messages, setMessages] = useState<RealtimeMessage[]>([])
  const [subtitles, setSubtitles] = useState<SubtitleItem[]>([])
  const [sourceTranscript, setSourceTranscript] = useState<SourceTranscriptItem[]>([])
  const [selectedSourceId, setSelectedSourceId] = useState<string | null>(null)
  const [sessions, setSessions] = useState<TranscriptSessionSummary[]>([])
  const [newSessionName, setNewSessionName] = useState('')
  const [creatingSession, setCreatingSession] = useState(false)
  const [socket, setSocket] = useState<{ current: WebSocket, send: (data: string | Blob | ArrayBufferLike | ArrayBufferView) => void, close: () => void } | null>(null)
  const [audioSession, setAudioSession] = useState<{ stop: () => Promise<void> } | null>(null)
  const audioSessionRef = useRef<{ stop: () => Promise<void> } | null>(null)
  const [glossary, setGlossary] = useState<GlossaryEntry[]>([])
  const [autoSpeak, setAutoSpeak] = useState(true)
  const autoSpeakRef = useRef(true)
  const speechLanguageRef = useRef('zh-CN')
  const lastSpokenRef = useRef('')
  const canRecord = connectionStatus === 'connected' && audioState !== 'recording' && audioState !== 'starting'
  const visibleSubtitles = subtitles.filter((item) => item.isFinal && (item.sourceText.trim() || item.translatedText.trim()))
  const latestSubtitle = visibleSubtitles[0]
  const selectedSource = selectedSourceId
    ? sourceTranscript.find((item) => item.id === selectedSourceId)
    : null
  const selectedSubtitle = selectedSource
    ? visibleSubtitles.find((item) => item.id === selectedSource.id)
      ?? visibleSubtitles.find((item) => item.sourceText.trim() === selectedSource.text.trim())
    : null
  const displayedSubtitle = selectedSourceId ? selectedSubtitle : latestSubtitle
  const totalCorrections = visibleSubtitles.reduce((sum, item) => sum + item.correctionCount, 0)

  useEffect(() => {
    void fetchTranscriptSessions()
      .then(async (items) => {
        setSessions(items)
        if (sessionId) return
        if (items.length) {
          onSessionChange(items[0].session_id)
          return
        }
        const created = await createTranscriptSession('我的第一次传译')
        setSessions([created])
        onSessionChange(created.session_id)
      })
      .catch(() => undefined)
  }, [sessionId, onSessionChange])

  useEffect(() => {
    if (!sessionId) return
    setSubtitles([])
    setSourceTranscript([])
    setSelectedSourceId(null)
    setConnectionStatus('connecting')
    const realtimeSocket = createRealtimeSocketWithFallback(sessionId, {
      onOpen: () => setConnectionStatus('connected'),
      onClose: () => setConnectionStatus('disconnected'),
      onError: () => setConnectionStatus('disconnected'),
      onFallback: (url) => setMessages((prev) => [...prev.slice(-19), { type: 'status', session_id: sessionId, payload: { message: `尝试连接：${url}` } }]),
      onMessage: (event) => {
        try {
          const message = JSON.parse(event.data as string) as RealtimeMessage & { payload?: any }
          setMessages((prev) => [...prev.slice(-19), message])

          if (message.type === 'source_partial' || message.type === 'source_final') {
            const payload = message.payload as { chunk_id?: string; sourceText?: string; source_text?: string; isFinal?: boolean; is_final?: boolean }
            const sourceText = payload.sourceText ?? payload.source_text ?? ''
            if (payload.chunk_id && sourceText.trim() && !isProviderError(sourceText, '')) {
              setSourceTranscript((current) => {
                const updatedSource: SourceTranscriptItem = {
                  id: payload.chunk_id!,
                  text: sourceText,
                  isFinal: payload.isFinal ?? payload.is_final ?? message.type === 'source_final',
                  updatedAt: Date.now(),
                }
                return [updatedSource, ...current.filter((item) => item.id !== payload.chunk_id)].slice(0, 16)
              })
            }
            return
          }

          if (message.type === 'chunk' || message.type === 'translated' || message.type === 'revision' || message.type === 'correction') {
            const payload = message.payload as Partial<SubtitleItem> & { chunk_id?: string; autoCorrection?: boolean; reasons?: string[] }
            if (!payload?.chunk_id) return
            setSubtitles((prev) => {
              const existing = prev.find((item) => item.id === payload.chunk_id)
              const sourceText = payload.sourceText ?? (payload as any).source_text ?? existing?.sourceText ?? ''
              const translatedText = payload.translatedText ?? (payload as any).translated_text ?? existing?.translatedText ?? ''
              const isFinal = payload.isFinal ?? (payload as any).is_final ?? existing?.isFinal ?? false
              const revision = payload.revision ?? (payload as any).currentRevision ?? existing?.revision ?? 0
              const autoCorrection = payload.autoCorrection ?? existing?.autoCorrection ?? false
              const correctionReasons = payload.reasons ?? payload.correctionReasons ?? existing?.correctionReasons ?? []
              const providerError = isProviderError(sourceText, translatedText)

              if (sourceText.trim() && !isProviderError(sourceText, '')) {
                setSourceTranscript((current) => {
                  const updatedSource: SourceTranscriptItem = { id: payload.chunk_id!, text: sourceText, isFinal, updatedAt: Date.now() }
                  return [updatedSource, ...current.filter((item) => item.id !== payload.chunk_id)].slice(0, 16)
                })
              }

              if (!isFinal || (!sourceText.trim() && !translatedText.trim())) {
                return prev.filter((item) => item.id !== payload.chunk_id)
              }

              const updated: SubtitleItem = {
                id: payload.chunk_id!,
                sourceText,
                translatedText: providerError ? getProviderErrorMessage(translatedText || sourceText) : translatedText,
                isFinal,
                revision,
                correctionCount: existing ? existing.correctionCount + (message.type === 'correction' || revision > existing.revision ? 1 : 0) : (autoCorrection ? 1 : 0),
                updatedAt: Date.now(),
                autoCorrection,
                correctionReasons,
                translationError: providerError,
              }
              if (!providerError && autoSpeakRef.current && translatedText && translatedText !== lastSpokenRef.current) {
                const spoke = speakText(translatedText, speechLanguageRef.current)
                if (spoke) lastSpokenRef.current = translatedText
              }
              return [updated, ...prev.filter((item) => item.id !== payload.chunk_id)].slice(0, 8)
            })
          }
        } catch {
          // ignore malformed payloads
        }
      },
    })
    setSocket(realtimeSocket)

    void fetchSessionChunks(sessionId).then((chunks) => {
      if (!chunks.length) return fetchLatestChunk(sessionId).then((chunk) => (chunk ? [chunk] : []))
      return chunks
    }).then((chunks) => {
      if (!chunks.length) return
      setSubtitles(chunks.slice(-8).reverse().map((chunk: any) => {
        const sourceText = chunk.sourceText ?? chunk.source_text ?? ''
        const translatedText = chunk.translatedText ?? chunk.translated_text ?? ''
        const providerError = isProviderError(sourceText, translatedText)
        return {
          id: chunk.chunk_id,
          sourceText,
          translatedText: providerError ? getProviderErrorMessage(translatedText || sourceText) : translatedText,
          isFinal: chunk.isFinal ?? chunk.is_final ?? false,
          revision: chunk.revision ?? 0,
          correctionCount: chunk.auto_correction ? 1 : 0,
          autoCorrection: chunk.auto_correction ?? false,
          correctionReasons: chunk.correction_reasons ?? [],
          translationError: providerError,
          updatedAt: Date.now(),
        }
      }))
    }).catch(() => undefined)

    return () => {
      audioSessionRef.current?.stop()
      audioSessionRef.current = null
      realtimeSocket.close()
      stopSpeaking()
    }
  }, [sessionId])

  useEffect(() => {
    void fetchGlossary().then(setGlossary).catch(() => setGlossary([]))
    void fetchSettings().then((settings) => {
      const language = settings.target_language ?? 'zh'
      speechLanguageRef.current = { zh: 'zh-CN', yue: 'zh-HK', en: 'en-US', ja: 'ja-JP', ko: 'ko-KR', fr: 'fr-FR', de: 'de-DE', es: 'es-ES', ru: 'ru-RU', pt: 'pt-PT', it: 'it-IT', ar: 'ar-SA', th: 'th-TH', vi: 'vi-VN' }[language] ?? language
    }).catch(() => undefined)
  }, [])

  const handleStartDemo = () => {
    if (!socket || socket.current.readyState !== WebSocket.OPEN) return
    socket.send(JSON.stringify({ type: 'start_demo' }))
  }

  const handleCreateSession = async () => {
    if (creatingSession || audioState === 'recording') return
    setCreatingSession(true)
    try {
      const created = await createTranscriptSession(
        newSessionName.trim() || `新会话 ${sessions.length + 1}`,
      )
      setSessions((current) => [created, ...current])
      setNewSessionName('')
      onSessionChange(created.session_id)
    } finally {
      setCreatingSession(false)
    }
  }

  const handleStartAudio = async () => {
    if (!socket || socket.current.readyState !== WebSocket.OPEN || !canRecord) return
    try {
      setAudioState('starting')
      socket.send(JSON.stringify({ type: 'start_audio', session_id: sessionId }))
      const session = await startAudioCapture((chunk) => {
        if (socket.current.readyState === WebSocket.OPEN) socket.send(chunk)
      })
      audioSessionRef.current = session
      setAudioSession(session)
      setAudioState('recording')
    } catch {
      setAudioState('error')
    }
  }

  const handleStopAudio = async () => {
    await audioSession?.stop()
    audioSessionRef.current = null
    setAudioSession(null)
    setAudioState('stopped')
    if (socket && socket.current.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: 'stop_audio', session_id: sessionId }))
  }

  const handleToggleAutoSpeak = () => {
    const nextAutoSpeak = !autoSpeakRef.current
    autoSpeakRef.current = nextAutoSpeak
    setAutoSpeak(nextAutoSpeak)
    if (!nextAutoSpeak) stopSpeaking()
  }

  const handleExport = (format: 'txt' | 'srt' | 'json') => {
    window.open(getSessionExportUrl(sessionId, format), '_blank', 'noopener,noreferrer')
  }

  return (
    <main className="sci-live-page">
      <section className="sci-toolbar">
        <div className="sci-brandline">
          <span className={`sci-signal ${audioState === 'recording' ? 'active' : ''}`} />
          <div>
            <strong>Realtime Interpretation Core</strong>
            <span>{connectionLabels[connectionStatus]} · {audioLabels[audioState]}</span>
          </div>
        </div>
        <div className="sci-metrics">
          <span>译文 {visibleSubtitles.length}</span>
          <span>原文 {sourceTranscript.length}</span>
          <span>纠错 {totalCorrections}</span>
          <span>术语 {glossary.length}</span>
        </div>
        <div className="sci-actions">
          <button className="primary-button" onClick={handleStartAudio} disabled={!canRecord}>{audioState === 'recording' ? '运行中' : '启动传译'}</button>
          <button className="secondary-button" onClick={handleStopAudio} disabled={audioState !== 'recording'}>停止</button>
          <button className="secondary-button" onClick={handleStartDemo} disabled={connectionStatus !== 'connected'}>演示</button>
          <button className="secondary-button" onClick={handleToggleAutoSpeak}>{autoSpeak ? '播报 ON' : '播报 OFF'}</button>
          <button className="secondary-button" onClick={() => handleExport('txt')} disabled={!visibleSubtitles.length}>导出 TXT</button>
          <button className="secondary-button" onClick={() => handleExport('srt')} disabled={!visibleSubtitles.length}>导出 SRT</button>
        </div>
      </section>

      <section className="sci-session-bar" aria-label="实时传译会话">
        <label>
          <span>当前会话</span>
          <select
            value={sessionId}
            onChange={(event) => onSessionChange(event.target.value)}
            disabled={audioState === 'recording' || creatingSession}
          >
            {sessions.map((session) => (
              <option key={session.session_id} value={session.session_id}>
                {session.name || session.session_id}
              </option>
            ))}
          </select>
        </label>
        <label className="sci-session-name">
          <span>新会话名称</span>
          <input
            value={newSessionName}
            onChange={(event) => setNewSessionName(event.target.value)}
            placeholder="例如：AI 技术大会"
            maxLength={160}
            disabled={audioState === 'recording' || creatingSession}
            onKeyDown={(event) => {
              if (event.key === 'Enter') void handleCreateSession()
            }}
          />
        </label>
        <button
          type="button"
          className="primary-button"
          onClick={() => void handleCreateSession()}
          disabled={audioState === 'recording' || creatingSession}
        >
          {creatingSession ? '创建中...' : '新建会话'}
        </button>
        <small>每个会话的字幕、纠错与导出记录均独立保存。</small>
      </section>

      <section className="sci-stage-grid">
        <article className="sci-panel sci-translation-panel">
          <div className="sci-panel-head">
            <span>TRANSLATION OUTPUT</span>
            <div className="sci-panel-head-actions">
              {selectedSourceId ? (
                <button type="button" className="sci-latest-button" onClick={() => setSelectedSourceId(null)}>
                  返回最新
                </button>
              ) : null}
              <small>{selectedSourceId ? 'SELECTED' : displayedSubtitle ? 'LATEST' : 'STANDBY'}</small>
            </div>
          </div>
          <div className="sci-translation-screen">
            {displayedSubtitle ? (
              <>
                <p>{displayedSubtitle.sourceText || '正在等待原文...'}</p>
                <h2>{displayedSubtitle.translatedText || '译文生成中...'}</h2>
                {displayedSubtitle.translationError ? (
                  <small className="sci-correction-badge">请在设置中检查翻译模型与 API Key</small>
                ) : null}
                {displayedSubtitle.autoCorrection ? (
                  <small className="sci-correction-badge">
                    AI 已自动纠错{displayedSubtitle.correctionReasons?.length ? `：${displayedSubtitle.correctionReasons.join('、')}` : ''}
                  </small>
                ) : null}
              </>
            ) : selectedSource ? (
              <>
                <p>{selectedSource.text}</p>
                <h2>译文生成中...</h2>
              </>
            ) : (
              <div className="sci-empty-screen">
                <h2>等待实时传译</h2>
                <p>点击“启动传译”，允许麦克风权限后开始显示内容。</p>
              </div>
            )}
          </div>
          {visibleSubtitles.length > 1 ? (
            <div className="sci-history-strip">
              {visibleSubtitles.slice(1, 4).map((item) => (
                <div key={item.id}>
                  <span>{item.sourceText || '原文暂缺'}</span>
                  <strong>{item.translatedText || '译文生成中'}</strong>
                </div>
              ))}
            </div>
          ) : null}
        </article>

        <article className="sci-panel sci-source-panel">
          <div className="sci-panel-head">
            <span>原文实时记录</span>
            <small>{audioState === 'recording' ? 'LIVE' : 'IDLE'}</small>
          </div>
          <div className="sci-source-stream">
            {sourceTranscript.length === 0 ? (
              <div className="sci-source-empty">开始后，识别到的原文会实时出现在这里。</div>
            ) : sourceTranscript.map((item) => (
              <button
                type="button"
                key={item.id}
                className={`sci-source-line ${item.isFinal ? 'final' : 'draft'} ${selectedSourceId === item.id ? 'selected' : ''}`}
                aria-pressed={selectedSourceId === item.id}
                onClick={() => setSelectedSourceId(item.id)}
              >
                <p>{item.text}</p>
                <small>
                  {selectedSourceId === item.id ? '正在查看' : item.isFinal ? '已确认' : '识别中'}
                  {' · '}
                  {new Date(item.updatedAt).toLocaleTimeString()}
                </small>
              </button>
            ))}
          </div>
        </article>
      </section>
    </main>
  )
}
