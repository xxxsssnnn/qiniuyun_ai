import { useEffect, useState } from 'react'

import { fetchHealth, fetchSettings, updateSettings } from '../services/api'

type ProviderChoice = 'mock' | 'whisper' | 'openai'

export function SettingsPage() {
  const [health, setHealth] = useState('unknown')
  const [asrProvider, setAsrProvider] = useState<ProviderChoice>('mock')
  const [translationProvider, setTranslationProvider] = useState<ProviderChoice>('mock')
  const [ttsProvider, setTtsProvider] = useState<ProviderChoice>('mock')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    void fetchHealth().then((res) => setHealth(res.status)).catch(() => setHealth('offline'))
    void fetchSettings().then((settings) => {
      setAsrProvider((settings.asr_provider as ProviderChoice) ?? 'mock')
      setTranslationProvider((settings.translation_provider as ProviderChoice) ?? 'mock')
      setTtsProvider((settings.tts_provider as ProviderChoice) ?? 'mock')
    }).catch(() => undefined)
  }, [])

  const handleSave = async () => {
    await updateSettings({ asr_provider: asrProvider, translation_provider: translationProvider, tts_provider: ttsProvider })
    setSaved(true)
    window.setTimeout(() => setSaved(false), 1800)
  }

  return (
    <main className="page-shell">
      <section className="page-hero">
        <span className="badge">Settings</span>
        <h2>系统配置</h2>
        <p>配置识别、翻译、播报与服务状态，用于后续接入真实模型。</p>
      </section>

      <section className="panel-grid two-cols">
        <article className="panel">
          <h3>服务状态</h3>
          <p className="muted">后端健康状态：{health}</p>
          <p className="muted">后端地址：http://localhost:8000</p>
        </article>
        <article className="panel">
          <h3>Provider 选择</h3>
          <div className="glossary-form">
            <select value={asrProvider} onChange={(e) => setAsrProvider(e.target.value as ProviderChoice)}>
              <option value="mock">ASR Mock</option>
              <option value="whisper">ASR Whisper</option>
            </select>
            <select value={translationProvider} onChange={(e) => setTranslationProvider(e.target.value as ProviderChoice)}>
              <option value="mock">Translation Mock</option>
              <option value="openai">Translation OpenAI</option>
            </select>
            <select value={ttsProvider} onChange={(e) => setTtsProvider(e.target.value as ProviderChoice)}>
              <option value="mock">TTS Mock</option>
              <option value="openai">TTS OpenAI</option>
            </select>
            <button className="primary-button" onClick={handleSave}>保存配置</button>
          </div>
          {saved ? <p className="muted">配置已保存。</p> : null}
        </article>
      </section>

      <section className="panel">
        <h3>配置说明</h3>
        <ul className="feature-list">
          <li>这些选择现在会保存到后端配置表。</li>
          <li>后续可以把运行时 provider 改成读取这个配置。</li>
          <li>也可以按项目模式和演示模式做切换。</li>
        </ul>
      </section>
    </main>
  )
}
