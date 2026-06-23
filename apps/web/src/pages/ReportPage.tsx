import { useEffect, useState } from "react";
import { createMockReport, type MockReportResponse } from "../api/client";

type ReportState = MockReportResponse | { error: string } | null;

export function ReportPage() {
  const [report, setReport] = useState<ReportState>(null);

  useEffect(() => {
    createMockReport().then(setReport).catch((error) => {
      setReport({ error: String(error) });
    });
  }, []);

  if (!report) {
    return <section className="panel">报告生成中...</section>;
  }

  if ("error" in report) {
    return <section className="panel">报告生成失败：{report.error}</section>;
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
    </section>
  );
}
