export type AudioCaptureState = 'idle' | 'starting' | 'recording' | 'stopped' | 'error'

export async function getMicrophoneStream() {
  return navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
  })
}

export function createAudioRecorder(stream: MediaStream, onChunk: (chunk: Blob) => void) {
  const recorder = new MediaRecorder(stream, {
    mimeType: 'audio/webm;codecs=opus',
  })

  recorder.ondataavailable = (event) => {
    if (event.data.size > 0) onChunk(event.data)
  }

  return recorder
}

export async function startAudioCapture(onChunk: (chunk: Blob) => void) {
  const stream = await getMicrophoneStream()
  const recorder = createAudioRecorder(stream, onChunk)
  recorder.start(250)
  return {
    stream,
    recorder,
    stop: () => {
      recorder.stop()
      stream.getTracks().forEach((track) => track.stop())
    },
  }
}
