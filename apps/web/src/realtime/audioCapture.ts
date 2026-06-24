const PREFERRED_MIME_TYPES = ["audio/webm;codecs=opus", "audio/webm"];

export type MicStatus = "idle" | "requesting" | "recording" | "error";

export type AudioCaptureState = {
  status: MicStatus;
  error?: string;
  mimeType?: string;
};

export type AudioChunk = {
  base64: string;
  mimeType: string;
};

type ChunkCallback = (chunk: AudioChunk) => void;

export function createAudioCapture(onChunk: ChunkCallback) {
  let mediaRecorder: MediaRecorder | null = null;
  let stream: MediaStream | null = null;
  let state: AudioCaptureState = { status: "idle" };

  function getState(): AudioCaptureState {
    return state;
  }

  function resolveMimeType(): string {
    for (const candidate of PREFERRED_MIME_TYPES) {
      if (MediaRecorder.isTypeSupported(candidate)) {
        return candidate;
      }
    }
    throw new Error("当前浏览器不支持所需音频编码（opus/webm）。");
  }

  async function start(): Promise<void> {
    if (state.status === "recording") return;

    state = { status: "requesting" };

    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = resolveMimeType();

      mediaRecorder = new MediaRecorder(stream, { mimeType });
      state = { status: "recording", mimeType };

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size === 0) return;
        const reader = new FileReader();
        reader.onloadend = () => {
          const result = typeof reader.result === "string" ? reader.result : "";
          const base64 = result.split(",")[1];
          if (base64) onChunk({ base64, mimeType });
        };
        reader.readAsDataURL(event.data);
      };

      mediaRecorder.start(250);
    } catch (error) {
      stream?.getTracks().forEach((track) => track.stop());
      mediaRecorder = null;
      stream = null;
      state = {
        status: "error",
        error: error instanceof Error ? error.message : "无法启动麦克风。",
      };
      throw error;
    }
  }

  function stop(): void {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
      mediaRecorder.stop();
    }
    stream?.getTracks().forEach((track) => track.stop());
    mediaRecorder = null;
    stream = null;
    state = { status: "idle" };
  }

  return { getState, start, stop };
}
