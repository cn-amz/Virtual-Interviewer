import { useEffect, useMemo, useState } from "react";
import {
  abilityTreeMarkdownUrl,
  getAuthHeaders,
  getAbilityTree,
  organizeAbilityTree,
  type AbilityEvidence,
  type AbilityQuestionGroup,
  type AbilityTree,
} from "../api/client";

type AbilityTreePageProps = {
  userId: string;
  onBack: () => void;
  onOpenReport: (interviewId: string) => void;
};

type SelectedNode =
  | { type: "root" }
  | { type: "branch"; name: string }
  | { type: "question"; group: AbilityQuestionGroup }
  | { type: "evidence"; evidence: AbilityEvidence }
  | { type: "target"; name: string };

export function AbilityTreePage({ userId, onBack, onOpenReport }: AbilityTreePageProps) {
  const [tree, setTree] = useState<AbilityTree>();
  const [selection, setSelection] = useState<SelectedNode>({ type: "root" });
  const [error, setError] = useState<string>();
  const [organizing, setOrganizing] = useState(false);
  const [obsidianMessage, setObsidianMessage] = useState<string>();

  useEffect(() => {
    getAbilityTree(userId)
      .then(setTree)
      .catch((loadError: unknown) => {
        setError(loadError instanceof Error ? loadError.message : "能力树加载失败。");
      });
  }, [userId]);

  const evidence = tree?.evidence_details ?? [];
  const evidenceById = useMemo(
    () => new Map(evidence.map((item) => [item.evidence_id, item])),
    [evidence]
  );
  const questionGroups = tree?.question_groups ?? [];
  const questionById = useMemo(
    () => new Map(questionGroups.map((item) => [item.question_id, item])),
    [questionGroups]
  );
  const branches = tree?.type_branches ?? [];

  async function openMarkdown() {
    const response = await fetch(abilityTreeMarkdownUrl(userId), {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      setError("能力树 Markdown 打开失败。");
      return;
    }
    const blobUrl = URL.createObjectURL(await response.blob());
    window.open(blobUrl, "_blank", "noopener,noreferrer");
    window.setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
  }

  async function organize() {
    setOrganizing(true);
    setError(undefined);
    try {
      setTree(await organizeAbilityTree(userId));
      setSelection({ type: "root" });
    } catch (organizeError: unknown) {
      setError(organizeError instanceof Error ? organizeError.message : "能力树整理失败。");
    } finally {
      setOrganizing(false);
    }
  }

  async function copyMarkdownPath() {
    if (!tree?.markdown_path) return;
    try {
      await navigator.clipboard.writeText(tree.markdown_path);
      setObsidianMessage("Markdown 路径已复制，可粘贴到 Obsidian 的打开文件窗口。");
    } catch {
      setObsidianMessage(`请手动复制路径：${tree.markdown_path}`);
    }
  }

  function openObsidian() {
    if (!tree?.obsidian_uri) return;
    setObsidianMessage("正在尝试打开 Obsidian；若没有反应，请复制下方路径。");
    window.location.assign(tree.obsidian_uri);
  }

  function renderDetail() {
    if (!tree) return null;
    if (selection.type === "evidence") {
      const item = selection.evidence;
      return (
        <div className="ability-detail">
          <p className="eyebrow">面试证据</p>
          <h2>{item.skill}</h2>
          <div className="ability-detail__quote">
            <strong>问题</strong>
            <p>{item.question || "历史记录没有保存问题文本。"}</p>
          </div>
          <div className="ability-detail__quote">
            <strong>回答</strong>
            <p>{item.answer || "历史记录没有保存回答文本。"}</p>
          </div>
          <h3>相关知识点</h3>
          <ul className="knowledge-point-list">
            {item.knowledge_points.map((point) => (
              <li key={point.title}>
                <strong>{point.title}</strong>
                {point.summary && <span>{point.summary}</span>}
                {point.obsidian_ref && <small>Obsidian：{point.obsidian_ref}</small>}
              </li>
            ))}
          </ul>
          {item.interview_id && (
            <button className="secondary-button" onClick={() => onOpenReport(item.interview_id)}>
              打开本次面试报告
            </button>
          )}
        </div>
      );
    }
    if (selection.type === "question") {
      const group = selection.group;
      return (
        <div className="ability-detail">
          <p className="eyebrow">合并问题</p>
          <h2>{group.canonical_question}</h2>
          <p>类型：{group.types.join("、")}；已合并 {group.evidence_ids.length} 次回答。</p>
          <div className="ability-detail__quote">
            <strong>相关技能</strong>
            <p>{group.skills.join("、") || "未分类"}</p>
          </div>
          <h3>回答证据</h3>
          <div className="ability-tree-children">
            {group.evidence_ids.map((evidenceId) => {
              const item = evidenceById.get(evidenceId);
              if (!item) return null;
              return (
                <button
                  className="ability-tree-node ability-tree-node--evidence"
                  key={item.evidence_id}
                  onClick={() => setSelection({ type: "evidence", evidence: item })}
                >
                  {item.answer || "查看回答证据"}
                </button>
              );
            })}
          </div>
        </div>
      );
    }
    if (selection.type === "branch") {
      const branch = branches.find((item) => item.type === selection.name);
      return (
        <div className="ability-detail">
          <p className="eyebrow">类型主干</p>
          <h2>{selection.name}</h2>
          <p>该类型下有 {branch?.question_ids.length ?? 0} 个合并问题，点击问题查看所有回答。</p>
        </div>
      );
    }
    if (selection.type === "target") {
      return (
        <div className="ability-detail">
          <p className="eyebrow">待提升虚拟树枝</p>
          <h2>{selection.name}</h2>
          <p>这个节点来自历史面试短板，需要在后续回答中补充可验证的知识和项目证据。</p>
        </div>
      );
    }
    return (
      <div className="ability-detail">
        <p className="eyebrow">能力树根节点</p>
        <h2>{userId} 的面试能力图谱</h2>
        <p>类型主干 → 合并问题 → 多次回答 → 相关知识点。</p>
        <p>类型 {branches.length} 项，合并问题 {questionGroups.length} 项，面试证据 {evidence.length} 条。</p>
        {tree.organization_mode === "deterministic_fallback" && (
          <p className="ability-tree-meta">当前使用本地整理结果；点击“AI 整理问题”可合并语义相近的问题。</p>
        )}
      </div>
    );
  }

  return (
    <section className="panel ability-tree-panel">
      <div className="dashboard-header">
        <div>
          <p className="eyebrow">能力成长树</p>
          <h1>我的能力树</h1>
          <p>类型主干 → 具体问题 → 多次回答 → 相关知识点。</p>
        </div>
        <div className="button-row">
          <button className="secondary-button" onClick={() => void organize()} disabled={organizing}>
            {organizing ? "AI 整理中..." : "AI 整理问题"}
          </button>
          <button className="secondary-button" onClick={() => void openMarkdown()}>
            预览 Markdown
          </button>
          {tree?.obsidian_uri && (
            <button className="secondary-button" onClick={openObsidian}>
              跳转 Obsidian
            </button>
          )}
          <button className="secondary-button" onClick={onBack}>返回工作台</button>
        </div>
      </div>
      {tree?.markdown_path && (
        <div className="obsidian-path">
          <span>能力树文件：<code>{tree.markdown_path}</code></span>
          <button className="text-button" onClick={() => void copyMarkdownPath()}>复制路径</button>
          {obsidianMessage && <small>{obsidianMessage}</small>}
        </div>
      )}
      {error && <p className="resume-error">{error}</p>}
      {!error && !tree && <p>能力树加载中...</p>}
      {tree && (
        <div className="ability-tree-layout">
          <div className="ability-tree-canvas">
            <button
              className={`ability-tree-node ability-tree-node--root${selection.type === "root" ? " is-selected" : ""}`}
              onClick={() => setSelection({ type: "root" })}
            >
              {userId} 的能力根系
            </button>
            <div className="ability-tree-columns">
              <div className="ability-tree-column">
                <h2>类型主干</h2>
                {branches.map((branch) => (
                  <div className="ability-tree-branch" key={branch.type}>
                    <button
                      className={`ability-tree-node ability-tree-node--type${selection.type === "branch" && selection.name === branch.type ? " is-selected" : ""}`}
                      onClick={() => setSelection({ type: "branch", name: branch.type })}
                    >
                      {branch.type}
                    </button>
                    <div className="ability-tree-children">
                      {branch.question_ids.map((questionId) => {
                        const group = questionById.get(questionId);
                        if (!group) return null;
                        return (
                          <button
                            className={`ability-tree-node ability-tree-node--question${selection.type === "question" && selection.group.question_id === group.question_id ? " is-selected" : ""}`}
                            key={group.question_id}
                            onClick={() => setSelection({ type: "question", group })}
                          >
                            {group.canonical_question}
                            <small>{group.evidence_ids.length} 次回答</small>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
              <div className="ability-tree-column ability-tree-column--targets">
                <h2>待提升虚拟树枝</h2>
                {tree.target_skills.map((target) => (
                  <button
                    className={`ability-tree-node ability-tree-node--target${selection.type === "target" && selection.name === target ? " is-selected" : ""}`}
                    key={target}
                    onClick={() => setSelection({ type: "target", name: target })}
                  >
                    {target}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <aside className="ability-detail-panel">{renderDetail()}</aside>
        </div>
      )}
    </section>
  );
}
