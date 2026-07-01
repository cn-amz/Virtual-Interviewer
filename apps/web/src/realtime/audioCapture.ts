const PCM_SAMPLE_RATE = 16000;
const WORKLET_URL = "/pcm16-capture-processor.js";

export type MicStatus = "idle" | "requesting" | "recording" | "error";

export type AudioCaptureState = {
  status: MicStatus;
  error?: string;
  mimeType?: string;
  sampleRate?: number;
};

export type AudioChunk = {
  base64: string;
  mimeType: string;
  sampleRate: number;
};

type ChunkCallback = (chunk: AudioChunk) => void;

export function createAudioCapture(onChunk: ChunkCallback) {
  let audioContext: AudioContext | null = null;
  let mediaStream: MediaStream | null = null;
  let sourceNode: MediaStreamAudioSourceNode | null = null;
  let workletNode: AudioWorkletNode | null = null;
  let silentGain: GainNode | null = null;
  let state: AudioCaptureState = { status: "idle" };

  function getState(): AudioCaptureState {
    return state;
  }

  async function start(): Promise<void> {
    if (state.status === "recording") return;

    state = { status: "requesting" };

    try {
      if (!window.AudioContext || !("audioWorklet" in AudioContext.prototype)) {
        throw new Error("当前浏览器不支持 AudioWorklet，无法采集 16 kHz PCM 音频。");
      }

      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error("当前浏览器不支持麦克风访问。");
      }

      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      audioContext = new AudioContext({ sampleRate: PCM_SAMPLE_RATE });
      await audioContext.audioWorklet.addModule(WORKLET_URL);

      sourceNode = audioContext.createMediaStreamSource(mediaStream);
      workletNode = new AudioWorkletNode(audioContext, "pcm16-capture-processor");
      silentGain = audioContext.createGain();
      silentGain.gain.value = 0;

      workletNode.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
        if (event.data.byteLength === 0) return;
        onChunk({
          base64: arrayBufferToBase64(event.data),
          mimeType: "audio/pcm",
          sampleRate: PCM_SAMPLE_RATE,
        });
      };

      sourceNode.connect(workletNode);
      workletNode.connect(silentGain);
      silentGain.connect(audioContext.destination);

      state = {
        status: "recording",
        mimeType: "audio/pcm",
        sampleRate: PCM_SAMPLE_RATE,
      };
    } catch (error) {
      await cleanup();
      let message: string;
      if (error instanceof DOMException && error.name === "NotAllowedError") {
        message =
          "麦克风权限被拒绝。请在浏览器地址栏或系统隐私设置中允许此站点访问麦克风，然后重新点击开始麦克风。";
      } else {
        message = error instanceof Error ? error.message : "无法启动麦克风。";
      }
      state = { status: "error", error: message };
      throw new Error(message);
    }
  }

  async function cleanup(): Promise<void> {
    workletNode?.port.close();
    sourceNode?.disconnect();
    workletNode?.disconnect();
    silentGain?.disconnect();
    mediaStream?.getTracks().forEach((track) => track.stop());
    if (audioContext && audioContext.state !== "closed") {
      await audioContext.close();
    }
    audioContext = null;
    mediaStream = null;
    sourceNode = null;
    workletNode = null;
    silentGain = null;
  }

  function stop(): void {
    void cleanup();
    state = { status: "idle" };
  }

  return { getState, start, stop };
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  const chunkSize = 0x8000;
  for (let index = 0; index < bytes.length; index += chunkSize) {
    const chunk = bytes.subarray(index, index + chunkSize);
    binary += String.fromCharCode(...chunk);
  }
  return btoa(binary);
}
