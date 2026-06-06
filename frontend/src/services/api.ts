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
