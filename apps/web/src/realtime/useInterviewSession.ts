import { useEffect, useRef, useState } from "react";
import { createAudioCapture, type MicStatus } from "./audioCapture";

export type RealtimeEvent = {
  type: string;
  text?: string;
  speaker?: string;
  name?: string;
  summary?: string;
  stage?: string;
  action?: string;
  bytes?: number;
  mode?: string;
  model?: string;
  message?: string;
};

export function useInterviewSession() {
  const socketRef = useRef<WebSocket | null>(null);
  const captureRef = useRef<ReturnType<typeof createAudioCapture> | null>(null);
  const [events, setEvents] = useState<RealtimeEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [micStatus, setMicStatus] = useState<MicStatus>("idle");
  const [micError, setMicError] = useState<string | undefined>();

  useEffect(() => {
    return () => {
      captureRef.current?.stop();
      socketRef.current?.close();
    };
  }, []);

  function start() {
    if (socketRef.current && socketRef.current.readyState !== WebSocket.CLOSED) {
      return;
    }
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
      setEvents((prev) => [...prev, JSON.parse(message.data)]);
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
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) {
      setMicError("请先连接面试官。");
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
      .catch(() => {
        const state = capture.getState();
        setMicStatus(state.status);
        setMicError(state.error ?? "麦克风启动失败。");
        captureRef.current = null;
      });
  }

  function stopMicrophone() {
    captureRef.current?.stop();
    captureRef.current = null;
    setMicStatus("idle");
    setMicError(undefined);
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
