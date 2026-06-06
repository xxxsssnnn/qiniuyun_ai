export type SpeechPlaybackState = 'idle' | 'speaking' | 'error'

export function canUseSpeechSynthesis() {
  return typeof window !== 'undefined' && 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window
}

export function speakText(text: string, lang = 'zh-CN') {
  if (!canUseSpeechSynthesis()) return false
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = lang
  window.speechSynthesis.cancel()
  window.speechSynthesis.speak(utterance)
  return true
}
