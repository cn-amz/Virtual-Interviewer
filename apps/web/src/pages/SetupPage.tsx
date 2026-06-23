type SetupPageProps = {
  onStart: () => void;
};

export function SetupPage({ onStart }: SetupPageProps) {
  return (
    <section className="panel">
      <p className="eyebrow">MVP Setup</p>
      <h1>机械臂运控算法工程师模拟面试</h1>
      <p>候选人：豆瓣酱。目标岗位：机械臂运控算法工程师。</p>
      <button className="primary-button" onClick={onStart}>
        开始模拟面试
      </button>
    </section>
  );
}
