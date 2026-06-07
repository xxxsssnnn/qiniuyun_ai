import { useEffect, useState } from 'react'

import { addGlossaryEntry, deleteGlossaryEntry, fetchGlossary, updateGlossaryEntry, type GlossaryEntry } from '../services/api'

type Feedback = { kind: 'success' | 'error'; message: string } | null

export function GlossaryPage() {
  const [glossary, setGlossary] = useState<GlossaryEntry[]>([])
  const [newSource, setNewSource] = useState('')
  const [newTarget, setNewTarget] = useState('')
  const [newNote, setNewNote] = useState('')
  const [editingSource, setEditingSource] = useState('')
  const [editingOriginalSource, setEditingOriginalSource] = useState('')
  const [editingTarget, setEditingTarget] = useState('')
  const [editingNote, setEditingNote] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [feedback, setFeedback] = useState<Feedback>(null)

  const loadGlossary = async () => {
    setLoading(true)
    try {
      const items = await fetchGlossary()
      setGlossary(items)
    } catch (error) {
      setFeedback({
        kind: 'error',
        message: error instanceof Error ? error.message : '读取术语库失败，请确认后端已启动。',
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadGlossary()
  }, [])

  const handleAdd = async () => {
    if (!newSource.trim() || !newTarget.trim()) return
    setSaving(true)
    setFeedback(null)
    try {
      const created = await addGlossaryEntry({ source: newSource.trim(), target: newTarget.trim(), note: newNote.trim() })
      setGlossary((prev) => [
        created,
        ...prev.filter((item) => item.source !== created.source),
      ].sort((left, right) => left.source.localeCompare(right.source)))
      setNewSource('')
      setNewTarget('')
      setNewNote('')
      setFeedback({ kind: 'success', message: `术语“${created.source}”已保存，将用于后续实时翻译和字幕纠错。` })
    } catch (error) {
      setFeedback({ kind: 'error', message: error instanceof Error ? error.message : '添加术语失败。' })
    } finally {
      setSaving(false)
    }
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
      setGlossary((prev) => prev
        .map((item) => (item.source === editingOriginalSource ? updated : item))
        .sort((left, right) => left.source.localeCompare(right.source)))
      setEditingOriginalSource('')
      setEditingSource('')
      setEditingTarget('')
      setEditingNote('')
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
      setGlossary((prev) => prev.filter((item) => item.source !== source))
      if (editingOriginalSource === source) {
        setEditingOriginalSource('')
        setEditingSource('')
        setEditingTarget('')
        setEditingNote('')
      }
      setFeedback({ kind: 'success', message: `术语“${source}”已删除。` })
    } catch (error) {
      setFeedback({ kind: 'error', message: error instanceof Error ? error.message : '删除术语失败。' })
    } finally {
      setSaving(false)
    }
  }

  return (
    <main className="page-shell">
      <section className="page-hero">
        <span className="badge">Glossary</span>
        <h2>术语库管理</h2>
        <p>维护翻译一致性，支持术语添加、编辑、删除与备注。</p>
      </section>

      <section className="panel-grid two-cols">
        <article className="panel">
          <h3>添加术语</h3>
          <div className="glossary-form">
            <input placeholder="原文术语" value={newSource} onChange={(e) => setNewSource(e.target.value)} />
            <input placeholder="目标译法" value={newTarget} onChange={(e) => setNewTarget(e.target.value)} />
            <input placeholder="备注" value={newNote} onChange={(e) => setNewNote(e.target.value)} />
            <button className="primary-button" disabled={saving || !newSource.trim() || !newTarget.trim()} onClick={() => void handleAdd()}>添加</button>
          </div>
        </article>

        <article className="panel">
          <h3>编辑术语</h3>
          <div className="glossary-form">
            <input placeholder="编辑原文术语" value={editingSource} onChange={(e) => setEditingSource(e.target.value)} />
            <input placeholder="编辑目标译法" value={editingTarget} onChange={(e) => setEditingTarget(e.target.value)} />
            <input placeholder="编辑备注" value={editingNote} onChange={(e) => setEditingNote(e.target.value)} />
            <button className="secondary-button" disabled={saving || !editingOriginalSource || !editingSource.trim() || !editingTarget.trim()} onClick={() => void handleUpdate()}>保存修改</button>
          </div>
        </article>
      </section>

      {feedback ? <p className={`settings-feedback ${feedback.kind}`}>{feedback.message}</p> : null}

      <section className="panel">
        <h3>术语列表 <small>共 {glossary.length} 条</small></h3>
        <div className="glossary-list">
          {loading ? (
            <div className="empty-state compact"><p>正在读取术语库...</p></div>
          ) : glossary.length === 0 ? (
            <div className="empty-state compact"><p>暂无术语，添加后会自动用于后续翻译与纠错。</p></div>
          ) : glossary.map((item) => (
            <div className="glossary-item" key={item.source}>
              <div className="glossary-text">
                <strong>{item.source}</strong>
                <span>→ {item.target}</span>
                {item.note ? <small>{item.note}</small> : null}
              </div>
              <div className="glossary-actions">
                <button className="secondary-button" onClick={() => {
                  setEditingOriginalSource(item.source)
                  setEditingSource(item.source)
                  setEditingTarget(item.target)
                  setEditingNote(item.note ?? '')
                }}>编辑</button>
                <button className="danger-button" disabled={saving} onClick={() => void handleDelete(item.source)}>删除</button>
              </div>
            </div>
          ))}
        </div>
      </section>
    </main>
  )
}
