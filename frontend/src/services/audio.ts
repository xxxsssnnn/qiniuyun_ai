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

export async function startAudioCapture(onChunk: (chunk: ArrayBuffer) => void) {
  const stream = await getMicrophoneStream()
  const audioContext = new AudioContext()
  let source: MediaStreamAudioSourceNode | null = null
  let processor: AudioWorkletNode | null = null
  let silentGain: GainNode | null = null

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
        chunkSamples: 1280,
      },
    })
    silentGain = audioContext.createGain()
    silentGain.gain.value = 0
    processor.port.onmessage = (event: MessageEvent<ArrayBuffer | { type: string }>) => {
      if (event.data instanceof ArrayBuffer && event.data.byteLength > 0) onChunk(event.data)
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
    stream,
    stop: async () => {
      if (processor) {
        source?.disconnect()
        await new Promise<void>((resolve) => {
          const timeout = window.setTimeout(resolve, 250)
          processor!.port.onmessage = (event: MessageEvent<ArrayBuffer | { type: string }>) => {
            if (event.data instanceof ArrayBuffer && event.data.byteLength > 0) {
              onChunk(event.data)
              return
            }
            if (!(event.data instanceof ArrayBuffer) && event.data.type === 'flushed') {
              window.clearTimeout(timeout)
              resolve()
            }
          }
          processor!.port.postMessage({ type: 'flush' })
        })
        processor.port.onmessage = null
        processor.onprocessorerror = null
        processor.disconnect()
      }
      silentGain?.disconnect()
      void audioContext.close()
      stream.getTracks().forEach((track) => track.stop())
    },
  }
}
