export type RealtimeMessage = {
  type: 'connected' | 'chunk' | 'translated' | 'revision' | 'correction' | 'status' | 'error' | 'audio'
  session_id: string
  payload?: unknown
}

const DEFAULT_WS_URLS = [
  'ws://localhost:8000/api/v1/transcripts/ws',
  'ws://localhost:8000/api/transcripts/ws',
  'ws://localhost:8000/api/v1/v1/transcripts/ws',
]

export function getRealtimeSocketUrls(sessionId: string) {
  const configuredUrl = import.meta.env.VITE_WS_BASE_URL
  const baseUrls = configuredUrl ? [configuredUrl] : DEFAULT_WS_URLS
  return baseUrls.map((baseUrl) => `${baseUrl.replace(/\/$/, '')}/${sessionId}`)
}

export function createRealtimeSocket(sessionId: string) {
  return new WebSocket(getRealtimeSocketUrls(sessionId)[0])
}

export function createRealtimeSocketWithFallback(
  sessionId: string,
  handlers: {
    onOpen?: (socket: WebSocket) => void
    onMessage?: (event: MessageEvent) => void
    onClose?: (event: CloseEvent) => void
    onError?: (event: Event) => void
    onFallback?: (url: string) => void
  } = {},
) {
  const urls = getRealtimeSocketUrls(sessionId)
  let index = 0
  let opened = false
  let socket: WebSocket

  const connect = () => {
    socket = new WebSocket(urls[index])
    socket.onopen = () => {
      opened = true
      handlers.onOpen?.(socket)
    }
    socket.onmessage = (event) => handlers.onMessage?.(event)
    socket.onerror = (event) => handlers.onError?.(event)
    socket.onclose = (event) => {
      if (!opened && index < urls.length - 1) {
        index += 1
        handlers.onFallback?.(urls[index])
        connect()
        return
      }
      handlers.onClose?.(event)
    }
  }

  connect()

  return {
    get current() {
      return socket
    },
    send(data: string | Blob | ArrayBufferLike | ArrayBufferView) {
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(data)
      }
    },
    close() {
      socket.close()
    },
  }
}

export function closeRealtimeSocket(socket: WebSocket) {
  if (socket.readyState === WebSocket.OPEN) {
    socket.close()
    return
  }

  if (socket.readyState === WebSocket.CONNECTING) {
    socket.addEventListener('open', () => socket.close(), { once: true })
  }
}
