import { useEffect, useState } from "react";
import { Loader2, RefreshCw, Sparkles } from "lucide-react";
import type { ApiClient, SkillSummary } from "../api/client";

type SkillsPageProps = {
  api: ApiClient;
};

export function SkillsPage({ api }: SkillsPageProps) {
  const [skills, setSkills] = useState<SkillSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadSkills() {
    setLoading(true);
    setError(null);
    try {
      setSkills(await api.listSkills());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Skills 加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadSkills();
  }, []);

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">写作能力模块</p>
          <h1>Skills</h1>
        </div>
        <button className="icon-button" onClick={loadSkills} title="刷新 Skills">
          {loading ? <Loader2 className="spin" size={18} /> : <RefreshCw size={18} />}
        </button>
      </header>
      {error ? <div className="alert error">{error}</div> : null}
      <div className="skills-grid">
        {loading ? <div className="empty-state">加载中</div> : null}
        {!loading && skills.length === 0 ? (
          <section className="panel skill-empty-panel">
            <Sparkles size={22} />
            <div>
              <h2>暂无 Skill</h2>
              <p>把写好的 `SKILL.md` 放入 Skills 目录后，这里会显示可用于润色和质检的能力。</p>
            </div>
          </section>
        ) : null}
        {skills.map((skill) => (
          <section className="panel skill-card" key={skill.id}>
            <div className="panel-header">
              <h2>{skill.name}</h2>
              <Sparkles size={18} />
            </div>
            <p>{skill.description || "暂无描述"}</p>
            <span className="pill muted">{skill.id}</span>
          </section>
        ))}
      </div>
    </section>
  );
}
