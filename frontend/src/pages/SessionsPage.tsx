import { useEffect, useState } from 'react'

import { fetchSessionChunks, fetchTranscriptSessions, getSessionExportUrl, type StreamTextChunk, type TranscriptSessionSummary } from '../services/api'

export function SessionsPage() {
  const [sessions, setSessions] = useState<TranscriptSessionSummary[]>([])
  const [selectedSessionId, setSelectedSessionId] = useState('')
  const [chunks, setChunks] = useState<StreamTextChunk[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    void fetchTranscriptSessions()
      .then((items) => {
        setSessions(items)
        if (items.length && !selectedSessionId) setSelectedSessionId(items[0].session_id)
      })
      .catch(() => setSessions([]))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!selectedSessionId) {
      setChunks([])
      return
    }
    setLoading(true)
    void fetchSessionChunks(selectedSessionId)
      .then(setChunks)
      .catch(() => setChunks([]))
      .finally(() => setLoading(false))
  }, [selectedSessionId])

  const selectedSession = sessions.find((item) => item.session_id === selectedSessionId)

  return (
    <main className="page-shell">
      <section className="page-hero">
        <span className="badge">Sessions</span>
        <h2>历史会话与字幕归档</h2>
        <p>查看已持久化的传译会话，支持回放字幕内容并导出 TXT、SRT 或 JSON。</p>
      </section>

      <section className="panel-grid two-cols">
        <article className="panel">
          <div className="panel-header">
            <h3>会话列表</h3>
            <small>{loading ? '加载中' : `${sessions.length} 个会话`}</small>
          </div>
          {sessions.length === 0 ? (
            <p className="subtle">暂无历史会话。完成一次实时传译后会自动归档。</p>
          ) : (
            <div className="message-list">
              {sessions.map((session) => (
                <button
                  key={session.session_id}
                  className={session.session_id === selectedSessionId ? 'session-row active' : 'session-row'}
                  onClick={() => setSelectedSessionId(session.session_id)}
                >
                  <strong>{session.session_id}</strong>
                  <span>{session.chunk_count} 条字幕 · {session.correction_count} 次纠错</span>
                  <small>{session.latest_updated_at ? new Date(session.latest_updated_at).toLocaleString() : '无更新时间'}</small>
                </button>
              ))}
            </div>
          )}
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>会话详情</h3>
            <small>{selectedSession ? `${chunks.length} 条字幕` : '未选择'}</small>
          </div>
          {selectedSession ? (
            <>
              <div className="hero-actions">
                <a className="secondary-button" href={getSessionExportUrl(selectedSession.session_id, 'txt')} target="_blank" rel="noreferrer">导出 TXT</a>
                <a className="secondary-button" href={getSessionExportUrl(selectedSession.session_id, 'srt')} target="_blank" rel="noreferrer">导出 SRT</a>
                <a className="secondary-button" href={getSessionExportUrl(selectedSession.session_id, 'json')} target="_blank" rel="noreferrer">导出 JSON</a>
              </div>
              <div className="message-list">
                {chunks.length === 0 ? (
                  <p className="subtle">该会话暂无最终字幕。</p>
                ) : chunks.map((chunk) => (
                  <div key={chunk.chunk_id} className="subtitle-item">
                    <div className="subtitle-topline">
                      <span>{chunk.chunk_id}</span>
                      <small>revision {chunk.revision ?? 0}</small>
                    </div>
                    <p className="source">{chunk.source_text}</p>
                    <p className="translation">{chunk.translated_text}</p>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p className="subtle">请选择一个会话查看详情。</p>
          )}
        </article>
      </section>
    </main>
  )
}
