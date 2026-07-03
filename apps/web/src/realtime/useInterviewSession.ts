import { useEffect, useRef, useState } from "react";
import { createAudioCapture, type MicStatus } from "./audioCapture";
import { createPcmAudioPlayer } from "./audioPlayback";

export type RealtimeEvent = {
  type: string;
  text?: string;
  speaker?: string;
  event?: string;
  data?: string;
  mime_type?: string;
  sample_rate?: number;
  name?: string;
  summary?: string;
  stage?: string;
  action?: string;
  bytes?: number;
  mode?: string;
  model?: string;
  message?: string;
};

export function appendRealtimeEvent(
  events: RealtimeEvent[],
  event: RealtimeEvent
): RealtimeEvent[] {
  const last = events[events.length - 1];
  if (event.type === "transcript.partial" && last?.type === "transcript.partial") {
    return [...events.slice(0, -1), event];
  }
  if (event.type === "assistant.audio.chunk" && last?.type === "assistant.audio.chunk") {
    return [...events.slice(0, -1), event];
  }
  if (
    event.type === "transcript.item" &&
    event.speaker === "candidate" &&
    last?.type === "transcript.partial"
  ) {
    return [...events.slice(0, -1), event];
  }
  return [...events, event];
}

export function useInterviewSession() {
  const socketRef = useRef<WebSocket | null>(null);
  const captureRef = useRef<ReturnType<typeof createAudioCapture> | null>(null);
  const audioPlayerRef = useRef(createPcmAudioPlayer());
  const [events, setEvents] = useState<RealtimeEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [micStatus, setMicStatus] = useState<MicStatus>("idle");
  const [micError, setMicError] = useState<string | undefined>();

  useEffect(() => {
    return () => {
      captureRef.current?.stop();
      audioPlayerRef.current.close();
      socketRef.current?.close();
    };
  }, []);

  function start() {
    if (socketRef.current && socketRef.current.readyState !== WebSocket.CLOSED) {
      return;
    }
    void audioPlayerRef.current.resume().catch(() => undefined);
    const socket = new WebSocket("ws://localhost:8000/api/interviews/realtime");
    socketRef.current = socket;
    socket.onopen = () => setConnected(true);
    socket.onclose = () => {
      captureRef.current?.stop();
      captureRef.current = null;
      setMicStatus("idle");
      setConnected(false);
      socketRef.current = null;
    };
    socket.onmessage = (message) => {
      const event = JSON.parse(message.data) as RealtimeEvent;
      if (event.type === "assistant.audio.chunk") {
        void audioPlayerRef.current
          .playChunk(event.data ?? "", event.sample_rate ?? 24000)
          .catch((error: unknown) => {
            const errorMessage =
              error instanceof Error ? error.message : "无法播放面试官语音。";
            setEvents((prev) =>
              appendRealtimeEvent(prev, { type: "audio.error", message: errorMessage })
            );
          });
      }
      setEvents((prev) => appendRealtimeEvent(prev, event));
    };
  }

  function sendJson(payload: unknown): boolean {
    if (socketRef.current?.readyState !== WebSocket.OPEN) {
      return false;
    }
    socketRef.current.send(JSON.stringify(payload));
    return true;
  }

  function sendText(text: string) {
    void audioPlayerRef.current.resume().catch(() => undefined);
    if (sendJson({ type: "text.input", text })) {
      setEvents((prev) => [
        ...prev,
        {
          type: "client.pending",
          message: "已发送文字回答，等待模型回复...",
        },
      ]);
    }
  }

  function startMicrophone() {
    void audioPlayerRef.current.resume().catch(() => undefined);
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      setMicError("请先连接面试官，再开启麦克风。");
      setEvents((prev) => [
        ...prev,
        { type: "audio.error", message: "请先连接面试官，再开启麦克风。" },
      ]);
      return;
    }
    if (captureRef.current) {
      return;
    }

    const capture = createAudioCapture((chunk) => {
      sendJson({
        type: "audio.chunk",
        data: chunk.base64,
        mime_type: chunk.mimeType,
        sample_rate: chunk.sampleRate,
      });
    });

    captureRef.current = capture;
    setMicStatus("requesting");
    setMicError(undefined);

    capture
      .start()
      .then(() => {
        const state = capture.getState();
        setMicStatus(state.status);
        if (state.mimeType) {
          sendJson({
            type: "audio.start",
            mime_type: state.mimeType,
            sample_rate: state.sampleRate ?? 16000,
          });
        }
      })
      .catch((error: unknown) => {
        const state = capture.getState();
        const errorMessage =
          state.error ??
          (error instanceof Error ? error.message : "麦克风启动失败。");
        setMicStatus(state.status);
        setMicError(errorMessage);
        setEvents((prev) => [
          ...prev,
          { type: "audio.error", message: errorMessage },
        ]);
        captureRef.current = null;
      });
  }

  function stopMicrophone() {
    captureRef.current?.stop();
    captureRef.current = null;
    setMicStatus("idle");
    setMicError(undefined);
    audioPlayerRef.current.resetQueue();
    sendJson({ type: "audio.stop" });
  }

  function end() {
    captureRef.current?.stop();
    captureRef.current = null;
    setMicStatus("idle");
    setMicError(undefined);
    sendJson({ type: "session.end" });
    socketRef.current?.close();
  }

  return {
    connected,
    events,
    micStatus,
    micError,
    start,
    sendText,
    end,
    startMicrophone,
    stopMicrophone,
  };
}
