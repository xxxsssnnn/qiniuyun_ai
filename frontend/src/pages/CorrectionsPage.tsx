import { useEffect, useMemo, useState } from 'react'

import {
  fetchSessionRevisions,
  fetchTranscriptSessions,
  restoreDirectTranslation,
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

  const reloadRevisions = async (targetSessionId: string) => {
    const items = await fetchSessionRevisions(targetSessionId)
    setRevisions(items.filter((item) => item.auto_correction))
  }

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
    void reloadRevisions(sessionId)
      .catch(() => {
        setRevisions([])
        setMessage('修订记录加载失败')
      })
      .finally(() => setLoading(false))
  }, [sessionId])

  const handleRestoreDirect = async (item: StreamTextChunk) => {
    if (!sessionId || !item.direct_translation) return
    setLoading(true)
    setMessage('')
    try {
      await restoreDirectTranslation(sessionId, item.chunk_id)
      await reloadRevisions(sessionId)
      setMessage('已恢复原始直译，并生成新的修订记录。')
    } catch {
      setMessage('恢复原始直译失败，请检查后端服务。')
    } finally {
      setLoading(false)
    }
  }

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

      <section className="panel-grid corrections-grid">
        <article className="panel">
          <div className="panel-header">
            <h3>修订记录</h3>
            <small>{loading ? '加载中' : `${revisions.length} 条修正`}</small>
          </div>
          <div className="glossary-form">
            <select
              value={sessionId}
              onChange={(event) => setSessionId(event.target.value)}
              disabled={!sessions.length}
            >
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
                <div className="correction-translation-block">
                  <small>原始直译</small>
                  <p>{item.direct_translation || item.translated_text}</p>
                </div>
                <div className="correction-translation-block corrected">
                  <small>修正后译文</small>
                  <p className="translation">{item.translated_text}</p>
                </div>
                <small className="subtitle-correction-note">
                  {item.correction_reasons?.length
                    ? item.correction_reasons.join('；')
                    : '字幕已自动修正'}
                </small>
                {item.direct_translation && item.translated_text !== item.direct_translation ? (
                  <button
                    type="button"
                    className="secondary-button correction-restore-button"
                    disabled={loading}
                    onClick={() => void handleRestoreDirect(item)}
                  >
                    恢复原始直译
                  </button>
                ) : null}
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

        <article className="panel correction-help-panel">
          <h3>修正说明</h3>
          <ul className="feature-list">
            <li>规则清理口头噪声和识别混淆。</li>
            <li>千问结合上下文复核字幕。</li>
            <li>每页展示 5 条修正记录。</li>
          </ul>
        </article>
      </section>
    </main>
  )
}
