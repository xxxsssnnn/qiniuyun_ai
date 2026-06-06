import { useMemo, useState } from 'react'

import { fetchLatestChunk } from '../services/api'

const sampleHistory = [
  { id: 'chunk-01', revision: 0, status: 'draft', source: 'Today we discuss architecture.', target: '今天我们讨论架构。' },
  { id: 'chunk-01', revision: 1, status: 'final', source: 'Today we discuss real-time architecture.', target: '今天我们讨论实时架构。' },
  { id: 'chunk-02', revision: 0, status: 'draft', source: 'The model uses streaming inference.', target: '这个模型使用流式推理。' },
] as const

export function CorrectionsPage() {
  const [selectedChunk, setSelectedChunk] = useState('chunk-01')
  const current = useMemo(() => sampleHistory.filter((item) => item.id === selectedChunk), [selectedChunk])

  const handleRollback = async () => {
    // 占位：后续可直接发送 rollback 消息到 websocket
    await fetchLatestChunk()
  }

  return (
    <main className="page-shell">
      <section className="page-hero">
        <span className="badge">Corrections</span>
        <h2>字幕修正与历史</h2>
        <p>集中查看字幕版本、回滚入口和修正记录。</p>
      </section>

      <section className="panel-grid two-cols">
        <article className="panel">
          <h3>历史记录</h3>
          <div className="glossary-form">
            <select value={selectedChunk} onChange={(e) => setSelectedChunk(e.target.value)}>
              <option value="chunk-01">chunk-01</option>
              <option value="chunk-02">chunk-02</option>
            </select>
            <button className="secondary-button" onClick={() => void handleRollback()}>回滚当前条目</button>
          </div>
          <div className="message-list">
            {current.map((item) => (
              <div key={`${item.id}-${item.revision}`} className="subtitle-item">
                <div className="subtitle-topline"><span>{item.status.toUpperCase()}</span><small>revision {item.revision}</small></div>
                <p className="source">{item.source}</p>
                <p className="translation">{item.target}</p>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <h3>修正说明</h3>
          <ul className="feature-list">
            <li>后续可从 Live 页触发 rollback 后，在这里看到变化。</li>
            <li>未来可以加入差异高亮、人工确认和批量修正。</li>
            <li>也可以用于回看 ASR 与翻译版本演变。</li>
          </ul>
        </article>
      </section>
    </main>
  )
}
