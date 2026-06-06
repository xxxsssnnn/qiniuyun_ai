import { useEffect, useMemo, useState } from 'react'

import { fetchHealth, fetchSettings, updateSettings } from '../services/api'

type ProviderChoice = 'mock' | 'whisper' | 'openai'
type ProviderKind = 'asr' | 'translation' | 'tts'

type ProviderMeta = {
  kind: ProviderKind
  title: string
  description: string
  helpText: Record<ProviderChoice, string>
}

type SettingsForm = {
  asrProvider: ProviderChoice
  translationProvider: ProviderChoice
  ttsProvider: ProviderChoice
  openaiApiKey: string
  openaiBaseUrl: string
  openaiModel: string
  openaiTranslationModel: string
  openaiTtsModel: string
  openaiTtsVoice: string
  whisperModel: string
  whisperDevice: string
  whisperComputeType: string
}

const providerOptions: { value: ProviderChoice; label: string }[] = [
  { value: 'mock', label: '演示模式' },
  { value: 'whisper', label: '本地语音识别' },
  { value: 'openai', label: 'AI 服务模式' },
]

const providerLabels: Record<ProviderChoice, string> = {
  mock: '演示模式',
  whisper: '本地语音识别',
  openai: 'AI 服务模式',
}

const providerMeta: ProviderMeta[] = [
  {
    kind: 'asr',
    title: '语音识别',
    description: '把音频转换成文本，是整条链路的入口。',
    helpText: {
      mock: '适合先看流程，不需要额外配置。',
      whisper: '适合本地运行识别模型。',
      openai: '适合接入在线识别服务。',
    },
  },
  {
    kind: 'translation',
    title: '自动翻译',
    description: '把识别结果转换成中文翻译。',
    helpText: {
      mock: '使用示例数据，适合调试界面。',
      whisper: '适合接入你自己的本地翻译逻辑。',
      openai: '适合接入真实翻译接口。',
    },
  },
  {
    kind: 'tts',
    title: '语音播报',
    description: '把翻译结果读出来，形成完整体验。',
    helpText: {
      mock: '只做演示，不消耗额外资源。',
      whisper: '适合本地语音合成方案。',
      openai: '适合使用在线语音合成服务。',
    },
  },
]

function ProviderCard({
  title,
  description,
  value,
  helpText,
  onChange,
  locked,
}: {
  title: string
  description: string
  value: ProviderChoice
  helpText: Record<ProviderChoice, string>
  onChange: (value: ProviderChoice) => void
  locked?: boolean
}) {
  return (
    <section className="setting-card">
      <div className="setting-card-header">
        <div>
          <h4>{title}</h4>
          <p>{description}</p>
        </div>
        <span className="setting-pill">当前：{providerLabels[value]}</span>
      </div>

      <label className="setting-field">
        <span className="setting-field-label">模式选择</span>
        <select
          value={value}
          onChange={(e) => onChange(e.target.value as ProviderChoice)}
          disabled={locked}
        >
          {providerOptions.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>

      <p className="setting-hint">{helpText[value]}</p>
      {value === 'openai' ? (
        <div className="setting-warning-box">
          <strong>需要额外配置</strong>
          <p>切换到 AI 服务模式后，请先填写 API Key 和相关模型参数，否则保存后无法真正调用。</p>
        </div>
      ) : null}
    </section>
  )
}

export function SettingsPage() {
  const [health, setHealth] = useState('loading')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [asrProvider, setAsrProvider] = useState<ProviderChoice>('mock')
  const [translationProvider, setTranslationProvider] = useState<ProviderChoice>('mock')
  const [ttsProvider, setTtsProvider] = useState<ProviderChoice>('mock')
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState<SettingsForm>({
    asrProvider: 'mock',
    translationProvider: 'mock',
    ttsProvider: 'mock',
    openaiApiKey: '',
    openaiBaseUrl: 'https://api.openai.com/v1',
    openaiModel: 'gpt-4o-mini',
    openaiTranslationModel: 'gpt-4o-mini',
    openaiTtsModel: 'gpt-4o-mini-tts',
    openaiTtsVoice: 'alloy',
    whisperModel: 'base',
    whisperDevice: 'cpu',
    whisperComputeType: 'int8',
  })

  const summary = useMemo(
    () => [asrProvider, translationProvider, ttsProvider].map((item) => providerLabels[item]).join(' · '),
    [asrProvider, translationProvider, ttsProvider],
  )

  useEffect(() => {
    let active = true

    const load = async () => {
      try {
        const [healthRes, settings] = await Promise.all([fetchHealth(), fetchSettings()])
        if (!active) return
        setHealth(healthRes.status)
        const nextForm: SettingsForm = {
          asrProvider: (settings.asr_provider as ProviderChoice) ?? 'mock',
          translationProvider: (settings.translation_provider as ProviderChoice) ?? 'mock',
          ttsProvider: (settings.tts_provider as ProviderChoice) ?? 'mock',
          openaiApiKey: settings.openai_api_key ?? '',
          openaiBaseUrl: settings.openai_base_url ?? 'https://api.openai.com/v1',
          openaiModel: settings.openai_model ?? 'gpt-4o-mini',
          openaiTranslationModel: settings.openai_translation_model ?? 'gpt-4o-mini',
          openaiTtsModel: settings.openai_tts_model ?? 'gpt-4o-mini-tts',
          openaiTtsVoice: settings.openai_tts_voice ?? 'alloy',
          whisperModel: settings.whisper_model ?? 'base',
          whisperDevice: settings.whisper_device ?? 'cpu',
          whisperComputeType: settings.whisper_compute_type ?? 'int8',
        }
        setForm(nextForm)
        setAsrProvider(nextForm.asrProvider)
        setTranslationProvider(nextForm.translationProvider)
        setTtsProvider(nextForm.ttsProvider)
      } catch {
        if (!active) return
        setHealth('offline')
        setError('暂时无法读取后端设置，请确认服务已启动。')
      } finally {
        if (active) setLoading(false)
      }
    }

    void load()

    return () => {
      active = false
    }
  }, [])

  const handleSave = async () => {
    setSaving(true)
    setError('')
    try {
      await updateSettings({
        asr_provider: asrProvider,
        translation_provider: translationProvider,
        tts_provider: ttsProvider,
        openai_api_key: form.openaiApiKey,
        openai_base_url: form.openaiBaseUrl,
        openai_model: form.openaiModel,
        openai_translation_model: form.openaiTranslationModel,
        openai_tts_model: form.openaiTtsModel,
        openai_tts_voice: form.openaiTtsVoice,
        whisper_model: form.whisperModel,
        whisper_device: form.whisperDevice,
        whisper_compute_type: form.whisperComputeType,
      })
      setSaved(true)
      window.setTimeout(() => setSaved(false), 1800)
    } catch {
      setError('保存失败，请检查后端是否正常运行。')
    } finally {
      setSaving(false)
    }
  }

  return (
    <main className="page-shell settings-page">
      <section className="page-hero settings-hero">
        <div className="settings-hero-copy">
          <span className="badge">Settings</span>
          <h2>系统设置</h2>
          <p>把语音识别、翻译和播报分开配置，页面会更清晰，也更容易排查问题。</p>
        </div>

        <div className="settings-status-grid">
          <article className="status-card">
            <span className="panel-badge">后端状态</span>
            <strong>{health}</strong>
            <p>当前服务监听 `http://localhost:8000`。</p>
          </article>
          <article className="status-card">
            <span className="panel-badge">加载状态</span>
            <strong>{loading ? '读取中' : '已就绪'}</strong>
            <p>进入页面时会自动拉取后端配置。</p>
          </article>
        </div>
      </section>

      <section className="panel-grid two-cols settings-overview-grid">
        <article className="panel">
          <h3>当前方案</h3>
          <p className="muted">{summary}</p>
          <div className="setting-summary-box">
            <strong>建议</strong>
            <p>如果你只是先体验，三项都保持“演示模式”最省事。</p>
          </div>
        </article>

        <article className="panel">
          <h3>操作提示</h3>
          <ul className="feature-list compact-list">
            <li>优先确认后端健康状态是正常的。</li>
            <li>有真实服务时，再逐项切换成对应模式。</li>
            <li>保存后会立即写入后端配置。</li>
          </ul>
        </article>
      </section>

      <section className="panel">
        <div className="panel-header">
          <div>
            <h3>功能配置</h3>
            <p className="muted">每个功能单独设置，避免混在一起不好理解。</p>
          </div>
          <span className="setting-pill">3 个模块</span>
        </div>

        <div className="setting-grid settings-grid-clean">
          {providerMeta.map((item) => (
            <ProviderCard
              key={item.kind}
              title={item.title}
              description={item.description}
              value={
                item.kind === 'asr'
                  ? asrProvider
                  : item.kind === 'translation'
                    ? translationProvider
                    : ttsProvider
              }
              helpText={item.helpText}
              onChange={
                item.kind === 'asr'
                  ? setAsrProvider
                  : item.kind === 'translation'
                    ? setTranslationProvider
                    : setTtsProvider
              }
            />
          ))}
        </div>

        <div className="settings-form-grid">
          <label className="setting-field">
            <span className="setting-field-label">OpenAI API Key</span>
            <input
              value={form.openaiApiKey}
              placeholder="sk-..."
              onChange={(e) => setForm((prev) => ({ ...prev, openaiApiKey: e.target.value }))}
            />
          </label>
          <label className="setting-field">
            <span className="setting-field-label">OpenAI Base URL</span>
            <input
              value={form.openaiBaseUrl}
              onChange={(e) => setForm((prev) => ({ ...prev, openaiBaseUrl: e.target.value }))}
            />
          </label>
          <label className="setting-field">
            <span className="setting-field-label">模型</span>
            <input
              value={form.openaiModel}
              onChange={(e) => setForm((prev) => ({ ...prev, openaiModel: e.target.value }))}
            />
          </label>
          <label className="setting-field">
            <span className="setting-field-label">翻译模型</span>
            <input
              value={form.openaiTranslationModel}
              onChange={(e) => setForm((prev) => ({ ...prev, openaiTranslationModel: e.target.value }))}
            />
          </label>
          <label className="setting-field">
            <span className="setting-field-label">TTS 模型</span>
            <input
              value={form.openaiTtsModel}
              onChange={(e) => setForm((prev) => ({ ...prev, openaiTtsModel: e.target.value }))}
            />
          </label>
          <label className="setting-field">
            <span className="setting-field-label">TTS 音色</span>
            <input
              value={form.openaiTtsVoice}
              onChange={(e) => setForm((prev) => ({ ...prev, openaiTtsVoice: e.target.value }))}
            />
          </label>
          <label className="setting-field">
            <span className="setting-field-label">Whisper 模型</span>
            <input
              value={form.whisperModel}
              onChange={(e) => setForm((prev) => ({ ...prev, whisperModel: e.target.value }))}
            />
          </label>
          <label className="setting-field">
            <span className="setting-field-label">Whisper 设备</span>
            <input
              value={form.whisperDevice}
              onChange={(e) => setForm((prev) => ({ ...prev, whisperDevice: e.target.value }))}
            />
          </label>
          <label className="setting-field">
            <span className="setting-field-label">Whisper 精度</span>
            <input
              value={form.whisperComputeType}
              onChange={(e) => setForm((prev) => ({ ...prev, whisperComputeType: e.target.value }))}
            />
          </label>
        </div>

        <div className="setting-actions settings-actions-clean">
          <button className="primary-button" onClick={handleSave} disabled={saving}>
            {saving ? '保存中…' : '保存设置'}
          </button>
          {saved ? <span className="setting-saved">设置已保存</span> : null}
          {error ? <span className="setting-error">{error}</span> : null}
        </div>
      </section>
    </main>
  )
}
