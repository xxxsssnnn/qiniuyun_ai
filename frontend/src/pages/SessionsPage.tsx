import { useEffect, useState } from 'react'

import { fetchSessionChunks, fetchTranscriptSessions, getSessionExportUrl, type StreamTextChunk, type TranscriptSessionSummary } from '../services/api'

const SESSION_PAGE_SIZE = 6
const CHUNK_PAGE_SIZE = 5

type SessionsPageProps = {
  onOpenSession: (sessionId: string) => void
}

export function SessionsPage({ onOpenSession }: SessionsPageProps) {
  const [sessions, setSessions] = useState<TranscriptSessionSummary[]>([])
  const [selectedSessionId, setSelectedSessionId] = useState('')
  const [chunks, setChunks] = useState<StreamTextChunk[]>([])
  const [sessionPage, setSessionPage] = useState(1)
  const [chunkPage, setChunkPage] = useState(1)
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
    setChunkPage(1)
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
  const sessionTotalPages = Math.max(1, Math.ceil(sessions.length / SESSION_PAGE_SIZE))
  const chunkTotalPages = Math.max(1, Math.ceil(chunks.length / CHUNK_PAGE_SIZE))
  const currentSessionPage = Math.min(sessionPage, sessionTotalPages)
  const currentChunkPage = Math.min(chunkPage, chunkTotalPages)
  const visibleSessions = sessions.slice(
    (currentSessionPage - 1) * SESSION_PAGE_SIZE,
    currentSessionPage * SESSION_PAGE_SIZE,
  )
  const visibleChunks = chunks.slice(
    (currentChunkPage - 1) * CHUNK_PAGE_SIZE,
    currentChunkPage * CHUNK_PAGE_SIZE,
  )

  return (
    <main className="page-shell">
      <section className="page-hero">
        <span className="badge">Sessions</span>
        <h2>历史会话与字幕归档</h2>
        <p>查看已持久化的传译会话，支持回放字幕内容并导出 TXT、SRT 或 JSON。</p>
      </section>

      <section className="panel-grid sessions-grid">
        <article className="panel">
          <div className="panel-header">
            <h3>会话列表</h3>
            <small>{loading ? '加载中' : `${sessions.length} 个会话`}</small>
          </div>
          {sessions.length === 0 ? (
            <p className="subtle">暂无历史会话。完成一次实时传译后会自动归档。</p>
          ) : (
            <div className="message-list">
              {visibleSessions.map((session) => (
                <button
                  key={session.session_id}
                  className={session.session_id === selectedSessionId ? 'session-row active' : 'session-row'}
                  onClick={() => setSelectedSessionId(session.session_id)}
                >
                  <strong>{session.name || session.session_id}</strong>
                  <span>{session.chunk_count} 条字幕 · {session.correction_count} 次纠错</span>
                  <small>{session.latest_updated_at ? new Date(session.latest_updated_at).toLocaleString() : '无更新时间'}</small>
                </button>
              ))}
            </div>
          )}
          {sessions.length > SESSION_PAGE_SIZE ? (
            <div className="correction-pagination" aria-label="会话列表分页">
              <button
                type="button"
                className="secondary-button"
                disabled={currentSessionPage <= 1}
                onClick={() => setSessionPage((value) => Math.max(1, value - 1))}
              >
                上一页
              </button>
              <span>第 {currentSessionPage} / {sessionTotalPages} 页</span>
              <button
                type="button"
                className="secondary-button"
                disabled={currentSessionPage >= sessionTotalPages}
                onClick={() => setSessionPage((value) => Math.min(sessionTotalPages, value + 1))}
              >
                下一页
              </button>
            </div>
          ) : null}
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>会话详情</h3>
            <small>{selectedSession ? `${chunks.length} 条字幕` : '未选择'}</small>
          </div>
          {selectedSession ? (
            <>
              <div className="hero-actions">
                <button className="primary-button" onClick={() => onOpenSession(selectedSession.session_id)}>在实时传译中打开</button>
                <a className="secondary-button" href={getSessionExportUrl(selectedSession.session_id, 'txt')} target="_blank" rel="noreferrer">导出 TXT</a>
                <a className="secondary-button" href={getSessionExportUrl(selectedSession.session_id, 'srt')} target="_blank" rel="noreferrer">导出 SRT</a>
                <a className="secondary-button" href={getSessionExportUrl(selectedSession.session_id, 'json')} target="_blank" rel="noreferrer">导出 JSON</a>
              </div>
              <div className="message-list">
                {chunks.length === 0 ? (
                  <p className="subtle">该会话暂无最终字幕。</p>
                ) : visibleChunks.map((chunk) => (
                  <div key={chunk.chunk_id} className="subtitle-item">
                    <p className="source">{chunk.source_text}</p>
                    <p className="translation">{chunk.translated_text}</p>
                    {chunk.auto_correction ? (
                      <small className="subtitle-correction-note">
                        已自动修正
                        {chunk.correction_reasons?.length
                          ? `：${chunk.correction_reasons.join('；')}`
                          : ''}
                      </small>
                    ) : null}
                  </div>
                ))}
              </div>
              {chunks.length > CHUNK_PAGE_SIZE ? (
                <div className="correction-pagination" aria-label="会话字幕分页">
                  <button
                    type="button"
                    className="secondary-button"
                    disabled={currentChunkPage <= 1}
                    onClick={() => setChunkPage((value) => Math.max(1, value - 1))}
                  >
                    上一页
                  </button>
                  <span>第 {currentChunkPage} / {chunkTotalPages} 页</span>
                  <button
                    type="button"
                    className="secondary-button"
                    disabled={currentChunkPage >= chunkTotalPages}
                    onClick={() => setChunkPage((value) => Math.min(chunkTotalPages, value + 1))}
                  >
                    下一页
                  </button>
                </div>
              ) : null}
            </>
          ) : (
            <p className="subtle">请选择一个会话查看详情。</p>
          )}
        </article>
      </section>
    </main>
  )
}
