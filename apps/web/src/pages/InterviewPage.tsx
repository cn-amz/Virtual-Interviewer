import { useEffect, useRef, useState } from "react";
import { getProviderStatus, type ProviderStatus } from "../api/client";
import {
  deriveMessages,
  isNearBottom,
  isProviderReady,
  type InterviewSessionSelection,
  useInterviewSession,
} from "../realtime/useInterviewSession";

type InterviewPageProps = {
  onFinish: (interviewId?: string) => void;
  onCancel: () => void;
  selection: InterviewSessionSelection;
};

export function InterviewPage({ onFinish, onCancel, selection }: InterviewPageProps) {
  const {
    connected,
    connecting,
    sessionState,
    events,
    micStatus,
    micError,
    start,
    sendText,
    finish,
    cancel,
    startMicrophone,
    stopMicrophone,
  } = useInterviewSession((interviewId, status) => {
    if (status === "completed") onFinish(interviewId);
    else onCancel();
  });
  const [answer, setAnswer] = useState(
    "我通过 ROS2 完成机械臂运动控制，并引入插值算法提升轨迹稳定性。"
  );
  const transcriptRef = useRef<HTMLDivElement | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement | null>(null);
  const autoFollowRef = useRef(true);
  const [followPaused, setFollowPaused] = useState(false);
  const [providerStatus, setProviderStatus] = useState<ProviderStatus>();
  const messages = deriveMessages(events);
  const errors = events.filter(
    (event) => event.type === "audio.error" || event.type === "realtime.error"
  );

  const micLabel =
    micStatus === "recording"
      ? "停止麦克风"
      : micStatus === "requesting"
        ? "请求权限中..."
        : "开始麦克风";

  const isMicActive = micStatus === "recording";

  function finishInterview() {
    finish();
  }

  function cancelInterview() {
    if (window.confirm("退出后不会生成报告，确定退出吗？")) cancel();
  }

  const isEnding = sessionState === "ending";

  useEffect(() => {
    if (connected) return;
    let active = true;
    const refresh = () => {
      void getProviderStatus(selection.provider)
        .then((status) => {
          if (active) setProviderStatus(status);
        })
        .catch(() => {
          if (active) {
            setProviderStatus({
              provider: selection.provider,
              state: "offline",
              detail: "状态服务不可用",
              queue_length: 0,
            });
          }
        });
    };
    refresh();
    const timer = window.setInterval(refresh, 3000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [connected, selection.provider]);

  useEffect(() => {
    if (autoFollowRef.current) {
      transcriptEndRef.current?.scrollIntoView({ block: "end" });
    }
  }, [events]);

  function handleTranscriptScroll() {
    const element = transcriptRef.current;
    if (!element) return;
    const nearBottom = isNearBottom(element.scrollTop, element.clientHeight, element.scrollHeight);
    autoFollowRef.current = nearBottom;
    setFollowPaused(!nearBottom);
  }

  function returnToLatest() {
    autoFollowRef.current = true;
    setFollowPaused(false);
    transcriptEndRef.current?.scrollIntoView({ block: "end", behavior: "smooth" });
  }

  return (
    <section className="interview-grid">
      <div className="panel">
        <p className="eyebrow">实时模拟面试</p>
        <h1>虚拟面试官</h1>
        <p>连接状态：{isEnding ? "正在保存面试" : connected ? "模型已就绪" : connecting ? "正在等待模型" : sessionState === "error" ? "连接异常" : "未连接"}</p>
        {!connected && (
          <p className="mic-status mic-status--hint">
            引擎状态：{providerStatus?.detail ?? "正在检查..."}
          </p>
        )}
        <div className="button-row">
          <button className="primary-button" disabled={connecting || connected || isEnding || !isProviderReady(providerStatus?.state)} onClick={() => start(selection)}>
            连接面试官
          </button>
          <button className="secondary-button" disabled={!connected} onClick={() => sendText(answer)}>
            发送模拟回答
          </button>
          <button
            className={isMicActive ? "mic-active-button" : "secondary-button"}
            disabled={micStatus === "requesting" || !connected || isEnding}
            onClick={isMicActive ? stopMicrophone : startMicrophone}
          >
            {micLabel}
          </button>
          <button className="secondary-button" disabled={!connected || isEnding} onClick={cancelInterview}>
            退出面试
          </button>
          <button className="secondary-button" disabled={!connected || isEnding} onClick={finishInterview}>
            结束并生成报告
          </button>
        </div>
        {micStatus !== "idle" && (
          <p className={`mic-status mic-status--${micStatus}`}>
            麦克风：
            {micStatus === "recording"
              ? "录音中"
              : micStatus === "requesting"
                ? "请求权限中..."
                : "错误"}
          </p>
        )}
        {!connected && (
          <p className="mic-status mic-status--hint">{connecting ? "正在等待模型 Worker，请勿开始录音。" : "请先连接面试官，再开启麦克风。"}</p>
        )}
        {micError && <p className="mic-error">{micError}</p>}
        <textarea value={answer} onChange={(event) => setAnswer(event.target.value)} />
      </div>
      <div className="panel">
        <h2>面试对话</h2>
        <div className="chat-transcript-shell">
        <div className="chat-transcript" ref={transcriptRef} onScroll={handleTranscriptScroll}>
          {messages.length === 0 ? (
            <p className="chat-empty">连接面试官后，对话将显示在这里。</p>
          ) : (
            messages.map((message) => (
              <div
                className={`chat-bubble chat-bubble--${message.role}`}
                key={`${message.role}-${message.id}`}
              >
                <span className="chat-bubble__speaker">
                  {message.role === "user" ? "候选人" : "面试官"}
                </span>
                <p className="chat-bubble__text">{message.text}</p>
              </div>
            ))
          )}
          <div ref={transcriptEndRef} />
        </div>
        {followPaused && (
          <button className="chat-follow-button" type="button" aria-label="回到最新消息" onClick={returnToLatest}>
            ↓
          </button>
        )}
        </div>
        {errors.length > 0 && (
          <div className="chat-errors">
            {errors.map((event, index) => (
              <p className="chat-error" key={`error-${index}`}>
                {event.message ?? "发生错误。"}
              </p>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
