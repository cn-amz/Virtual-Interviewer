import { useEffect, useState } from "react";
import { listInterviewHistory, type MockReportResponse } from "../api/client";

type HistoryPageProps = {
  onBack: () => void;
  onOpenReport: (interviewId: string) => void;
};

function formatDate(value?: string): string {
  if (!value) return "时间未知";
  return new Date(value).toLocaleString("zh-CN");
}

export function HistoryPage({ onBack, onOpenReport }: HistoryPageProps) {
  const [reports, setReports] = useState<MockReportResponse[]>([]);
  const [error, setError] = useState<string>();

  useEffect(() => {
    listInterviewHistory()
      .then(setReports)
      .catch((loadError: unknown) => {
        setError(loadError instanceof Error ? loadError.message : "历史报告加载失败。");
      });
  }, []);

  return (
    <section className="panel history-panel">
      <div className="dashboard-header">
        <div>
          <p className="eyebrow">训练记录</p>
          <h1>历史报告</h1>
          <p>只展示包含有效问答证据的面试复盘，测试空记录不会出现在这里。</p>
        </div>
        <button className="secondary-button" onClick={onBack}>返回工作台</button>
      </div>
      {error && <p className="resume-error">{error}</p>}
      {!error && reports.length === 0 && <p className="resume-empty">暂无历史报告。</p>}
      <div className="history-list">
        {reports.map((item) => (
          <button className="history-item" key={item.interview_id} onClick={() => onOpenReport(item.interview_id)}>
            <span>
              <strong>{item.report.summary}</strong>
              <small>{formatDate(item.created_at)} · {item.interview_id}</small>
            </span>
            <b>{item.report.score.average} 分</b>
          </button>
        ))}
      </div>
    </section>
  );
}
