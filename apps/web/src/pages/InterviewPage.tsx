import { useState } from "react";
import { type RealtimeEvent, useInterviewSession } from "../realtime/useInterviewSession";

type InterviewPageProps = {
  onFinish: () => void;
};

const eventLabels: Record<string, string> = {
  "session.ready": "会话就绪",
  "assistant.text.delta": "面试官回复",
  "assistant.audio.chunk": "面试官语音",
  "transcript.partial": "实时转写",
  "transcript.item": "发言记录",
  "audio.started": "麦克风已开启",
  "audio.stopped": "麦克风已停止",
  "audio.error": "麦克风错误",
  "client.pending": "等待回复",
  "text.mode": "文本模式",
  "realtime.error": "实时链路错误",
  "bailian.event": "百炼事件",
  "session.ended": "会话结束",
};

function eventTitle(event: RealtimeEvent): string {
  return eventLabels[event.type] ?? event.type;
}

function eventContent(event: RealtimeEvent): string {
  if (event.type === "assistant.audio.chunk") {
    return "正在播放模型语音...";
  }
  return (
    event.text ??
    event.summary ??
    event.action ??
    event.stage ??
    event.message ??
    event.event ??
    event.mode ??
    event.model ??
    (event.bytes ? `${event.bytes} 字节` : "")
  );
}

export function InterviewPage({ onFinish }: InterviewPageProps) {
  const {
    connected,
    events,
    micStatus,
    micError,
    start,
    sendText,
    end,
    startMicrophone,
    stopMicrophone,
  } = useInterviewSession();
  const [answer, setAnswer] = useState(
    "我通过 ROS2 完成机械臂运动控制，并引入插值算法提升轨迹稳定性。"
  );

  const micLabel =
    micStatus === "recording"
      ? "停止麦克风"
      : micStatus === "requesting"
        ? "请求权限中..."
        : "开始麦克风";

  const isMicActive = micStatus === "recording";

  function finishInterview() {
    end();
    onFinish();
  }

  return (
    <section className="interview-grid">
      <div className="panel">
        <p className="eyebrow">实时模拟面试</p>
        <h1>虚拟面试官</h1>
        <p>连接状态：{connected ? "已连接" : "未连接"}</p>
        <div className="button-row">
          <button className="primary-button" onClick={start}>
            连接面试官
          </button>
          <button className="secondary-button" onClick={() => sendText(answer)}>
            发送模拟回答
          </button>
          <button
            className={isMicActive ? "mic-active-button" : "secondary-button"}
            disabled={micStatus === "requesting" || !connected}
            onClick={isMicActive ? stopMicrophone : startMicrophone}
          >
            {micLabel}
          </button>
          <button className="secondary-button" onClick={finishInterview}>
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
          <p className="mic-status mic-status--hint">请先连接面试官，再开启麦克风。</p>
        )}
        {micError && <p className="mic-error">{micError}</p>}
        <textarea value={answer} onChange={(event) => setAnswer(event.target.value)} />
      </div>
      <div className="panel">
        <h2>事件流</h2>
        <div className="event-list">
          {events.map((event, index) => (
            <div className="event-item" key={`${event.type}-${index}`}>
              <strong>{eventTitle(event)}</strong>
              <span>{eventContent(event)}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
