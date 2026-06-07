export type StreamSessionState = {
  session_id: string
  source_language: string
  target_language: string
  is_active: boolean
}

export type StreamTextChunk = {
  chunk_id: string
  session_id: string
  source_text: string
  translated_text: string
  direct_translation: string
  is_final: boolean
  start_ms?: number | null
  end_ms?: number | null
  revision: number
  auto_correction?: boolean
  correction_reasons?: string[]
}

export type GlossaryEntry = {
  source: string
  target: string
  note?: string
}

export type TranscriptSessionSummary = {
  session_id: string
  name: string
  chunk_count: number
  correction_count: number
  created_at: string
  latest_updated_at: string
}

export type AppSettings = {
  asr_provider: string
  translation_provider: string
  tts_provider: string
  qwen_asr_model: string
  qwen_asr_language: string
  target_language: string
  dashscope_region: string
  dashscope_api_key_configured?: boolean
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

async function parseApiResponse<T>(response: Response, fallbackMessage: string): Promise<T> {
  if (response.ok) return response.json() as Promise<T>

  let message = fallbackMessage
  try {
    const payload = await response.json() as { detail?: string | Array<{ msg?: string }> }
    if (typeof payload.detail === 'string') {
      message = payload.detail
    } else if (Array.isArray(payload.detail)) {
      message = payload.detail.map((item) => item.msg).filter(Boolean).join('；') || message
    }
  } catch {
    // Keep the user-facing fallback when the server did not return JSON.
  }
  throw new Error(message)
}

export async function fetchHealth() {
  const response = await fetch(`${API_BASE}/health`)
  return response.json() as Promise<{ status: string }>
}

export async function fetchGlossary() {
  const response = await fetch(`${API_BASE}/glossary`)
  return parseApiResponse<GlossaryEntry[]>(response, '读取术语库失败')
}

export async function addGlossaryEntry(entry: GlossaryEntry) {
  const response = await fetch(`${API_BASE}/glossary`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(entry),
  })
  return parseApiResponse<GlossaryEntry>(response, '添加术语失败')
}

export async function updateGlossaryEntry(source: string, entry: GlossaryEntry) {
  const response = await fetch(`${API_BASE}/glossary/${encodeURIComponent(source)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(entry),
  })
  return parseApiResponse<GlossaryEntry>(response, '更新术语失败')
}

export async function deleteGlossaryEntry(source: string) {
  const response = await fetch(`${API_BASE}/glossary/${encodeURIComponent(source)}`, {
    method: 'DELETE',
  })
  return parseApiResponse<{ ok: boolean }>(response, '删除术语失败')
}

export async function fetchSettings() {
  const response = await fetch(`${API_BASE}/settings`)
  if (!response.ok) throw new Error(`Failed to fetch settings: ${response.status}`)
  return response.json() as Promise<Partial<AppSettings>>
}

export async function updateSettings(payload: AppSettings) {
  const response = await fetch(`${API_BASE}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) throw new Error(`Failed to update settings: ${response.status}`)
  return response.json() as Promise<AppSettings>
}

export async function testQwenConnection() {
  const response = await fetch(`${API_BASE}/settings/test-qwen`, { method: 'POST' })
  return response.json() as Promise<{ ok: boolean; message: string }>
}

export async function fetchLatestChunk(sessionId?: string) {
  const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ''
  const response = await fetch(`${API_BASE}/transcripts/latest${query}`)
  return response.json() as Promise<any>
}

export async function fetchTranscriptSessions() {
  const response = await fetch(`${API_BASE}/transcripts/sessions`)
  if (!response.ok) throw new Error(`Failed to fetch transcript sessions: ${response.status}`)
  return response.json() as Promise<TranscriptSessionSummary[]>
}

export async function createTranscriptSession(name: string) {
  const response = await fetch(`${API_BASE}/transcripts/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
  if (!response.ok) throw new Error(`Failed to create session: ${response.status}`)
  return response.json() as Promise<TranscriptSessionSummary>
}

export async function renameTranscriptSession(sessionId: string, name: string) {
  const response = await fetch(`${API_BASE}/transcripts/sessions/${encodeURIComponent(sessionId)}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
  if (!response.ok) throw new Error(`Failed to rename session: ${response.status}`)
  return response.json() as Promise<TranscriptSessionSummary>
}

export async function fetchSessionChunks(sessionId: string) {
  const response = await fetch(`${API_BASE}/transcripts/sessions/${encodeURIComponent(sessionId)}/chunks?final_only=true`)
  if (!response.ok) throw new Error(`Failed to fetch session chunks: ${response.status}`)
  return response.json() as Promise<StreamTextChunk[]>
}

export async function fetchSessionRevisions(sessionId: string, chunkId?: string) {
  const query = chunkId ? `?chunk_id=${encodeURIComponent(chunkId)}` : ''
  const response = await fetch(
    `${API_BASE}/transcripts/sessions/${encodeURIComponent(sessionId)}/revisions${query}`,
  )
  if (!response.ok) throw new Error(`Failed to fetch revisions: ${response.status}`)
  return response.json() as Promise<StreamTextChunk[]>
}

export async function rollbackTranscriptChunk(
  sessionId: string,
  chunkId: string,
  revision: number,
) {
  const response = await fetch(
    `${API_BASE}/transcripts/sessions/${encodeURIComponent(sessionId)}/chunks/${encodeURIComponent(chunkId)}/rollback`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ revision }),
    },
  )
  if (!response.ok) throw new Error(`Failed to rollback revision: ${response.status}`)
  return response.json() as Promise<StreamTextChunk>
}

export async function restoreDirectTranslation(sessionId: string, chunkId: string) {
  const response = await fetch(
    `${API_BASE}/transcripts/sessions/${encodeURIComponent(sessionId)}/chunks/${encodeURIComponent(chunkId)}/restore-direct`,
    { method: 'POST' },
  )
  if (!response.ok) throw new Error(`Failed to restore direct translation: ${response.status}`)
  return response.json() as Promise<StreamTextChunk>
}

export function getSessionExportUrl(sessionId: string, format: 'json' | 'txt' | 'srt') {
  return `${API_BASE}/transcripts/sessions/${encodeURIComponent(sessionId)}/export?format=${format}`
}
