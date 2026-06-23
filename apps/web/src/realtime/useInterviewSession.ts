import { useEffect, useRef, useState } from "react";

export type RealtimeEvent = {
  type: string;
  text?: string;
  speaker?: string;
  name?: string;
  summary?: string;
  stage?: string;
  action?: string;
};

export function useInterviewSession() {
  const socketRef = useRef<WebSocket | null>(null);
  const [events, setEvents] = useState<RealtimeEvent[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    return () => {
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
      setConnected(false);
      socketRef.current = null;
    };
    socket.onmessage = (message) => {
      setEvents((prev) => [...prev, JSON.parse(message.data)]);
    };
  }

  function sendText(text: string) {
    socketRef.current?.send(JSON.stringify({ type: "text.input", text }));
  }

  function end() {
    socketRef.current?.send(JSON.stringify({ type: "session.end" }));
    socketRef.current?.close();
  }

  return { connected, events, start, sendText, end };
}
