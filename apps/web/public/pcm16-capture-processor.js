class Pcm16CaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.targetSampleRate = 16000;
    this.sourceSampleRate = sampleRate;
    this.readOffset = 0;
  }

  process(inputs) {
    const input = inputs[0] && inputs[0][0];
    if (!input || input.length === 0) {
      return true;
    }

    const samples = this.downsample(input);
    if (samples.length === 0) {
      return true;
    }

    const buffer = new ArrayBuffer(samples.length * 2);
    const view = new DataView(buffer);
    for (let index = 0; index < samples.length; index += 1) {
      const clamped = Math.max(-1, Math.min(1, samples[index]));
      const int16 = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff;
      view.setInt16(index * 2, int16, true);
    }
    this.port.postMessage(buffer, [buffer]);
    return true;
  }

  downsample(input) {
    if (this.sourceSampleRate <= this.targetSampleRate) {
      return input;
    }

    const ratio = this.sourceSampleRate / this.targetSampleRate;
    const output = [];
    let offset = this.readOffset;

    while (offset < input.length) {
      const nextOffset = offset + ratio;
      const averageEnd = Math.min(input.length, nextOffset);
      let total = 0;
      let count = 0;
      for (let index = Math.floor(offset); index < Math.floor(averageEnd); index += 1) {
        total += input[index];
        count += 1;
      }
      // ponytail: simple window averaging is enough for speech ASR; upgrade to a proper
      // low-pass resampler if music-quality audio or tougher noise conditions become a goal.
      output.push(count > 0 ? total / count : input[Math.floor(offset)]);
      offset = nextOffset;
    }

    this.readOffset = offset - input.length;
    return output;
  }
}

registerProcessor("pcm16-capture-processor", Pcm16CaptureProcessor);
