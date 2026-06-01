import { FormEvent, useEffect, useState } from "react";
import { ArrowRight, Loader2, Plus, RefreshCw, WandSparkles } from "lucide-react";
import type { ApiClient, ProjectSummary } from "../api/client";

type ProjectHubProps = {
  api: ApiClient;
  onOpenProject: (projectId: string) => void;
};

export function ProjectHub({ api, onOpenProject }: ProjectHubProps) {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [projectId, setProjectId] = useState("");
  const [title, setTitle] = useState("");
  const [idea, setIdea] = useState("");
  const [assistantNotes, setAssistantNotes] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadProjects() {
    setLoading(true);
    setError(null);
    try {
      setProjects(await api.listProjects());
    } catch (err) {
      setError(err instanceof Error ? err.message : "项目加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadProjects();
  }, []);

  async function handleCreateProject(event: FormEvent) {
    event.preventDefault();
    if (!projectId.trim()) {
      setError("请输入项目 ID");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const created = await api.createProject({
        project_id: projectId.trim(),
        title: title.trim() || null,
      });
      await loadProjects();
      onOpenProject(created.project_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "项目创建失败");
    } finally {
      setSaving(false);
    }
  }

  function handleIdea() {
    const cleanIdea = idea.trim();
    if (!cleanIdea) {
      return;
    }
    setAssistantNotes((notes) => [
      `创意：${cleanIdea}`,
      "下一步：创建项目后用 Workflow 生成蓝图与章节。",
      ...notes,
    ]);
    setIdea("");
  }

  return (
    <section className="page page-hub">
      <header className="page-header">
        <div>
          <p className="eyebrow">创作项目</p>
          <h1>小说工作台</h1>
        </div>
        <button className="icon-button" onClick={loadProjects} title="刷新项目">
          {loading ? <Loader2 className="spin" size={18} /> : <RefreshCw size={18} />}
        </button>
      </header>

      {error ? <div className="alert error">{error}</div> : null}

      <div className="hub-grid">
        <section className="panel">
          <div className="panel-header">
            <h2>项目</h2>
            <span>{projects.length} 个</span>
          </div>
          <form className="create-project" onSubmit={handleCreateProject}>
            <label>
              <span>项目 ID</span>
              <input
                value={projectId}
                onChange={(event) => setProjectId(event.target.value)}
                placeholder="novel-demo"
              />
            </label>
            <label>
              <span>标题</span>
              <input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="雨夜来信"
              />
            </label>
            <button className="primary-button" disabled={saving}>
              {saving ? <Loader2 className="spin" size={17} /> : <Plus size={17} />}
              <span>新建</span>
            </button>
          </form>

          <div className="project-list">
            {loading ? <div className="empty-state">加载中</div> : null}
            {!loading && projects.length === 0 ? (
              <div className="empty-state">暂无项目</div>
            ) : null}
            {projects.map((project) => (
              <button
                className="project-row"
                key={project.project_id}
                onClick={() => onOpenProject(project.project_id)}
              >
                <div>
                  <strong>{project.title || project.project_id}</strong>
                  <span>{project.project_id}</span>
                </div>
                <div className="row-meta">
                  <span>{project.chapter_count} 章</span>
                  <span>{project.has_outline ? "有大纲" : "未生成大纲"}</span>
                  <ArrowRight size={16} />
                </div>
              </button>
            ))}
          </div>
        </section>

        <section className="panel assistant-panel">
          <div className="panel-header">
            <h2>灵感</h2>
            <WandSparkles size={18} />
          </div>
          <textarea
            value={idea}
            onChange={(event) => setIdea(event.target.value)}
            placeholder="写下题材、主角、冲突或一句灵感"
          />
          <button className="secondary-button" onClick={handleIdea}>
            <WandSparkles size={17} />
            <span>整理</span>
          </button>
          <div className="note-stack">
            {assistantNotes.length === 0 ? (
              <div className="empty-state">灵感会保留在这里</div>
            ) : null}
            {assistantNotes.map((note, index) => (
              <p key={`${note}-${index}`}>{note}</p>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}
