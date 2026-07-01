import { logout, type UserPublic } from "../api/client";

type DashboardTarget = "setup" | "abilityTree";

type DashboardPageProps = {
  user: UserPublic;
  onNavigate: (screen: DashboardTarget) => void;
  onLogout: () => void;
};

const cards: Array<{
  title: string;
  desc: string;
  target?: DashboardTarget;
  enabled: boolean;
}> = [
  {
    title: "开始模拟面试",
    desc: "选择简历和岗位，开始 AI 模拟面试。",
    target: "setup",
    enabled: true,
  },
  {
    title: "查看能力树",
    desc: "查看能力成长、薄弱项和目标岗位差距。",
    target: "abilityTree",
    enabled: true,
  },
  {
    title: "历史报告",
    desc: "查看过往面试记录和复盘报告，后续阶段开放。",
    enabled: false,
  },
  {
    title: "管理简历与岗位",
    desc: "编辑个人简历和目标岗位，后续阶段开放。",
    enabled: false,
  },
];

export function DashboardPage({ user, onNavigate, onLogout }: DashboardPageProps) {
  async function handleLogout() {
    await logout();
    onLogout();
  }

  return (
    <section className="panel dashboard-panel">
      <div className="dashboard-header">
        <div>
          <p className="eyebrow">Dashboard</p>
          <h1>你好，{user.display_name}</h1>
          <p>从这里选择训练路径，而不是直接进入面试。</p>
        </div>
        <button className="secondary-button" onClick={handleLogout}>
          退出登录
        </button>
      </div>
      <div className="dashboard-grid">
        {cards.map((card) => (
          <button
            key={card.title}
            className={`dashboard-card${card.enabled ? "" : " dashboard-card--disabled"}`}
            disabled={!card.enabled}
            onClick={() => card.target && card.enabled && onNavigate(card.target)}
          >
            <h2>{card.title}</h2>
            <p>{card.desc}</p>
          </button>
        ))}
      </div>
    </section>
  );
}
