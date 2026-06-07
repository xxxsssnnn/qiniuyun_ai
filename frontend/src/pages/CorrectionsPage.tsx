import { useEffect, useMemo, useState } from 'react'

import {
  fetchSessionRevisions,
  fetchTranscriptSessions,
  type StreamTextChunk,
  type TranscriptSessionSummary,
} from '../services/api'

const PAGE_SIZE = 5

export function CorrectionsPage() {
  const [sessions, setSessions] = useState<TranscriptSessionSummary[]>([])
  const [sessionId, setSessionId] = useState('')
  const [revisions, setRevisions] = useState<StreamTextChunk[]>([])
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    void fetchTranscriptSessions()
      .then((items) => {
        const correctedSessions = items.filter((item) => item.correction_count > 0)
        setSessions(correctedSessions)
        setSessionId((current) => (
          current && correctedSessions.some((item) => item.session_id === current)
            ? current
            : correctedSessions[0]?.session_id || ''
        ))
      })
      .catch(() => setMessage('会话列表加载失败'))
  }, [])

  useEffect(() => {
    setPage(1)
    if (!sessionId) {
      setRevisions([])
      return
    }
    setLoading(true)
    setMessage('')
    void fetchSessionRevisions(sessionId)
      .then((items) => setRevisions(items.filter((item) => item.auto_correction)))
      .catch(() => {
        setRevisions([])
        setMessage('修订记录加载失败')
      })
      .finally(() => setLoading(false))
  }, [sessionId])

  const totalPages = Math.max(1, Math.ceil(revisions.length / PAGE_SIZE))
  const currentPage = Math.min(page, totalPages)
  const visibleRevisions = useMemo(
    () => revisions.slice(
      (currentPage - 1) * PAGE_SIZE,
      currentPage * PAGE_SIZE,
    ),
    [currentPage, revisions],
  )

  return (
    <main className="page-shell">
      <section className="page-hero">
        <span className="badge">Corrections</span>
        <h2>字幕修正与历史</h2>
        <p>集中查看规则纠错和千问上下文复核产生的字幕修正记录。</p>
      </section>

      <section className="panel-grid two-cols">
        <article className="panel">
          <div className="panel-header">
            <h3>修订记录</h3>
            <small>{loading ? '加载中' : `${revisions.length} 条修正`}</small>
          </div>
          <div className="glossary-form">
            <select value={sessionId} onChange={(event) => setSessionId(event.target.value)}>
              <option value="">选择有修正记录的会话</option>
              {sessions.map((session) => (
                <option key={session.session_id} value={session.session_id}>
                  {session.name || session.session_id}
                </option>
              ))}
            </select>
          </div>
          {message ? <p>{message}</p> : null}
          {!loading && sessions.length === 0 ? (
            <p className="subtle">暂无包含字幕修正记录的会话。</p>
          ) : null}
          <div className="message-list">
            {loading ? <p>加载中...</p> : null}
            {!loading && sessionId && !visibleRevisions.length ? (
              <p className="subtle">该会话暂无字幕修正记录。</p>
            ) : null}
            {visibleRevisions.map((item) => (
              <div key={`${item.chunk_id}-${item.revision}`} className="subtitle-item">
                <p className="source">{item.source_text}</p>
                <p className="translation">{item.translated_text}</p>
                <small className="subtitle-correction-note">
                  {item.correction_reasons?.length
                    ? item.correction_reasons.join('；')
                    : '字幕已自动修正'}
                </small>
              </div>
            ))}
          </div>
          {revisions.length > PAGE_SIZE ? (
            <div className="correction-pagination" aria-label="修正记录分页">
              <button
                type="button"
                className="secondary-button"
                disabled={currentPage <= 1}
                onClick={() => setPage((value) => Math.max(1, value - 1))}
              >
                上一页
              </button>
              <span>第 {currentPage} / {totalPages} 页</span>
              <button
                type="button"
                className="secondary-button"
                disabled={currentPage >= totalPages}
                onClick={() => setPage((value) => Math.min(totalPages, value + 1))}
              >
                下一页
              </button>
            </div>
          ) : null}
        </article>

        <article className="panel">
          <h3>自动修正机制</h3>
          <ul className="feature-list">
            <li>第一层快速清理重复词、口头噪声和常见识别混淆。</li>
            <li>第二层由千问结合最近字幕复核当前句和前文。</li>
            <li>这里只展示实际发生过修正的字幕和修正原因。</li>
            <li>每页展示 5 条记录，便于集中回看修正结果。</li>
          </ul>
        </article>
      </section>
    </main>
  )
}
