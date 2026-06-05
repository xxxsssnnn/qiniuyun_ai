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

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export async function fetchHealth() {
  const response = await fetch(`${API_BASE}/health`)
  return response.json() as Promise<{ status: string }>
}
