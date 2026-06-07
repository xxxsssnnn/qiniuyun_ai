import { useEffect, useMemo, useState } from 'react'

import {
  fetchSessionRevisions,
  fetchTranscriptSessions,
  rollbackTranscriptChunk,
  type StreamTextChunk,
  type TranscriptSessionSummary,
} from '../services/api'

export function CorrectionsPage() {
  const [sessions, setSessions] = useState<TranscriptSessionSummary[]>([])
  const [sessionId, setSessionId] = useState('')
  const [revisions, setRevisions] = useState<StreamTextChunk[]>([])
  const [selectedChunkId, setSelectedChunkId] = useState('')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    void fetchTranscriptSessions()
      .then((items) => {
        setSessions(items)
        setSessionId((current) => current || items[0]?.session_id || '')
      })
      .catch(() => setMessage('会话列表加载失败'))
  }, [])

  useEffect(() => {
    if (!sessionId) {
      setRevisions([])
      return
    }
    setLoading(true)
    setMessage('')
    void fetchSessionRevisions(sessionId)
      .then((items) => {
        setRevisions(items)
        setSelectedChunkId((current) => (
          current && items.some((item) => item.chunk_id === current)
            ? current
            : items[0]?.chunk_id || ''
        ))
      })
      .catch(() => setMessage('修订记录加载失败'))
      .finally(() => setLoading(false))
  }, [sessionId])

  const chunkIds = useMemo(
    () => Array.from(new Set(revisions.map((item) => item.chunk_id))),
    [revisions],
  )
  const current = revisions
    .filter((item) => item.chunk_id === selectedChunkId)
    .sort((left, right) => right.revision - left.revision)
  const latestRevision = current[0]?.revision ?? 0

  const handleRollback = async (revision: number) => {
    if (!sessionId || !selectedChunkId || revision === latestRevision) return
    setLoading(true)
    setMessage('')
    try {
      await rollbackTranscriptChunk(sessionId, selectedChunkId, revision)
      const items = await fetchSessionRevisions(sessionId)
      setRevisions(items)
      setMessage(`已回滚 revision ${revision}，并生成新的修订版本`)
    } catch {
      setMessage('回滚失败，请检查后端服务')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="page-shell">
      <section className="page-hero">
        <span className="badge">Corrections</span>
        <h2>字幕修正与历史</h2>
        <p>查看规则纠错和千问上下文复核产生的版本，也可以恢复历史字幕。</p>
      </section>

      <section className="panel-grid two-cols">
        <article className="panel">
          <h3>修订记录</h3>
          <div className="glossary-form">
            <select value={sessionId} onChange={(event) => setSessionId(event.target.value)}>
              <option value="">选择会话</option>
              {sessions.map((session) => (
                <option key={session.session_id} value={session.session_id}>
                  {session.name || session.session_id}
                </option>
              ))}
            </select>
            <select
              value={selectedChunkId}
              onChange={(event) => setSelectedChunkId(event.target.value)}
              disabled={!chunkIds.length}
            >
              <option value="">选择字幕</option>
              {chunkIds.map((chunkId) => (
                <option key={chunkId} value={chunkId}>{chunkId}</option>
              ))}
            </select>
          </div>
          {message ? <p>{message}</p> : null}
          <div className="message-list">
            {loading ? <p>加载中...</p> : null}
            {!loading && selectedChunkId && !current.length ? <p>暂无修订记录。</p> : null}
            {current.map((item) => (
              <div key={`${item.chunk_id}-${item.revision}`} className="subtitle-item">
                <div className="subtitle-topline">
                  <span>{item.auto_correction ? 'CORRECTED' : 'ORIGINAL'}</span>
                  <small>revision {item.revision}</small>
                </div>
                <p className="source">{item.source_text}</p>
                <p className="translation">{item.translated_text}</p>
                {item.correction_reasons?.length ? (
                  <small>{item.correction_reasons.join('；')}</small>
                ) : null}
                {item.revision !== latestRevision ? (
                  <button
                    className="secondary-button"
                    disabled={loading}
                    onClick={() => void handleRollback(item.revision)}
                  >
                    恢复此版本
                  </button>
                ) : null}
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <h3>自动修正机制</h3>
          <ul className="feature-list">
            <li>第一层快速清理重复词、口头噪声和常见识别混淆。</li>
            <li>第二层由千问结合最近字幕复核当前句和前文。</li>
            <li>每次修正都会生成新 revision，旧版本不会被覆盖。</li>
            <li>恢复历史版本同样会生成新 revision，便于审计。</li>
          </ul>
        </article>
      </section>
    </main>
  )
}
