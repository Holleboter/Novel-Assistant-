import { GitBranch, Milestone, Network, Rows3 } from "lucide-react";

const views = [
  { label: "人物图谱", icon: Network },
  { label: "世界图谱", icon: GitBranch },
  { label: "剧情时间线", icon: Milestone },
  { label: "章节结构", icon: Rows3 },
];

export function GraphCenter() {
  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">蓝图中心</p>
          <h1>图谱</h1>
        </div>
      </header>
      <div className="graph-center">
        <div className="graph-tabs">
          {views.map((view, index) => {
            const Icon = view.icon;
            return (
              <button className={index === 0 ? "active" : ""} key={view.label}>
                <Icon size={18} />
                <span>{view.label}</span>
              </button>
            );
          })}
        </div>
        <div className="graph-canvas">
          <div className="graph-node protagonist">主角</div>
          <div className="graph-line one" />
          <div className="graph-node faction">势力</div>
          <div className="graph-line two" />
          <div className="graph-node event">事件</div>
        </div>
        <aside className="graph-side">
          <strong>当前阶段</strong>
          <p>这里先作为图谱中心入口。下一阶段接入 Neo4j 导出数据、人物关系筛选、剧情时间线和伏笔回收表。</p>
        </aside>
      </div>
    </section>
  );
}
