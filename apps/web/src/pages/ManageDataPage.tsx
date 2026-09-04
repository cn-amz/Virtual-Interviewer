import { useEffect, useState } from "react";
import {
  analyzeJobDescription,
  createJobDescriptionFromText,
  jobDescriptionUrl,
  listJobDescriptions,
  listProfiles,
  listResumes,
  resumeUrl,
  uploadJobDescription,
  uploadResume,
  type JobDescriptionDocument,
  type JobDescriptionAnalysis,
  type ResumeDocument,
} from "../api/client";

type ManageDataPageProps = {
  onBack: () => void;
};

type ManagedProfile = {
  profileId: string;
  resumes: ResumeDocument[];
};

function formatSize(size: number): string {
  return `${Math.max(1, Math.round(size / 1024))} KB`;
}

export function ManageDataPage({ onBack }: ManageDataPageProps) {
  const [profiles, setProfiles] = useState<ManagedProfile[]>([]);
  const [jobDescriptions, setJobDescriptions] = useState<JobDescriptionDocument[]>([]);
  const [profileId, setProfileId] = useState("豆瓣酱");
  const [resumeFile, setResumeFile] = useState<File>();
  const [jobDescriptionFile, setJobDescriptionFile] = useState<File>();
  const [jobDescriptionTitle, setJobDescriptionTitle] = useState("");
  const [jobDescriptionText, setJobDescriptionText] = useState("");
  const [selectedAnalysis, setSelectedAnalysis] = useState<JobDescriptionAnalysis>();
  const [analyzingJdId, setAnalyzingJdId] = useState<string>();
  const [message, setMessage] = useState<string>();
  const [error, setError] = useState<string>();

  async function refresh() {
    const [{ profiles: profileIds }, descriptions] = await Promise.all([
      listProfiles(),
      listJobDescriptions(),
    ]);
    const profileData = await Promise.all(
      profileIds.map(async (id) => ({ profileId: id, resumes: await listResumes(id) }))
    );
    setProfiles(profileData);
    setJobDescriptions(descriptions);
  }

  useEffect(() => {
    refresh().catch((loadError: unknown) => {
      setError(loadError instanceof Error ? loadError.message : "管理数据加载失败。");
    });
  }, []);

  async function handleResumeUpload() {
    if (!profileId.trim() || !resumeFile) return;
    setError(undefined);
    setMessage(undefined);
    try {
      await uploadResume(profileId.trim(), resumeFile);
      setMessage(`已添加 ${profileId.trim()} 的简历。`);
      setResumeFile(undefined);
      await refresh();
    } catch (uploadError: unknown) {
      setError(uploadError instanceof Error ? uploadError.message : "简历上传失败。");
    }
  }

  async function handleJobDescriptionUpload() {
    if (!jobDescriptionFile) return;
    setError(undefined);
    setMessage(undefined);
    try {
      await uploadJobDescription(jobDescriptionFile);
      setMessage(`已添加岗位 JD：${jobDescriptionFile.name}`);
      setJobDescriptionFile(undefined);
      await refresh();
    } catch (uploadError: unknown) {
      setError(uploadError instanceof Error ? uploadError.message : "岗位 JD 上传失败。");
    }
  }

  async function handleJobDescriptionPaste() {
    if (!jobDescriptionText.trim()) return;
    setError(undefined);
    setMessage(undefined);
    try {
      const document = await createJobDescriptionFromText(jobDescriptionTitle, jobDescriptionText);
      setMessage(`已保存岗位 JD：${document.title}`);
      setJobDescriptionTitle("");
      setJobDescriptionText("");
      await refresh();
    } catch (saveError: unknown) {
      setError(saveError instanceof Error ? saveError.message : "岗位 JD 保存失败。");
    }
  }

  async function handleJobDescriptionAnalysis(jdId: string) {
    setError(undefined);
    setMessage(undefined);
    setAnalyzingJdId(jdId);
    try {
      const analysis = await analyzeJobDescription(jdId);
      setSelectedAnalysis(analysis);
      setMessage(`已生成“${analysis.role_direction}”面试关注点。`);
      await refresh();
    } catch (analysisError: unknown) {
      setError(analysisError instanceof Error ? analysisError.message : "岗位方向分析失败。");
    } finally {
      setAnalyzingJdId(undefined);
    }
  }

  return (
    <section className="panel manage-panel">
      <div className="dashboard-header">
        <div>
          <p className="eyebrow">资料管理</p>
          <h1>简历与岗位 JD</h1>
          <p>集中查看和添加面试资料。上传后不会自动改变当前面试上下文。</p>
        </div>
        <button className="secondary-button" onClick={onBack}>返回工作台</button>
      </div>

      {message && <p className="manage-message">{message}</p>}
      {error && <p className="resume-error">{error}</p>}

      <div className="manage-grid">
        <section className="manage-section">
          <h2>所有简历</h2>
          {profiles.map((profile) => (
            <div className="manage-group" key={profile.profileId}>
              <h3>{profile.profileId}</h3>
              {profile.resumes.length === 0 && <p className="resume-empty">暂无简历文件。</p>}
              {profile.resumes.map((resume) => (
                <div className="resume-item" key={`${profile.profileId}-${resume.name}`}>
                  <div>
                    <strong>{resume.name}</strong>
                    <span>{resume.format.toUpperCase()} · {formatSize(resume.size)}</span>
                  </div>
                  <button
                    className="secondary-button"
                    onClick={() => window.open(resumeUrl(profile.profileId, resume.name), "_blank", "noopener,noreferrer")}
                  >查看</button>
                </div>
              ))}
            </div>
          ))}
          <div className="manage-form">
            <label>
              候选人名称
              <input value={profileId} onChange={(event) => setProfileId(event.target.value)} />
            </label>
            <label>
              选择简历文件
              <input type="file" accept=".pdf,.doc,.docx" onChange={(event) => setResumeFile(event.target.files?.[0])} />
            </label>
            <button className="primary-button" disabled={!profileId.trim() || !resumeFile} onClick={handleResumeUpload}>
              添加简历
            </button>
          </div>
        </section>

        <section className="manage-section">
          <h2>所有岗位 JD</h2>
          {jobDescriptions.map((jobDescription) => (
            <div className="resume-item" key={jobDescription.jd_id}>
              <div>
                <strong>{jobDescription.title}</strong>
                <span>{jobDescription.name} · {formatSize(jobDescription.size)}{jobDescription.analysis_ready ? " · 已有面试重点" : ""}</span>
              </div>
              <div className="button-row button-row--compact">
                <button
                  className="secondary-button"
                  onClick={() => window.open(jobDescriptionUrl(jobDescription.jd_id), "_blank", "noopener,noreferrer")}
                >查看</button>
                <button
                  className="secondary-button"
                  disabled={analyzingJdId === jobDescription.jd_id}
                  onClick={() => void handleJobDescriptionAnalysis(jobDescription.jd_id)}
                >{analyzingJdId === jobDescription.jd_id ? "分析中..." : "AI 分析面试重点"}</button>
              </div>
            </div>
          ))}
          {selectedAnalysis && (
            <article className="jd-analysis">
              <p className="eyebrow">岗位分析结果</p>
              <h3>{selectedAnalysis.title}</h3>
              <p><strong>岗位族：</strong>{selectedAnalysis.role_family}</p>
              <p><strong>实际方向：</strong>{selectedAnalysis.role_direction}</p>
              <h4>面试关注点</h4>
              <ul>{selectedAnalysis.focus_points.map((point) => <li key={point}>{point}</li>)}</ul>
              <h4>初始面试官 Prompt</h4>
              <pre>{selectedAnalysis.initial_prompt}</pre>
              <h4>参考岗位样本</h4>
              <ul>
                {selectedAnalysis.research_sources.map((source) => (
                  <li key={source.url}>
                    <a href={source.url} target="_blank" rel="noreferrer">{source.title}</a>
                  </li>
                ))}
              </ul>
              <small>分析模式：{selectedAnalysis.analysis_mode === "bailian_text" ? "百炼文本模型" : "本地降级规则"}</small>
            </article>
          )}
          <div className="manage-form">
            <label>
              岗位名称（可选）
              <input
                value={jobDescriptionTitle}
                onChange={(event) => setJobDescriptionTitle(event.target.value)}
                placeholder="例如：机械臂运控算法工程师"
              />
            </label>
            <label>
              粘贴岗位 JD
              <textarea
                value={jobDescriptionText}
                onChange={(event) => setJobDescriptionText(event.target.value)}
                placeholder="将岗位职责、任职要求等内容粘贴到这里"
              />
            </label>
            <button className="primary-button" disabled={!jobDescriptionText.trim()} onClick={() => void handleJobDescriptionPaste()}>
              保存为 Markdown JD
            </button>
            <div className="manage-divider">或上传已有 Markdown 文件</div>
            <label>
              选择 Markdown JD
              <input type="file" accept=".md" onChange={(event) => setJobDescriptionFile(event.target.files?.[0])} />
            </label>
            <button className="primary-button" disabled={!jobDescriptionFile} onClick={handleJobDescriptionUpload}>
              添加岗位 JD
            </button>
          </div>
        </section>
      </div>
    </section>
  );
}
