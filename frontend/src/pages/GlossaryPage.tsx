import { useEffect, useMemo, useState } from 'react'

import {
  addGlossaryEntry,
  deleteGlossaryConversion,
  deleteGlossaryEntry,
  fetchGlossary,
  fetchGlossaryConversions,
  fetchTranscriptSessions,
  toggleGlossaryConversion,
  updateGlossaryEntry,
  type GlossaryConversionRecord,
  type GlossaryEntry,
  type TranscriptSessionSummary,
} from '../services/api'

type Feedback = { kind: 'success' | 'error'; message: string } | null

const GLOSSARY_PAGE_SIZE = 4
const CONVERSION_PAGE_SIZE = 5

export function GlossaryPage() {
  const [glossary, setGlossary] = useState<GlossaryEntry[]>([])
  const [sessions, setSessions] = useState<TranscriptSessionSummary[]>([])
  const [sessionId, setSessionId] = useState('')
  const [conversions, setConversions] = useState<GlossaryConversionRecord[]>([])
  const [newSource, setNewSource] = useState('')
  const [newTarget, setNewTarget] = useState('')
  const [newNote, setNewNote] = useState('')
  const [editingOriginalSource, setEditingOriginalSource] = useState('')
  const [editingSource, setEditingSource] = useState('')
  const [editingTarget, setEditingTarget] = useState('')
  const [editingNote, setEditingNote] = useState('')
  const [glossaryPage, setGlossaryPage] = useState(1)
  const [conversionPage, setConversionPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState<Feedback>(null)

  const loadGlossary = async () => {
    const items = await fetchGlossary()
    setGlossary(items)
  }

  const loadConversions = async (targetSessionId: string) => {
    if (!targetSessionId) {
      setConversions([])
      return
    }
    const items = await fetchGlossaryConversions(targetSessionId)
    setConversions(items)
  }

  useEffect(() => {
    setLoading(true)
    void Promise.all([fetchGlossary(), fetchTranscriptSessions()])
      .then(([glossaryItems, sessionItems]) => {
        setGlossary(glossaryItems)
        setSessions(sessionItems)
        const nextSessionId = sessionItems[0]?.session_id || ''
        setSessionId(nextSessionId)
        return loadConversions(nextSessionId)
      })
      .catch((error) => {
        setFeedback({
          kind: 'error',
          message: error instanceof Error ? error.message : '读取术语库失败，请确认后端已启动。',
        })
      })
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    setConversionPage(1)
    void loadConversions(sessionId).catch(() => setConversions([]))
  }, [sessionId])

  const glossaryTotalPages = Math.max(1, Math.ceil(glossary.length / GLOSSARY_PAGE_SIZE))
  const currentGlossaryPage = Math.min(glossaryPage, glossaryTotalPages)
  const visibleGlossary = useMemo(
    () => glossary.slice(
      (currentGlossaryPage - 1) * GLOSSARY_PAGE_SIZE,
      currentGlossaryPage * GLOSSARY_PAGE_SIZE,
    ),
    [currentGlossaryPage, glossary],
  )

  const conversionTotalPages = Math.max(1, Math.ceil(conversions.length / CONVERSION_PAGE_SIZE))
  const currentConversionPage = Math.min(conversionPage, conversionTotalPages)
  const visibleConversions = useMemo(
    () => conversions.slice(
      (currentConversionPage - 1) * CONVERSION_PAGE_SIZE,
      currentConversionPage * CONVERSION_PAGE_SIZE,
    ),
    [conversions, currentConversionPage],
  )

  const resetEditing = () => {
    setEditingOriginalSource('')
    setEditingSource('')
    setEditingTarget('')
    setEditingNote('')
  }

  const handleAdd = async () => {
    if (!newSource.trim() || !newTarget.trim()) return
    setSaving(true)
    setFeedback(null)
    try {
      const created = await addGlossaryEntry({
        source: newSource.trim(),
        target: newTarget.trim(),
        note: newNote.trim(),
      })
      await loadGlossary()
      setNewSource('')
      setNewTarget('')
      setNewNote('')
      setFeedback({ kind: 'success', message: `术语“${created.source}”已保存。` })
    } catch (error) {
      setFeedback({ kind: 'error', message: error instanceof Error ? error.message : '添加术语失败。' })
    } finally {
      setSaving(false)
    }
  }

  const handleStartEdit = (item: GlossaryEntry) => {
    setEditingOriginalSource(item.source)
    setEditingSource(item.source)
    setEditingTarget(item.target)
    setEditingNote(item.note ?? '')
  }

  const handleUpdate = async () => {
    if (!editingOriginalSource || !editingSource.trim() || !editingTarget.trim()) return
    setSaving(true)
    setFeedback(null)
    try {
      const updated = await updateGlossaryEntry(editingOriginalSource, {
        source: editingSource.trim(),
        target: editingTarget.trim(),
        note: editingNote.trim(),
      })
      await loadGlossary()
      resetEditing()
      setFeedback({ kind: 'success', message: `术语“${updated.source}”已更新。` })
    } catch (error) {
      setFeedback({ kind: 'error', message: error instanceof Error ? error.message : '更新术语失败。' })
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (source: string) => {
    setSaving(true)
    setFeedback(null)
    try {
      await deleteGlossaryEntry(source)
      await loadGlossary()
      if (editingOriginalSource === source) resetEditing()
      setFeedback({ kind: 'success', message: `术语“${source}”已删除。` })
    } catch (error) {
      setFeedback({ kind: 'error', message: error instanceof Error ? error.message : '删除术语失败。' })
    } finally {
      setSaving(false)
    }
  }

  const handleToggleConversion = async (item: GlossaryConversionRecord) => {
    if (!sessionId) return
    setSaving(true)
    setFeedback(null)
    try {
      await toggleGlossaryConversion(sessionId, item.id)
      await loadConversions(sessionId)
      setFeedback({ kind: 'success', message: item.active ? '已取消术语转换。' : '已重新应用术语转换。' })
    } catch (error) {
      setFeedback({ kind: 'error', message: error instanceof Error ? error.message : '切换术语转换失败。' })
    } finally {
      setSaving(false)
    }
  }

  const handleDeleteConversion = async (item: GlossaryConversionRecord) => {
    if (!sessionId) return
    setSaving(true)
    setFeedback(null)
    try {
      await deleteGlossaryConversion(sessionId, item.id)
      await loadConversions(sessionId)
      setFeedback({ kind: 'success', message: '术语转换记录已删除。' })
    } catch (error) {
      setFeedback({ kind: 'error', message: error instanceof Error ? error.message : '删除术语转换记录失败。' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <main className="page-shell">
      <section className="page-hero">
        <span className="badge">Glossary</span>
        <h2>术语库管理</h2>
        <p>维护翻译一致性，查看每次术语转换记录，并支持取消、恢复和删除。</p>
      </section>

      <section className="panel">
        <h3>添加术语</h3>
        <div className="glossary-form">
          <input placeholder="原文术语" value={newSource} onChange={(event) => setNewSource(event.target.value)} />
          <input placeholder="目标译法" value={newTarget} onChange={(event) => setNewTarget(event.target.value)} />
          <input placeholder="备注" value={newNote} onChange={(event) => setNewNote(event.target.value)} />
          <button className="primary-button" disabled={saving || !newSource.trim() || !newTarget.trim()} onClick={() => void handleAdd()}>添加</button>
        </div>
      </section>

      {feedback ? <p className={`settings-feedback ${feedback.kind}`}>{feedback.message}</p> : null}

      <section className="panel-grid two-cols">
        <article className="panel">
          <div className="panel-header">
            <h3>术语列表 <small>共 {glossary.length} 条</small></h3>
            <small>每页 4 条</small>
          </div>
          <div className="glossary-list">
            {loading ? (
              <div className="empty-state compact"><p>正在读取术语库...</p></div>
            ) : glossary.length === 0 ? (
              <div className="empty-state compact"><p>暂无术语，添加后会自动用于后续翻译与纠错。</p></div>
            ) : visibleGlossary.map((item) => (
              <div className="glossary-item" key={item.source}>
                {editingOriginalSource === item.source ? (
                  <div className="glossary-form glossary-inline-edit">
                    <input value={editingSource} onChange={(event) => setEditingSource(event.target.value)} />
                    <input value={editingTarget} onChange={(event) => setEditingTarget(event.target.value)} />
                    <input value={editingNote} onChange={(event) => setEditingNote(event.target.value)} />
                    <button className="primary-button" disabled={saving || !editingSource.trim() || !editingTarget.trim()} onClick={() => void handleUpdate()}>保存</button>
                    <button className="secondary-button" disabled={saving} onClick={resetEditing}>取消</button>
                  </div>
                ) : (
                  <>
                    <div className="glossary-text">
                      <strong>{item.source}</strong>
                      <span>→ {item.target}</span>
                      {item.note ? <small>{item.note}</small> : null}
                    </div>
                    <div className="glossary-actions">
                      <button className="secondary-button" disabled={saving} onClick={() => handleStartEdit(item)}>修改</button>
                      <button className="danger-button" disabled={saving} onClick={() => void handleDelete(item.source)}>删除</button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
          {glossary.length > GLOSSARY_PAGE_SIZE ? (
            <div className="correction-pagination" aria-label="术语列表分页">
              <button className="secondary-button" disabled={currentGlossaryPage <= 1} onClick={() => setGlossaryPage((value) => Math.max(1, value - 1))}>上一页</button>
              <span>第 {currentGlossaryPage} / {glossaryTotalPages} 页</span>
              <button className="secondary-button" disabled={currentGlossaryPage >= glossaryTotalPages} onClick={() => setGlossaryPage((value) => Math.min(glossaryTotalPages, value + 1))}>下一页</button>
            </div>
          ) : null}
        </article>

        <article className="panel">
          <div className="panel-header">
            <h3>术语转换记录</h3>
            <small>{conversions.length} 条</small>
          </div>
          <div className="glossary-form">
            <select value={sessionId} onChange={(event) => setSessionId(event.target.value)} disabled={!sessions.length || saving}>
              {sessions.map((session) => (
                <option key={session.session_id} value={session.session_id}>
                  {session.name || session.session_id}
                </option>
              ))}
            </select>
          </div>
          <div className="message-list">
            {!sessionId ? <p className="subtle">暂无可查看的历史会话。</p> : null}
            {sessionId && !visibleConversions.length ? <p className="subtle">该会话暂无术语转换记录。</p> : null}
            {visibleConversions.map((item) => (
              <div className="subtitle-item" key={item.id}>
                <p className="source">{item.glossary_source} → {item.glossary_target}</p>
                <div className="correction-translation-block">
                  <small>{item.active ? '当前已应用' : '当前已取消'}</small>
                  <p>{item.converted_text}</p>
                </div>
                <small className="subtitle-correction-note">
                  {item.updated_at ? new Date(item.updated_at).toLocaleString() : '无更新时间'}
                </small>
                <div className="glossary-actions">
                  <button className="secondary-button" disabled={saving} onClick={() => void handleToggleConversion(item)}>
                    {item.active ? '取消转换' : '重新转换'}
                  </button>
                  <button className="danger-button" disabled={saving} onClick={() => void handleDeleteConversion(item)}>删除记录</button>
                </div>
              </div>
            ))}
          </div>
          {conversions.length > CONVERSION_PAGE_SIZE ? (
            <div className="correction-pagination" aria-label="术语转换记录分页">
              <button className="secondary-button" disabled={currentConversionPage <= 1} onClick={() => setConversionPage((value) => Math.max(1, value - 1))}>上一页</button>
              <span>第 {currentConversionPage} / {conversionTotalPages} 页</span>
              <button className="secondary-button" disabled={currentConversionPage >= conversionTotalPages} onClick={() => setConversionPage((value) => Math.min(conversionTotalPages, value + 1))}>下一页</button>
            </div>
          ) : null}
        </article>
      </section>
    </main>
  )
}
