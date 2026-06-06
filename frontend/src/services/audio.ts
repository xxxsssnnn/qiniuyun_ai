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

function resampleTo16Khz(input: Float32Array, sourceSampleRate: number) {
  if (sourceSampleRate === 16000) return input
  const ratio = sourceSampleRate / 16000
  const output = new Float32Array(Math.round(input.length / ratio))
  for (let i = 0; i < output.length; i += 1) {
    const sourceIndex = i * ratio
    const left = Math.floor(sourceIndex)
    const right = Math.min(left + 1, input.length - 1)
    const weight = sourceIndex - left
    output[i] = input[left] * (1 - weight) + input[right] * weight
  }
  return output
}

function encodePcm16(samples: Float32Array) {
  const buffer = new ArrayBuffer(samples.length * 2)
  const view = new DataView(buffer)
  samples.forEach((sample, index) => {
    const clamped = Math.max(-1, Math.min(1, sample))
    view.setInt16(index * 2, clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff, true)
  })
  return buffer
}

export async function startAudioCapture(onChunk: (chunk: ArrayBuffer) => void) {
  const stream = await getMicrophoneStream()
  const audioContext = new AudioContext()
  const source = audioContext.createMediaStreamSource(stream)
  const processor = audioContext.createScriptProcessor(4096, 1, 1)
  const silentGain = audioContext.createGain()
  silentGain.gain.value = 0

  processor.onaudioprocess = (event) => {
    const channel = event.inputBuffer.getChannelData(0)
    onChunk(encodePcm16(resampleTo16Khz(channel, audioContext.sampleRate)))
  }

  source.connect(processor)
  processor.connect(silentGain)
  silentGain.connect(audioContext.destination)
  return {
    stream,
    stop: () => {
      processor.disconnect()
      source.disconnect()
      silentGain.disconnect()
      void audioContext.close()
      stream.getTracks().forEach((track) => track.stop())
    },
  }
}
