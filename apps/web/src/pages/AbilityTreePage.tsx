type AbilityTreePageProps = {
  onBack: () => void;
};

export function AbilityTreePage({ onBack }: AbilityTreePageProps) {
  return (
    <section className="panel">
      <p className="eyebrow">Ability Tree</p>
      <h1>能力树</h1>
      <p>
        能力树功能正在第二阶段建设中。完成模拟面试后，系统会逐步沉淀成长枝、薄弱枝和目标岗位需要补齐的虚拟树枝。
      </p>
      <button className="secondary-button" onClick={onBack}>
        返回工作台
      </button>
    </section>
  );
}
