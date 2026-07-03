const DEFAULT_OUTPUT_SAMPLE_RATE = 24000;

type BrowserAudioContext = typeof AudioContext;

type WindowWithWebkitAudio = Window & {
  webkitAudioContext?: BrowserAudioContext;
};

export function decodePcm16Base64(base64: string): Float32Array {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }

  const view = new DataView(bytes.buffer);
  const sampleCount = Math.floor(bytes.byteLength / 2);
  const samples = new Float32Array(sampleCount);
  for (let index = 0; index < sampleCount; index += 1) {
    samples[index] = view.getInt16(index * 2, true) / 0x8000;
  }
  return samples;
}

export function createPcmAudioPlayer() {
  let audioContext: AudioContext | null = null;
  let nextStartTime = 0;

  function ensureAudioContext(): AudioContext {
    if (audioContext) return audioContext;

    const AudioContextCtor =
      window.AudioContext ?? (window as WindowWithWebkitAudio).webkitAudioContext;
    if (!AudioContextCtor) {
      throw new Error("当前浏览器不支持音频播放。");
    }
    audioContext = new AudioContextCtor();
    return audioContext;
  }

  async function resume(): Promise<void> {
    const context = ensureAudioContext();
    if (context.state === "suspended") {
      await context.resume();
    }
  }

  async function playChunk(base64: string, sampleRate = DEFAULT_OUTPUT_SAMPLE_RATE): Promise<void> {
    if (!base64) return;

    const context = ensureAudioContext();
    await resume();

    const samples = decodePcm16Base64(base64);
    const buffer = context.createBuffer(1, samples.length, sampleRate);
    buffer.getChannelData(0).set(samples);

    const source = context.createBufferSource();
    source.buffer = buffer;
    source.connect(context.destination);

    const startAt = Math.max(context.currentTime, nextStartTime);
    source.start(startAt);
    nextStartTime = startAt + buffer.duration;
  }

  function resetQueue(): void {
    if (audioContext) {
      nextStartTime = audioContext.currentTime;
    }
  }

  function close(): void {
    if (audioContext && audioContext.state !== "closed") {
      void audioContext.close();
    }
    audioContext = null;
    nextStartTime = 0;
  }

  return { resume, playChunk, resetQueue, close };
}
