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
  is_final: boolean
  start_ms?: number | null
  end_ms?: number | null
  revision: number
}

export type GlossaryEntry = {
  source: string
  target: string
  note?: string
}

export type AppSettings = {
  asr_provider: string
  translation_provider: string
  tts_provider: string
  qwen_asr_model: string
  qwen_asr_language: string
  dashscope_region: string
  dashscope_api_key_configured?: boolean
}

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export async function fetchHealth() {
  const response = await fetch(`${API_BASE}/health`)
  return response.json() as Promise<{ status: string }>
}

export async function fetchGlossary() {
  const response = await fetch(`${API_BASE}/glossary`)
  return response.json() as Promise<GlossaryEntry[]>
}

export async function addGlossaryEntry(entry: GlossaryEntry) {
  const response = await fetch(`${API_BASE}/glossary`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(entry),
  })
  return response.json() as Promise<GlossaryEntry>
}

export async function updateGlossaryEntry(source: string, entry: GlossaryEntry) {
  const response = await fetch(`${API_BASE}/glossary/${encodeURIComponent(source)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(entry),
  })
  return response.json() as Promise<GlossaryEntry>
}

export async function deleteGlossaryEntry(source: string) {
  const response = await fetch(`${API_BASE}/glossary/${encodeURIComponent(source)}`, {
    method: 'DELETE',
  })
  return response.json() as Promise<{ ok: boolean }>
}

export async function fetchSettings() {
  const response = await fetch(`${API_BASE}/settings`)
  return response.json() as Promise<Partial<AppSettings>>
}

export async function updateSettings(payload: AppSettings) {
  const response = await fetch(`${API_BASE}/settings`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  return response.json() as Promise<AppSettings>
}

export async function testQwenConnection() {
  const response = await fetch(`${API_BASE}/settings/test-qwen`, { method: 'POST' })
  return response.json() as Promise<{ ok: boolean; message: string }>
}

export async function fetchLatestChunk() {
  const response = await fetch(`${API_BASE}/transcripts/latest`)
  return response.json() as Promise<any>
}
