import { useEffect, useState } from "react";
import {
  analyzeInterview,
  createMockReport,
  type MockReportResponse,
} from "../api/client";

type ReportPageProps = {
  onBack: () => void;
  interviewId?: string;
};

type ReportState = MockReportResponse | { error: string } | null;

export function ReportPage({ onBack, interviewId }: ReportPageProps) {
  const [report, setReport] = useState<ReportState>(null);

  useEffect(() => {
    (interviewId ? analyzeInterview(interviewId) : createMockReport())
      .then(setReport)
      .catch((error) => {
        setReport({ error: String(error) });
      });
  }, [interviewId]);

  if (!report) {
    return (
      <section className="panel">
        <p>报告生成中...</p>
      </section>
    );
  }

  if ("error" in report) {
    return (
      <section className="panel">
        <p>报告生成失败：{report.error}</p>
        <button className="secondary-button" onClick={onBack}>
          返回工作台
        </button>
      </section>
    );
  }

  return (
    <section className="panel">
      <p className="eyebrow">面试后复盘</p>
      <h1>能力树复盘</h1>
      <p>{report.report.summary}</p>
      {report.report.analysis_mode && (
        <p className="report-meta">分析方式：{report.report.analysis_mode}</p>
      )}
      <h2>平均分：{report.report.score.average}</h2>
      {report.report.strengths && report.report.strengths.length > 0 && (
        <>
          <h2>表现较好的地方</h2>
          <ul>{report.report.strengths.map((item) => <li key={item}>{item}</li>)}</ul>
        </>
      )}
      {report.report.transcript && report.report.transcript.length > 0 && (
        <>
          <h2>完整面试文本</h2>
          <div className="report-transcript">
            {report.report.transcript.map((item, index) => (
              <p key={`${item.speaker}-${index}`}>
                <strong>{item.speaker === "assistant" ? "面试官" : "候选人"}：</strong>
                {item.text}
              </p>
            ))}
          </div>
        </>
      )}
      <h2>成长树枝</h2>
      <ul>
        {report.ability_tree.skills.map((skill: string) => (
          <li key={skill}>{skill}</li>
        ))}
      </ul>
      <h2>虚拟树枝</h2>
      <ul>
        {report.ability_tree.target_skills.map((skill: string) => (
          <li key={skill}>{skill}</li>
        ))}
      </ul>
      <button className="secondary-button" onClick={onBack}>
        返回工作台
      </button>
    </section>
  );
}
