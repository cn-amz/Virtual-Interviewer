import { useEffect, useRef, useState } from "react";
import { createAudioCapture, type MicStatus } from "./audioCapture";
import { createPcmAudioPlayer } from "./audioPlayback";
import { createSpeechRecognition, type SpeechRecognitionCapture } from "./speechRecognition";

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
  session_id?: string;
  status?: "completed" | "cancelled";
  turn_id?: string;
  item_id?: string;
  response_id?: string;
  is_final?: boolean;
  source?: "provider_asr" | "browser_asr" | "provider" | "application";
};

export type InterviewSessionSelection = {
  provider: "bailian" | "minicpm";
  audioMode: "full_duplex" | "playback_gate";
  profileId: string;
  resumeName: string;
  jdId: string;
};

export type SessionState = "idle" | "connecting" | "ready" | "ending" | "persisted" | "error";

export type SessionStateAction =
  | { type: "connect" | "ready" | "finish" | "cancel" | "error" | "reset" }
  | { type: "persisted"; status: "completed" | "cancelled" };

export function shouldUseBrowserAsr(provider: InterviewSessionSelection["provider"]): boolean {
  return provider === "minicpm";
}

export function isProviderReady(
  state: "offline" | "loading" | "queued" | "idle" | "busy" | "error" | undefined
): boolean {
  return state === "idle";
}

export function shouldUploadMicrophone(
  audioMode: InterviewSessionSelection["audioMode"],
  playbackActive: boolean
): boolean {
  return audioMode === "full_duplex" || !playbackActive;
}

export function reduceSessionState(_state: SessionState, action: SessionStateAction): SessionState {
  if (action.type === "connect") return "connecting";
  if (action.type === "ready") return "ready";
  if (action.type === "finish" || action.type === "cancel") return "ending";
  if (action.type === "persisted") return action.status === "completed" ? "persisted" : "idle";
  if (action.type === "error") return "error";
  return "idle";
}

export function buildRealtimeUrl(selection: InterviewSessionSelection): string {
  const query = new URLSearchParams({
    provider: selection.provider,
    profile_id: selection.profileId,
    resume_name: selection.resumeName,
    jd_id: selection.jdId,
  });
  return `ws://localhost:8000/api/interviews/realtime?${query.toString()}`;
}

export function appendRealtimeEvent(
  events: RealtimeEvent[],
  event: RealtimeEvent
): RealtimeEvent[] {
  const last = events[events.length - 1];
  if (
    event.type === "transcript.partial" &&
    last?.type === "transcript.partial" &&
    (!event.turn_id || event.turn_id === last.turn_id)
  ) {
    return [...events.slice(0, -1), event];
  }
  if (event.type === "assistant.audio.chunk" && last?.type === "assistant.audio.chunk") {
    return [...events.slice(0, -1), event];
  }
  if (event.type === "assistant.text.delta") {
    const index = event.turn_id
      ? findEventByTurnId(events, "assistant.text.delta", event.turn_id)
      : findMergeableAssistantTextIndex(events);
    if (index >= 0) {
      const merged = {
        ...events[index],
        text: `${events[index].text ?? ""}${event.text ?? ""}`,
      };
      return [...events.slice(0, index), merged, ...events.slice(index + 1)];
    }
  }
  if (
    event.type === "transcript.item" &&
    event.speaker === "candidate"
  ) {
    const partialIndex = event.turn_id
      ? findEventByTurnId(events, "transcript.partial", event.turn_id)
      : findLatestCandidatePartialIndex(events);
    if (partialIndex >= 0) {
      return [...events.slice(0, partialIndex), event, ...events.slice(partialIndex + 1)];
    }
  }
  return [...events, event];
}

function findEventByTurnId(events: RealtimeEvent[], type: string, turnId: string): number {
  for (let index = events.length - 1; index >= 0; index -= 1) {
    if (events[index].type === type && events[index].turn_id === turnId) return index;
  }
  return -1;
}

function findLatestCandidatePartialIndex(events: RealtimeEvent[]): number {
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const event = events[index];
    if (event.type === "transcript.item" && event.speaker === "candidate") return -1;
    if (event.type === "transcript.partial" && event.speaker === "candidate") return index;
  }
  return -1;
}

function findMergeableAssistantTextIndex(events: RealtimeEvent[]): number {
  for (let index = events.length - 1; index >= 0; index -= 1) {
    const event = events[index];
    if (event.type === "assistant.text.delta") return index;
    if (isAssistantTextBoundary(event)) return -1;
  }
  return -1;
}

function isAssistantTextBoundary(event: RealtimeEvent): boolean {
  if (event.type === "bailian.event" && event.event === "response.done") return true;
  return [
    "session.ready",
    "session.ended",
    "transcript.partial",
    "transcript.item",
    "client.pending",
    "audio.stopped",
    "assistant.turn.completed",
    "audio.error",
    "realtime.error",
  ].includes(event.type);
}

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  text: string;
  isFinal: boolean;
};

export function deriveMessages(events: RealtimeEvent[]): ChatMessage[] {
  const messages: ChatMessage[] = [];
  const positions = new Map<string, number>();
  let legacyUserId = "";
  let legacyAssistantId = "";
  let userCount = 0;
  let assistantCount = 0;

  function upsert(id: string, role: ChatMessage["role"], text: string, isFinal: boolean, replace: boolean) {
    const key = `${role}:${id}`;
    const position = positions.get(key);
    if (position === undefined) {
      positions.set(key, messages.length);
      messages.push({ id, role, text, isFinal });
      return;
    }
    const current = messages[position];
    messages[position] = {
      ...current,
      text: replace ? text : `${current.text}${text}`,
      isFinal: current.isFinal || isFinal,
    };
  }

  for (const event of events) {
    if (
      (event.type === "transcript.partial" || event.type === "transcript.item") &&
      event.speaker === "candidate"
    ) {
      if (!event.turn_id && (!legacyUserId || messages[messages.length - 1]?.role !== "user")) {
        userCount += 1;
        legacyUserId = `legacy-user-${userCount}`;
      }
      const id = event.turn_id ?? legacyUserId;
      upsert(id, "user", event.text ?? "", event.is_final ?? event.type === "transcript.item", true);
      legacyAssistantId = "";
    } else if (event.type === "assistant.text.delta") {
      if (!event.turn_id && !legacyAssistantId) {
        assistantCount += 1;
        legacyAssistantId = `legacy-assistant-${assistantCount}`;
      }
      const id = event.turn_id ?? legacyAssistantId;
      upsert(id, "assistant", event.text ?? "", event.is_final ?? false, false);
      legacyUserId = "";
    } else if (
      (event.type === "bailian.event" && event.event === "response.done") ||
      event.type === "assistant.turn.completed"
    ) {
      const lastAssistant = [...messages].reverse().find((message) => message.role === "assistant");
      if (lastAssistant) lastAssistant.isFinal = true;
      legacyAssistantId = "";
    }
  }
  return messages;
}

export function isNearBottom(
  scrollTop: number,
  clientHeight: number,
  scrollHeight: number
): boolean {
  return scrollHeight - scrollTop - clientHeight <= 80;
}

export function useInterviewSession(
  onPersisted?: (interviewId: string, status: "completed" | "cancelled") => void
) {
  const socketRef = useRef<WebSocket | null>(null);
  const selectionRef = useRef<InterviewSessionSelection | null>(null);
  const captureRef = useRef<ReturnType<typeof createAudioCapture> | null>(null);
  const recognitionRef = useRef<SpeechRecognitionCapture | null>(null);
  const playbackActiveRef = useRef(false);
  const audioPlayerRef = useRef(
    createPcmAudioPlayer((active) => {
      playbackActiveRef.current = active;
    })
  );
  const interviewIdRef = useRef<string>();
  const browserTurnRef = useRef<string>();
  const browserTurnCountRef = useRef(0);
  const onPersistedRef = useRef(onPersisted);
  onPersistedRef.current = onPersisted;
  const [events, setEvents] = useState<RealtimeEvent[]>([]);
  const [sessionState, setSessionState] = useState<SessionState>("idle");
  const sessionStateRef = useRef<SessionState>("idle");
  const [micStatus, setMicStatus] = useState<MicStatus>("idle");
  const [micError, setMicError] = useState<string | undefined>();
  const [interviewId, setInterviewId] = useState<string>();

  function transition(action: SessionStateAction) {
    const next = reduceSessionState(sessionStateRef.current, action);
    sessionStateRef.current = next;
    setSessionState(next);
  }

  useEffect(() => {
    return () => {
      captureRef.current?.stop();
      recognitionRef.current?.stop();
      audioPlayerRef.current.close();
      socketRef.current?.close();
    };
  }, []);

  function start(selection: InterviewSessionSelection) {
    if (socketRef.current && socketRef.current.readyState !== WebSocket.CLOSED) {
      return;
    }
    void audioPlayerRef.current.resume().catch(() => undefined);
    setEvents([]);
    setInterviewId(undefined);
    interviewIdRef.current = undefined;
    selectionRef.current = selection;
    browserTurnRef.current = undefined;
    transition({ type: "connect" });
    const socket = new WebSocket(buildRealtimeUrl(selection));
    socketRef.current = socket;
    socket.onclose = () => {
      captureRef.current?.stop();
      captureRef.current = null;
      recognitionRef.current?.stop();
      recognitionRef.current = null;
      setMicStatus("idle");
      socketRef.current = null;
      if (!['idle', 'persisted'].includes(sessionStateRef.current)) {
        transition({ type: "error" });
      }
    };
    socket.onerror = () => transition({ type: "error" });
    socket.onmessage = (message) => {
      const event = JSON.parse(message.data) as RealtimeEvent;
      if (event.type === "session.ready" && event.session_id) {
        setInterviewId(event.session_id);
        interviewIdRef.current = event.session_id;
        transition({ type: "ready" });
      }
      if (event.type === "session.persisted" && event.session_id && event.status) {
        transition({ type: "persisted", status: event.status });
        socket.close();
        onPersistedRef.current?.(event.session_id, event.status);
      }
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

  function recordCandidateTranscript(text: string) {
    const transcript = text.trim();
    const turnId = browserTurnRef.current ?? nextBrowserTurnId();
    if (!transcript || !sendJson({
      type: "transcript.item",
      speaker: "candidate",
      text: transcript,
      turn_id: turnId,
      is_final: true,
      source: "browser_asr",
    })) {
      return;
    }
    setEvents((prev) => appendRealtimeEvent(prev, {
      type: "transcript.item",
      speaker: "candidate",
      text: transcript,
      turn_id: turnId,
      is_final: true,
      source: "browser_asr",
    }));
    browserTurnRef.current = undefined;
  }

  function nextBrowserTurnId(): string {
    browserTurnCountRef.current += 1;
    const turnId = `local-candidate-${browserTurnCountRef.current}`;
    browserTurnRef.current = turnId;
    return turnId;
  }

  function startBrowserTranscription() {
    const recognition = createSpeechRecognition({
      onPartial: (text) => {
        if (!text.trim()) return;
        const turnId = browserTurnRef.current ?? nextBrowserTurnId();
        setEvents((prev) => appendRealtimeEvent(prev, {
          type: "transcript.partial",
          speaker: "candidate",
          text,
          turn_id: turnId,
          is_final: false,
          source: "browser_asr",
        }));
      },
      onFinal: recordCandidateTranscript,
      onError: setMicError,
    });
    if (!recognition) {
      setMicError("当前浏览器不支持语音转写；语音仍会发送给 MiniCPM，但不会写入报告。");
      return;
    }
    recognitionRef.current = recognition;
    try {
      recognition.start();
    } catch (error) {
      recognitionRef.current = null;
      setMicError(error instanceof Error ? error.message : "浏览器语音识别启动失败。");
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
      const audioMode = selectionRef.current?.audioMode ?? "full_duplex";
      if (!shouldUploadMicrophone(audioMode, playbackActiveRef.current)) return;
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
        if (selectionRef.current && shouldUseBrowserAsr(selectionRef.current.provider)) {
          startBrowserTranscription();
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
    recognitionRef.current?.stop();
    recognitionRef.current = null;
    captureRef.current?.stop();
    captureRef.current = null;
    setMicStatus("idle");
    setMicError(undefined);
    audioPlayerRef.current.resetQueue();
    sendJson({ type: "audio.stop" });
  }

  function stopLocalCapture() {
    recognitionRef.current?.stop();
    recognitionRef.current = null;
    captureRef.current?.stop();
    captureRef.current = null;
    setMicStatus("idle");
    setMicError(undefined);
  }

  function finish() {
    stopLocalCapture();
    transition({ type: "finish" });
    if (!sendJson({ type: "session.end" })) transition({ type: "error" });
  }

  function cancel() {
    stopLocalCapture();
    transition({ type: "cancel" });
    if (!sendJson({ type: "session.cancel" })) transition({ type: "error" });
  }

  return {
    connected: sessionState === "ready",
    connecting: sessionState === "connecting",
    sessionState,
    events,
    interviewId,
    micStatus,
    micError,
    start,
    sendText,
    finish,
    cancel,
    startMicrophone,
    stopMicrophone,
  };
}
