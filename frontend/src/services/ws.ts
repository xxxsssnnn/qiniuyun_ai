export type RealtimeMessage = {
  type: 'connected' | 'chunk' | 'translated' | 'revision' | 'status' | 'error' | 'audio'
  session_id: string
  payload?: unknown
}

export function createRealtimeSocket(sessionId: string) {
  const baseUrl = import.meta.env.VITE_WS_BASE_URL ?? 'ws://localhost:8000/api/v1/transcripts/ws'
  return new WebSocket(`${baseUrl}/${sessionId}`)
}
