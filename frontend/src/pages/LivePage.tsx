import { useEffect, useMemo, useRef, useState } from 'react'

import { fetchGlossary, fetchSettings, type GlossaryEntry, fetchLatestChunk, fetchSessionChunks, getSessionExportUrl } from '../services/api'
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

export function LivePage() {
  const sessionId = useMemo(() => 'demo-session', [])
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'connecting' | 'connected' | 'disconnected'>('idle')
  const [audioState, setAudioState] = useState<AudioCaptureState>('idle')
  const [messages, setMessages] = useState<RealtimeMessage[]>([])
  const [subtitles, setSubtitles] = useState<SubtitleItem[]>([])
  const [sourceTranscript, setSourceTranscript] = useState<SourceTranscriptItem[]>([])
  const [socket, setSocket] = useState<{ current: WebSocket, send: (data: string | Blob | ArrayBufferLike | ArrayBufferView) => void, close: () => void } | null>(null)
  const [audioSession, setAudioSession] = useState<{ stop: () => void } | null>(null)
  const audioSessionRef = useRef<{ stop: () => void } | null>(null)
  const [glossary, setGlossary] = useState<GlossaryEntry[]>([])
  const [autoSpeak, setAutoSpeak] = useState(true)
  const autoSpeakRef = useRef(true)
  const speechLanguageRef = useRef('zh-CN')
  const lastSpokenRef = useRef('')
  const canRecord = connectionStatus === 'connected' && audioState !== 'recording' && audioState !== 'starting'
  const visibleSubtitles = subtitles.filter((item) => item.isFinal && (item.sourceText.trim() || item.translatedText.trim()))
  const latestSubtitle = visibleSubtitles[0]
  const totalCorrections = visibleSubtitles.reduce((sum, item) => sum + item.correctionCount, 0)

  useEffect(() => {
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

              if (sourceText.trim() && !providerError) {
                setSourceTranscript((current) => {
                  const updatedSource: SourceTranscriptItem = { id: payload.chunk_id!, text: sourceText, isFinal, updatedAt: Date.now() }
                  return [updatedSource, ...current.filter((item) => item.id !== payload.chunk_id)].slice(0, 16)
                })
              }

              if (!isFinal || providerError || (!sourceText.trim() && !translatedText.trim())) {
                return prev.filter((item) => item.id !== payload.chunk_id)
              }

              const updated: SubtitleItem = {
                id: payload.chunk_id!,
                sourceText,
                translatedText,
                isFinal,
                revision,
                correctionCount: existing ? existing.correctionCount + (message.type === 'correction' || revision > existing.revision ? 1 : 0) : (autoCorrection ? 1 : 0),
                updatedAt: Date.now(),
                autoCorrection,
                correctionReasons,
              }
              if (autoSpeakRef.current && translatedText && translatedText !== lastSpokenRef.current) {
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
      if (!chunks.length) return fetchLatestChunk().then((chunk) => (chunk ? [chunk] : []))
      return chunks
    }).then((chunks) => {
      if (!chunks.length) return
      setSubtitles(chunks.slice(-8).reverse().map((chunk: any) => ({
        id: chunk.chunk_id,
        sourceText: chunk.sourceText ?? chunk.source_text ?? '',
        translatedText: chunk.translatedText ?? chunk.translated_text ?? '',
        isFinal: chunk.isFinal ?? chunk.is_final ?? false,
        revision: chunk.revision ?? 0,
        correctionCount: chunk.auto_correction ? 1 : 0,
        autoCorrection: chunk.auto_correction ?? false,
        correctionReasons: chunk.correction_reasons ?? [],
        updatedAt: Date.now(),
      })))
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

  const handleStopAudio = () => {
    audioSession?.stop()
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

      <section className="sci-stage-grid">
        <article className="sci-panel sci-translation-panel">
          <div className="sci-panel-head">
            <span>TRANSLATION OUTPUT</span>
            <small>{latestSubtitle ? 'FINAL' : 'STANDBY'}</small>
          </div>
          <div className="sci-translation-screen">
            {latestSubtitle ? (
              <>
                <p>{latestSubtitle.sourceText || '正在等待原文...'}</p>
                <h2>{latestSubtitle.translatedText || '译文生成中...'}</h2>
                {latestSubtitle.autoCorrection ? (
                  <small className="sci-correction-badge">
                    AI 已自动纠错{latestSubtitle.correctionReasons?.length ? `：${latestSubtitle.correctionReasons.join('、')}` : ''}
                  </small>
                ) : null}
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
              <div key={item.id} className={`sci-source-line ${item.isFinal ? 'final' : 'draft'}`}>
                <p>{item.text}</p>
                <small>{item.isFinal ? '已确认' : '识别中'} · {new Date(item.updatedAt).toLocaleTimeString()}</small>
              </div>
            ))}
          </div>
        </article>
      </section>
    </main>
  )
}
