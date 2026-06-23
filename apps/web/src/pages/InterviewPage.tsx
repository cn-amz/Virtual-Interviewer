import { useState } from "react";
import { useInterviewSession } from "../realtime/useInterviewSession";

type InterviewPageProps = {
  onFinish: () => void;
};

export function InterviewPage({ onFinish }: InterviewPageProps) {
  const { connected, events, start, sendText, end } = useInterviewSession();
  const [answer, setAnswer] = useState("我通过ROS2完成机械臂运动控制，并引入插值算法提升稳定性。");

  return (
    <section className="interview-grid">
      <div className="panel">
        <p className="eyebrow">Realtime Interview</p>
        <h1>虚拟面试官</h1>
        <p>连接状态：{connected ? "已连接" : "未连接"}</p>
        <div className="button-row">
          <button className="primary-button" onClick={start}>连接面试官</button>
          <button className="secondary-button" onClick={() => sendText(answer)}>发送模拟回答</button>
          <button className="secondary-button" onClick={() => { end(); onFinish(); }}>结束并生成报告</button>
        </div>
        <textarea value={answer} onChange={(event) => setAnswer(event.target.value)} />
      </div>
      <div className="panel">
        <h2>事件流</h2>
        <div className="event-list">
          {events.map((event, index) => (
            <div className="event-item" key={`${event.type}-${index}`}>
              <strong>{event.type}</strong>
              <span>{event.text || event.summary || event.action || event.stage}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
