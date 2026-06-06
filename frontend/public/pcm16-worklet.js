class Pcm16Processor extends AudioWorkletProcessor {
  constructor(options) {
    super()
    this.targetSampleRate = options.processorOptions?.targetSampleRate ?? 16000
    this.chunkSamples = options.processorOptions?.chunkSamples ?? 1600
    this.resamplePosition = 0
    this.pendingSamples = new Float32Array(0)
    this.pcmChunk = new Int16Array(this.chunkSamples)
    this.pcmChunkOffset = 0
  }

  process(inputs, outputs) {
    const input = inputs[0]?.[0]
    if (!input?.length) return true

    const output = outputs[0]?.[0]
    if (output) output.fill(0)

    const samples = new Float32Array(this.pendingSamples.length + input.length)
    samples.set(this.pendingSamples)
    samples.set(input, this.pendingSamples.length)

    const ratio = sampleRate / this.targetSampleRate
    const availableSamples = samples.length - 1 - this.resamplePosition
    const outputLength = Math.max(0, Math.ceil(availableSamples / ratio))
    if (outputLength === 0) {
      this.pendingSamples = samples
      return true
    }

    for (let index = 0; index < outputLength; index += 1) {
      const sourceIndex = this.resamplePosition + index * ratio
      const left = Math.floor(sourceIndex)
      const right = Math.min(left + 1, samples.length - 1)
      const weight = sourceIndex - left
      const sample = samples[left] * (1 - weight) + samples[right] * weight
      const clamped = Math.max(-1, Math.min(1, sample))
      this.pcmChunk[this.pcmChunkOffset] = (
        clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff
      )
      this.pcmChunkOffset += 1

      if (this.pcmChunkOffset === this.chunkSamples) {
        const buffer = this.pcmChunk.buffer
        this.port.postMessage(buffer, [buffer])
        this.pcmChunk = new Int16Array(this.chunkSamples)
        this.pcmChunkOffset = 0
      }
    }

    const nextPosition = this.resamplePosition + outputLength * ratio
    const consumedSamples = Math.min(
      Math.floor(nextPosition),
      samples.length - 1,
    )
    this.pendingSamples = samples.slice(consumedSamples)
    this.resamplePosition = nextPosition - consumedSamples
    return true
  }
}

registerProcessor('pcm16-processor', Pcm16Processor)
