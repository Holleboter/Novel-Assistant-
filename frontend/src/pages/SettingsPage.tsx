import { useEffect, useState } from "react";
import { KeyRound, Loader2, RefreshCw } from "lucide-react";
import type { ApiClient, LLMProfileSummary, SkillSummary } from "../api/client";

type SettingsPageProps = {
  api: ApiClient;
};

export function SettingsPage({ api }: SettingsPageProps) {
  const [profiles, setProfiles] = useState<LLMProfileSummary[]>([]);
  const [skills, setSkills] = useState<SkillSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadSettings() {
    setLoading(true);
    setError(null);
    try {
      const [profileList, skillList] = await Promise.all([
        api.listLLMProfiles(),
        api.listSkills(),
      ]);
      setProfiles(profileList);
      setSkills(skillList);
    } catch (err) {
      setError(err instanceof Error ? err.message : "设置加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadSettings();
  }, []);

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">运行配置</p>
          <h1>设置</h1>
        </div>
        <button className="icon-button" onClick={loadSettings} title="刷新设置">
          {loading ? <Loader2 className="spin" size={18} /> : <RefreshCw size={18} />}
        </button>
      </header>
      {error ? <div className="alert error">{error}</div> : null}
      <div className="settings-grid">
        <section className="panel">
          <div className="panel-header">
            <h2>LLM</h2>
            <KeyRound size={18} />
          </div>
          <div className="list-stack">
            {profiles.length === 0 ? <div className="empty-state">暂无模型配置</div> : null}
            {profiles.map((profile) => (
              <div className="config-row" key={profile.id}>
                <div>
                  <strong>{profile.name}</strong>
                  <span>{profile.provider} / {profile.model}</span>
                </div>
                <span className={profile.api_key_set ? "pill success" : "pill muted"}>
                  {profile.api_key_set ? "已配置 Key" : "未配置 Key"}
                </span>
              </div>
            ))}
          </div>
        </section>
        <section className="panel">
          <div className="panel-header">
            <h2>Skill</h2>
            <span>{skills.length} 个</span>
          </div>
          <div className="list-stack">
            {skills.length === 0 ? <div className="empty-state">暂无 Skill</div> : null}
            {skills.map((skill) => (
              <div className="config-row" key={skill.id}>
                <div>
                  <strong>{skill.name}</strong>
                  <span>{skill.description || skill.id}</span>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}
