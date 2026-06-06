import { useEffect, useState } from 'react'

import { addGlossaryEntry, deleteGlossaryEntry, fetchGlossary, updateGlossaryEntry, type GlossaryEntry } from '../services/api'

export function GlossaryPage() {
  const [glossary, setGlossary] = useState<GlossaryEntry[]>([])
  const [newSource, setNewSource] = useState('')
  const [newTarget, setNewTarget] = useState('')
  const [newNote, setNewNote] = useState('')
  const [editingSource, setEditingSource] = useState('')
  const [editingTarget, setEditingTarget] = useState('')
  const [editingNote, setEditingNote] = useState('')

  const loadGlossary = async () => {
    const items = await fetchGlossary()
    setGlossary(items)
  }

  useEffect(() => {
    void loadGlossary()
  }, [])

  const handleAdd = async () => {
    if (!newSource.trim() || !newTarget.trim()) return
    const created = await addGlossaryEntry({ source: newSource.trim(), target: newTarget.trim(), note: newNote.trim() })
    setGlossary((prev) => [created, ...prev])
    setNewSource('')
    setNewTarget('')
    setNewNote('')
  }

  const handleUpdate = async () => {
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

  const handleDelete = async (source: string) => {
    await deleteGlossaryEntry(source)
    await loadGlossary()
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
            <button className="primary-button" onClick={handleAdd}>添加</button>
          </div>
        </article>

        <article className="panel">
          <h3>编辑术语</h3>
          <div className="glossary-form">
            <input placeholder="编辑原文术语" value={editingSource} onChange={(e) => setEditingSource(e.target.value)} />
            <input placeholder="编辑目标译法" value={editingTarget} onChange={(e) => setEditingTarget(e.target.value)} />
            <input placeholder="编辑备注" value={editingNote} onChange={(e) => setEditingNote(e.target.value)} />
            <button className="secondary-button" onClick={handleUpdate}>保存修改</button>
          </div>
        </article>
      </section>

      <section className="panel">
        <h3>术语列表</h3>
        <div className="glossary-list">
          {glossary.length === 0 ? (
            <div className="empty-state compact"><p>暂无术语。</p></div>
          ) : glossary.map((item) => (
            <div className="glossary-item" key={item.source}>
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
                <button className="danger-button" onClick={() => void handleDelete(item.source)}>删除</button>
              </div>
            </div>
          ))}
        </div>
      </section>
    </main>
  )
}
