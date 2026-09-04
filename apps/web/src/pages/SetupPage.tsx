import { useEffect, useState } from "react";
import {
  jobDescriptionUrl,
  getProviderStatus,
  listJobDescriptions,
  listProfiles,
  listResumes,
  resumeUrl,
  type JobDescriptionDocument,
  type ProviderStatus,
  type ResumeDocument,
} from "../api/client";
import { isProviderReady, type InterviewSessionSelection } from "../realtime/useInterviewSession";

type SetupPageProps = {
  onStart: (selection: InterviewSessionSelection) => void;
  onBack: () => void;
  initialProfileId?: string;
};

function formatSize(size: number): string {
  return `${Math.max(1, Math.round(size / 1024))} KB`;
}

export function SetupPage({ onStart, onBack, initialProfileId }: SetupPageProps) {
  const [profiles, setProfiles] = useState<string[]>([]);
  const [profileId, setProfileId] = useState(initialProfileId ?? "");
  const [provider, setProvider] = useState<InterviewSessionSelection["provider"]>("bailian");
  const [audioMode, setAudioMode] = useState<InterviewSessionSelection["audioMode"]>("full_duplex");
  const [providerStatus, setProviderStatus] = useState<ProviderStatus>();
  const [resumes, setResumes] = useState<ResumeDocument[]>([]);
  const [resumeName, setResumeName] = useState("");
  const [resumeError, setResumeError] = useState<string>();
  const [jobDescriptions, setJobDescriptions] = useState<JobDescriptionDocument[]>([]);
  const [jdId, setJdId] = useState("");
  const [jobDescriptionError, setJobDescriptionError] = useState<string>();

  useEffect(() => {
    let active = true;
    void listProfiles()
      .then(({ profiles: items }) => {
        if (!active) return;
        setProfiles(items);
        setProfileId((current) => (items.includes(current) ? current : items[0] ?? ""));
      })
      .catch((error: unknown) => {
        if (active) setResumeError(error instanceof Error ? error.message : "候选人列表加载失败。");
      });
    void listJobDescriptions()
      .then((items) => {
        if (!active) return;
        setJobDescriptions(items);
        setJdId((current) => (items.some((item) => item.jd_id === current) ? current : items[0]?.jd_id ?? ""));
      })
      .catch((error: unknown) => {
        if (active) setJobDescriptionError(error instanceof Error ? error.message : "岗位 JD 列表加载失败。");
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!profileId) {
      setResumes([]);
      setResumeName("");
      return;
    }
    let active = true;
    setResumeError(undefined);
    void listResumes(profileId)
      .then((items) => {
        if (!active) return;
        setResumes(items);
        setResumeName((current) => (items.some((item) => item.name === current) ? current : items[0]?.name ?? ""));
      })
      .catch((error: unknown) => {
        if (active) setResumeError(error instanceof Error ? error.message : "简历列表加载失败。");
      });
    return () => {
      active = false;
    };
  }, [profileId]);

  useEffect(() => {
    let active = true;
    setProviderStatus(undefined);
    const refresh = () => {
      void getProviderStatus(provider)
        .then((status) => {
          if (active) setProviderStatus(status);
        })
        .catch(() => {
          if (active) {
            setProviderStatus({ provider, state: "offline", detail: "状态服务不可用", queue_length: 0 });
          }
        });
    };
    refresh();
    const timer = window.setInterval(refresh, 3000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [provider]);

  const selectedResume = resumes.find((resume) => resume.name === resumeName);
  const selectedJobDescription = jobDescriptions.find((item) => item.jd_id === jdId);
  const canStart = Boolean(profileId && resumeName && jdId && isProviderReady(providerStatus?.state));

  return (
    <section className="panel">
      <p className="eyebrow">面试设置</p>
      <h1>模拟面试配置</h1>
      <div className="setup-fields">
        <fieldset className="provider-picker">
          <legend>面试引擎</legend>
          <button className={provider === "bailian" ? "mode-button is-selected" : "mode-button"} type="button" aria-pressed={provider === "bailian"} onClick={() => setProvider("bailian")}>百炼 API</button>
          <button className={provider === "minicpm" ? "mode-button is-selected" : "mode-button"} type="button" aria-pressed={provider === "minicpm"} onClick={() => setProvider("minicpm")}>MiniCPM 本地</button>
        </fieldset>
        <label className="setup-field">
          候选人
          <select value={profileId} onChange={(event) => setProfileId(event.target.value)}>
            <option value="">选择候选人</option>
            {profiles.map((profile) => <option key={profile} value={profile}>{profile}</option>)}
          </select>
        </label>
        <label className="setup-field setup-field--checkbox">
          <input
            type="checkbox"
            checked={audioMode === "playback_gate"}
            onChange={(event) => setAudioMode(event.target.checked ? "playback_gate" : "full_duplex")}
          />
          模型说话时暂停上传麦克风
        </label>
        <label className="setup-field">
          简历版本
          <select value={resumeName} onChange={(event) => setResumeName(event.target.value)} disabled={!profileId}>
            <option value="">选择简历</option>
            {resumes.map((resume) => <option key={resume.name} value={resume.name}>{resume.name}</option>)}
          </select>
        </label>
        <label className="setup-field">
          目标岗位
          <select value={jdId} onChange={(event) => setJdId(event.target.value)}>
            <option value="">选择岗位 JD</option>
            {jobDescriptions.map((item) => <option key={item.jd_id} value={item.jd_id}>{item.title}</option>)}
          </select>
        </label>
      </div>

      {provider === "minicpm" && <p className="setup-warning">MiniCPM 会在会话开始时注入压缩后的岗位、简历摘要和面试规则；完整简历上下文与严格遵循能力仍弱于百炼 API。</p>}
      <p className="mic-status mic-status--hint">
        引擎状态：{providerStatus?.detail ?? "正在检查..."}
        {providerStatus?.queue_length ? `（队列 ${providerStatus.queue_length}）` : ""}
      </p>
      {resumeError && <p className="resume-error">{resumeError}</p>}
      {jobDescriptionError && <p className="resume-error">{jobDescriptionError}</p>}

      <section className="resume-section" aria-labelledby="selection-heading">
        <div className="section-heading"><h2 id="selection-heading">本次上下文</h2></div>
        {selectedResume && (
          <div className="resume-item">
            <div><strong>{selectedResume.name}</strong><span>{selectedResume.format.toUpperCase()} · {formatSize(selectedResume.size)}</span></div>
            <button className="secondary-button" type="button" onClick={() => window.open(resumeUrl(profileId, selectedResume.name), "_blank", "noopener,noreferrer")}>查看简历</button>
          </div>
        )}
        {selectedJobDescription && (
          <div className="resume-item">
            <div><strong>{selectedJobDescription.title}</strong><span>Markdown · {formatSize(selectedJobDescription.size)}</span></div>
            <button className="secondary-button" type="button" onClick={() => window.open(jobDescriptionUrl(selectedJobDescription.jd_id), "_blank", "noopener,noreferrer")}>查看 JD</button>
          </div>
        )}
      </section>
      <div className="button-row">
        <button className="primary-button" disabled={!canStart} onClick={() => onStart({ provider, audioMode, profileId, resumeName, jdId })}>开始模拟面试</button>
        <button className="secondary-button" onClick={onBack}>返回工作台</button>
      </div>
    </section>
  );
}
