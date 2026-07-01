import { useEffect, useState } from "react";
import { createMockReport, type MockReportResponse } from "../api/client";

type ReportPageProps = {
  onBack: () => void;
};

type ReportState = MockReportResponse | { error: string } | null;

export function ReportPage({ onBack }: ReportPageProps) {
  const [report, setReport] = useState<ReportState>(null);

  useEffect(() => {
    createMockReport()
      .then(setReport)
      .catch((error) => {
        setReport({ error: String(error) });
      });
  }, []);

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
      <p className="eyebrow">Post Interview Report</p>
      <h1>能力树复盘</h1>
      <p>{report.report.summary}</p>
      <h2>平均分：{report.report.score.average}</h2>
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
