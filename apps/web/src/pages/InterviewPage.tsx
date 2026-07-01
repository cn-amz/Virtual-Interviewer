import { useState } from "react";
import { useInterviewSession } from "../realtime/useInterviewSession";

type InterviewPageProps = {
  onFinish: () => void;
};

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
        <p className="eyebrow">Realtime Interview</p>
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
        {micError && <p className="mic-error">{micError}</p>}
        <textarea value={answer} onChange={(event) => setAnswer(event.target.value)} />
      </div>
      <div className="panel">
        <h2>事件流</h2>
        <div className="event-list">
          {events.map((event, index) => (
            <div className="event-item" key={`${event.type}-${index}`}>
              <strong>{event.type}</strong>
              <span>
                {event.text ??
                  event.summary ??
                  event.action ??
                  event.stage ??
                  event.message ??
                  (event.bytes ? `${event.bytes} bytes` : "")}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
