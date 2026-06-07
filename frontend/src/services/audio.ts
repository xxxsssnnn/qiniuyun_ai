export type AudioCaptureState = 'idle' | 'starting' | 'recording' | 'stopped' | 'error'
export type AudioCaptureSession = {
  stop: () => Promise<void>
}

export async function getMicrophoneStream() {
  return navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
  })
}

export async function startAudioCapture(onChunk: (chunk: ArrayBuffer) => void) {
  const stream = await getMicrophoneStream()
  const audioContext = new AudioContext()
  let source: MediaStreamAudioSourceNode | null = null
  let processor: AudioWorkletNode | null = null
  let silentGain: GainNode | null = null
  let stopPromise: Promise<void> | null = null

  try {
    if (audioContext.state === 'suspended') {
      await audioContext.resume()
    }
    await audioContext.audioWorklet.addModule('/pcm16-worklet.js?v=3')
    source = audioContext.createMediaStreamSource(stream)
    processor = new AudioWorkletNode(audioContext, 'pcm16-processor', {
      numberOfInputs: 1,
      numberOfOutputs: 1,
      channelCount: 1,
      processorOptions: {
        targetSampleRate: 16000,
        chunkSamples: 1600,
      },
    })
    silentGain = audioContext.createGain()
    silentGain.gain.value = 0
    processor.port.onmessage = (event: MessageEvent<ArrayBuffer | { type: string }>) => {
      if (event.data instanceof ArrayBuffer && event.data.byteLength > 0) {
        onChunk(event.data)
      }
    }
    processor.onprocessorerror = () => {
      stream.getTracks().forEach((track) => track.stop())
    }

    source.connect(processor)
    processor.connect(silentGain)
    silentGain.connect(audioContext.destination)
  } catch (error) {
    await audioContext.close()
    stream.getTracks().forEach((track) => track.stop())
    throw error
  }

  return {
    stop: () => {
      if (stopPromise) return stopPromise
      stopPromise = new Promise<void>((resolve) => {
        let finished = false
        const finish = () => {
          if (finished) return
          finished = true
          if (processor) {
            processor.port.onmessage = null
            processor.onprocessorerror = null
            processor.disconnect()
          }
          source?.disconnect()
          silentGain?.disconnect()
          stream.getTracks().forEach((track) => track.stop())
          void audioContext.close().finally(resolve)
        }

        if (!processor) {
          finish()
          return
        }

        const timeoutId = window.setTimeout(finish, 150)
        processor.port.onmessage = (
          event: MessageEvent<ArrayBuffer | { type: string }>,
        ) => {
          if (event.data instanceof ArrayBuffer) {
            if (event.data.byteLength > 0) onChunk(event.data)
            return
          }
          if (event.data?.type === 'flushed') {
            window.clearTimeout(timeoutId)
            finish()
          }
        }
        processor.port.postMessage({ type: 'flush' })
      })
      return stopPromise
    },
  } satisfies AudioCaptureSession
}
