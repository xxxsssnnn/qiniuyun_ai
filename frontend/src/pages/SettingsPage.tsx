import { useEffect, useState } from 'react'

import {
  fetchHealth,
  fetchSettings,
  testQwenConnection,
  updateSettings,
  type AppSettings,
} from '../services/api'

type ProviderChoice = 'mock' | 'whisper' | 'qwen' | 'openai'
type Feedback = { kind: 'success' | 'error'; message: string } | null

const defaultSettings: AppSettings = {
  asr_provider: 'mock',
  translation_provider: 'mock',
  tts_provider: 'mock',
  qwen_asr_model: 'qwen3.5-omni-plus-realtime',
  qwen_asr_language: 'en',
  target_language: 'zh',
  dashscope_region: 'cn',
  dashscope_api_key_configured: false,
}

export function SettingsPage() {
  const [health, setHealth] = useState('检查中')
  const [settings, setSettings] = useState<AppSettings>(defaultSettings)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [feedback, setFeedback] = useState<Feedback>(null)

  useEffect(() => {
    void fetchHealth().then((res) => setHealth(res.status)).catch(() => setHealth('offline'))
    void fetchSettings()
      .then((stored) => setSettings({ ...defaultSettings, ...stored }))
      .catch(() => setFeedback({ kind: 'error', message: '读取配置失败，请确认后端已启动。' }))
      .finally(() => setLoading(false))
  }, [])

  const setField = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    setSettings((current) => ({ ...current, [key]: value }))
    setFeedback(null)
  }

  const handleSave = async () => {
    setSaving(true)
    setFeedback(null)
    try {
      const saved = await updateSettings(settings)
      setSettings((current) => ({ ...current, ...saved }))
      setFeedback({ kind: 'success', message: '配置已保存，新建的实时会话会立即使用这套设置。' })
    } catch {
      setFeedback({ kind: 'error', message: '保存失败，请检查后端服务。' })
    } finally {
      setSaving(false)
    }
  }

  const handleTargetLanguageChange = async (targetLanguage: string) => {
    const nextSettings = { ...settings, target_language: targetLanguage }
    setSettings(nextSettings)
    setSaving(true)
    setFeedback(null)
    try {
      const saved = await updateSettings(nextSettings)
      setSettings((current) => ({ ...current, ...saved }))
      setFeedback({
        kind: 'success',
        message: '目标语言已保存。返回 Live 页面后，新会话会使用该语言。',
      })
    } catch {
      setFeedback({ kind: 'error', message: '目标语言保存失败，请检查后端服务。' })
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async () => {
    setTesting(true)
    setFeedback(null)
    try {
      await updateSettings(settings)
      const result = await testQwenConnection()
      setFeedback({ kind: result.ok ? 'success' : 'error', message: result.message })
    } catch {
      setFeedback({ kind: 'error', message: '连接测试失败，请检查网络与后端日志。' })
    } finally {
      setTesting(false)
    }
  }

  return (
    <main className="page-shell">
      <section className="page-hero">
        <span className="badge">Settings</span>
        <h2>模型与实时语音配置</h2>
        <p>选择识别、翻译和播报服务。千问 API Key 只从后端环境变量读取，不会发送到浏览器或写入数据库。</p>
      </section>

      <section className="settings-status-grid">
        <article className="panel settings-status-card">
          <span className={`settings-dot ${health === 'ok' ? 'online' : ''}`} />
          <div><small>后端服务</small><strong>{health}</strong></div>
        </article>
        <article className="panel settings-status-card">
          <span className={`settings-dot ${settings.dashscope_api_key_configured ? 'online' : ''}`} />
          <div><small>千问 API Key</small><strong>{settings.dashscope_api_key_configured ? '已配置' : '未检测到'}</strong></div>
        </article>
        <article className="panel settings-status-card">
          <span className={`settings-dot ${settings.asr_provider === 'qwen' ? 'online' : ''}`} />
          <div><small>当前语音识别</small><strong>{settings.asr_provider}</strong></div>
        </article>
      </section>

      <section className="panel settings-panel" aria-busy={loading}>
        <div className="panel-header">
          <div>
            <h3>Provider 配置</h3>
            <p>保存后，下一次开始麦克风采集时会按这里的配置创建模型连接。</p>
          </div>
          <span className="panel-badge">Runtime</span>
        </div>

        <div className="settings-form-grid">
          <label className="settings-field">
            <span>语音识别 ASR</span>
            <select value={settings.asr_provider} onChange={(event) => setField('asr_provider', event.target.value as ProviderChoice)} disabled={loading}>
              <option value="qwen">千问 Omni 实时翻译</option>
              <option value="whisper">本地 Whisper</option>
              <option value="mock">Mock 演示</option>
            </select>
            <small>直接完成语音识别和中文翻译。</small>
          </label>

          <label className="settings-field">
            <span>翻译</span>
            <select value={settings.translation_provider} onChange={(event) => setField('translation_provider', event.target.value as ProviderChoice)} disabled={loading || settings.asr_provider === 'qwen'}>
              <option value="mock">Mock 翻译</option>
              <option value="openai">OpenAI 兼容翻译</option>
            </select>
            <small>{settings.asr_provider === 'qwen' ? '千问 Omni 已直接输出译文，此项不会参与。' : '对 ASR 原文执行第二阶段翻译。'}</small>
          </label>

          <label className="settings-field">
            <span>语音播报 TTS</span>
            <select value={settings.tts_provider} onChange={(event) => setField('tts_provider', event.target.value as ProviderChoice)} disabled={loading}>
              <option value="mock">浏览器播报 / Mock</option>
              <option value="openai">OpenAI TTS</option>
            </select>
          </label>
        </div>
      </section>

      <section className="panel settings-panel">
        <div className="panel-header">
          <div>
            <h3>千问 Omni 实时语音翻译</h3>
            <p>音频以 PCM16、16 kHz、单声道发送；Omni 同时生成原文转写和所选目标语言译文。</p>
          </div>
          <span className="panel-badge">Qwen Omni</span>
        </div>

        <div className="settings-form-grid">
          <label className="settings-field">
            <span>模型</span>
            <input value={settings.qwen_asr_model} onChange={(event) => setField('qwen_asr_model', event.target.value)} placeholder="qwen3.5-omni-plus-realtime" />
          </label>

          <label className="settings-field">
            <span>源语言</span>
            <select value={settings.qwen_asr_language} onChange={(event) => setField('qwen_asr_language', event.target.value)}>
              <option value="en">英语</option>
              <option value="zh">中文</option>
              <option value="yue">粤语</option>
              <option value="ja">日语</option>
              <option value="ko">韩语</option>
              <option value="fr">法语</option>
              <option value="de">德语</option>
              <option value="es">西班牙语</option>
            </select>
          </label>

          <label className="settings-field">
            <span>目标语言</span>
            <select
              value={settings.target_language}
              onChange={(event) => void handleTargetLanguageChange(event.target.value)}
              disabled={saving}
            >
              <option value="zh">中文</option>
              <option value="en">英语</option>
              <option value="yue">粤语</option>
              <option value="ja">日语</option>
              <option value="ko">韩语</option>
              <option value="fr">法语</option>
              <option value="de">德语</option>
              <option value="es">西班牙语</option>
              <option value="ru">俄语</option>
              <option value="pt">葡萄牙语</option>
              <option value="it">意大利语</option>
              <option value="ar">阿拉伯语</option>
              <option value="th">泰语</option>
              <option value="vi">越南语</option>
            </select>
            <small>选择后自动保存；返回 Live 页面会创建使用该语言的新会话。</small>
          </label>

          <label className="settings-field">
            <span>服务地域</span>
            <select value={settings.dashscope_region} onChange={(event) => setField('dashscope_region', event.target.value)}>
              <option value="cn">中国内地（北京）</option>
              <option value="intl">国际（新加坡）</option>
            </select>
            <small>API Key 必须与所选地域一致。</small>
          </label>
        </div>

        <div className="settings-actions">
          <button className="primary-button" onClick={handleSave} disabled={loading || saving}>{saving ? '保存中...' : '保存配置'}</button>
          <button className="secondary-button" onClick={handleTest} disabled={loading || testing}>{testing ? '连接中...' : '测试千问连接'}</button>
        </div>

        {feedback ? <p className={`settings-feedback ${feedback.kind}`}>{feedback.message}</p> : null}
      </section>

      <section className="panel">
        <h3>环境变量</h3>
        <ul className="feature-list">
          <li><code>DASHSCOPE_API_KEY</code>：推荐名称；也兼容 <code>QWEN_API_KEY</code> 和 <code>ALIYUN_API_KEY</code>。</li>
          <li>切换地域时，请使用对应地域创建的 API Key。</li>
          <li>修改 provider 后请重新开始一次麦克风会话，已有会话不会中途更换模型。</li>
        </ul>
      </section>
    </main>
  )
}
