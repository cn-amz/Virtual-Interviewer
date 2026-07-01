type SetupPageProps = {
  onStart: () => void;
  onBack: () => void;
};

export function SetupPage({ onStart, onBack }: SetupPageProps) {
  return (
    <section className="panel">
      <p className="eyebrow">Interview Setup</p>
      <h1>机械臂运控算法工程师模拟面试</h1>
      <p>候选人：豆瓣酱。目标岗位：机械臂运控算法工程师。</p>
      <div className="button-row">
        <button className="primary-button" onClick={onStart}>
          开始模拟面试
        </button>
        <button className="secondary-button" onClick={onBack}>
          返回工作台
        </button>
      </div>
    </section>
  );
}
