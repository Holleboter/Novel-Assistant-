import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  BookOpen,
  Loader2,
  RefreshCw,
  Save,
  Sparkles,
  Users,
} from "lucide-react";
import type {
  ApiClient,
  BlueprintDocument,
  ProjectSummary,
} from "../api/client";

type BlueprintCenterProps = {
  api: ApiClient;
  projectId?: string;
  onProjectChange?: (projectId: string) => void;
  onOpenWorkbench: (projectId: string) => void;
};

type BlueprintTab = "overview" | "world" | "characters" | "outline";

const emptyBlueprint: BlueprintDocument = {
  project_id: "",
  blueprint: {
    title: "",
    logline: "",
    setting: "",
    central_conflict: "",
    themes: [],
  },
  characters: [],
  outline: [],
};

export function BlueprintCenter({
  api,
  projectId,
  onProjectChange,
  onOpenWorkbench,
}: BlueprintCenterProps) {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [activeProjectId, setActiveProjectId] = useState(projectId ?? "");
  const [document, setDocument] = useState<BlueprintDocument | null>(null);
  const [tab, setTab] = useState<BlueprintTab>("overview");
  const [idea, setIdea] = useState(
    "写一部节奏清晰、人物动机明确的类型小说。",
  );
  const [chapterCount, setChapterCount] = useState("12");
  const [loading, setLoading] = useState(false);
  const [loadFailed, setLoadFailed] = useState(false);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const activeProject = useMemo(
    () => projects.find((project) => project.project_id === activeProjectId) ?? null,
    [projects, activeProjectId],
  );
  const activeDocument = document ?? {
    ...emptyBlueprint,
    project_id: activeProjectId,
  };

  async function loadProjects() {
    try {
      const projectList = await api.listProjects();
      setProjects(projectList);
      if (!activeProjectId && projectList[0]) {
        setActiveProjectId(projectList[0].project_id);
        onProjectChange?.(projectList[0].project_id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "项目加载失败");
    }
  }

  async function loadBlueprint(id = activeProjectId) {
    if (!id) {
      setDocument(null);
      return;
    }
    setLoading(true);
    setLoadFailed(false);
    setError(null);
    try {
      setDocument(await api.getProjectBlueprint(id));
      setLoadFailed(false);
    } catch (err) {
      setDocument(null);
      setLoadFailed(true);
      setError(err instanceof Error ? err.message : "蓝图加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadProjects();
  }, []);

  useEffect(() => {
    if (projectId) {
      setActiveProjectId(projectId);
    }
  }, [projectId]);

  useEffect(() => {
    void loadBlueprint(activeProjectId);
  }, [activeProjectId]);

  function updateBlueprintField(
    field: keyof BlueprintDocument["blueprint"],
    value: string,
  ) {
    if (loadFailed) {
      setError("请先刷新或重新生成蓝图");
      return;
    }
    setError(null);
    setDocument((current) => {
      const base = current ?? { ...emptyBlueprint, project_id: activeProjectId };
      return {
        ...base,
        blueprint: {
          ...base.blueprint,
          [field]: field === "themes" ? splitTags(value) : value,
        },
      };
    });
  }

  async function handleGenerate() {
    if (!activeProjectId) {
      setError("请先选择项目");
      return;
    }
    if (!idea.trim()) {
      setError("请填写创作需求");
      return;
    }
    const normalizedChapterCount = Number(chapterCount);
    if (
      !Number.isInteger(normalizedChapterCount) ||
      normalizedChapterCount < 1 ||
      normalizedChapterCount > 200
    ) {
      setError("章节数需要是 1-200 之间的整数");
      return;
    }
    setBusy("generate");
    setError(null);
    try {
      const result = await api.generateProjectBlueprint(activeProjectId, {
        user_input: idea.trim(),
        chapter_count: normalizedChapterCount,
      });
      setDocument(result);
      setLoadFailed(false);
      setNotice("蓝图已生成");
    } catch (err) {
      setError(err instanceof Error ? err.message : "蓝图生成失败");
    } finally {
      setBusy(null);
    }
  }

  async function handleSave() {
    if (!activeProjectId || !document || loading || loadFailed) {
      return;
    }
    setBusy("save");
    setError(null);
    try {
      const result = await api.saveProjectBlueprint(activeProjectId, {
        ...document,
        project_id: activeProjectId,
      });
      setDocument(result);
      setNotice("蓝图已保存");
    } catch (err) {
      setError(err instanceof Error ? err.message : "蓝图保存失败");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="page blueprint-page">
      <header className="page-header">
        <div>
          <p className="eyebrow">小说规划</p>
          <h1>蓝图中心</h1>
        </div>
        <div className="page-actions">
          <select
            value={activeProjectId}
            onChange={(event) => {
              const nextProjectId = event.target.value;
              setDocument(null);
              setLoadFailed(false);
              setActiveProjectId(nextProjectId);
              if (nextProjectId) {
                onProjectChange?.(nextProjectId);
              }
            }}
          >
            <option value="">选择项目</option>
            {projects.map((project) => (
              <option key={project.project_id} value={project.project_id}>
                {project.title || project.project_id}
              </option>
            ))}
          </select>
          <button className="secondary-button" onClick={() => void loadBlueprint()}>
            {loading ? <Loader2 className="spin" size={17} /> : <RefreshCw size={17} />}
            <span>刷新</span>
          </button>
          <button
            className="primary-button"
            onClick={handleSave}
            disabled={
              !activeProjectId ||
              !document ||
              loading ||
              loadFailed ||
              busy === "save"
            }
          >
            {busy === "save" ? <Loader2 className="spin" size={17} /> : <Save size={17} />}
            <span>保存蓝图</span>
          </button>
        </div>
      </header>

      {error ? <div className="alert error">{error}</div> : null}
      {notice ? <div className="alert success">{notice}</div> : null}

      <div className="blueprint-layout">
        <aside className="blueprint-sidebar">
          <div className="blueprint-project-card">
            <strong>{activeProject?.title || activeProjectId || "未选择项目"}</strong>
            <span>{activeProjectId || "先在项目页创建项目"}</span>
          </div>
          <button
            className={tab === "overview" ? "blueprint-tab active" : "blueprint-tab"}
            onClick={() => setTab("overview")}
          >
            <BookOpen size={17} />
            <span>基础设定</span>
          </button>
          <button
            className={tab === "world" ? "blueprint-tab active" : "blueprint-tab"}
            onClick={() => setTab("world")}
          >
            <Sparkles size={17} />
            <span>世界观</span>
          </button>
          <button
            className={tab === "characters" ? "blueprint-tab active" : "blueprint-tab"}
            onClick={() => setTab("characters")}
          >
            <Users size={17} />
            <span>人物</span>
          </button>
          <button
            className={tab === "outline" ? "blueprint-tab active" : "blueprint-tab"}
            onClick={() => setTab("outline")}
          >
            <ArrowRight size={17} />
            <span>章节大纲</span>
          </button>
          {activeProjectId ? (
            <button
              className="secondary-button full"
              onClick={() => onOpenWorkbench(activeProjectId)}
            >
              <ArrowRight size={17} />
              <span>进入创作</span>
            </button>
          ) : null}
        </aside>

        <main className="blueprint-main">
          <section className="panel blueprint-generator">
            <div>
              <h2>生成蓝图</h2>
              <p>
                输入小说方向后生成基础设定、人物和章节大纲。基础设定可修改，人物和章节大纲本阶段先展示。
              </p>
            </div>
            <textarea value={idea} onChange={(event) => setIdea(event.target.value)} />
            <div className="generator-actions">
              <label>
                章节数
                <input
                  type="number"
                  min="1"
                  max="200"
                  step="1"
                  value={chapterCount}
                  onChange={(event) => setChapterCount(event.target.value)}
                  inputMode="numeric"
                />
              </label>
              <button
                className="primary-button"
                onClick={handleGenerate}
                disabled={busy === "generate"}
              >
                {busy === "generate" ? (
                  <Loader2 className="spin" size={17} />
                ) : (
                  <Sparkles size={17} />
                )}
                <span>生成蓝图</span>
              </button>
            </div>
          </section>

          {loadFailed ? (
            <section className="panel empty-state">
              <strong>蓝图加载失败</strong>
              <span>为避免覆盖已有大纲，请先刷新蓝图，或用上方输入重新生成。</span>
              <button className="secondary-button" onClick={() => void loadBlueprint()}>
                <RefreshCw size={17} />
                <span>重新加载</span>
              </button>
            </section>
          ) : null}

          {!loadFailed && tab === "overview" ? (
            <section className="panel blueprint-editor">
              <h2>基础设定</h2>
              <label>
                标题
                <input
                  value={activeDocument.blueprint.title}
                  onChange={(event) => updateBlueprintField("title", event.target.value)}
                />
              </label>
              <label>
                一句话卖点
                <textarea
                  value={activeDocument.blueprint.logline}
                  onChange={(event) => updateBlueprintField("logline", event.target.value)}
                />
              </label>
              <label>
                核心冲突
                <textarea
                  value={activeDocument.blueprint.central_conflict}
                  onChange={(event) =>
                    updateBlueprintField("central_conflict", event.target.value)
                  }
                />
              </label>
              <label>
                主题标签
                <input
                  value={activeDocument.blueprint.themes.join(", ")}
                  onChange={(event) => updateBlueprintField("themes", event.target.value)}
                  placeholder="成长, 悬疑, 救赎"
                />
              </label>
            </section>
          ) : null}

          {!loadFailed && tab === "world" ? (
            <section className="panel blueprint-editor">
              <h2>世界观</h2>
              <label>
                时代、地点与规则
                <textarea
                  value={activeDocument.blueprint.setting}
                  onChange={(event) => updateBlueprintField("setting", event.target.value)}
                />
              </label>
            </section>
          ) : null}

          {!loadFailed && tab === "characters" ? (
            <section className="blueprint-card-grid">
              {activeDocument.characters.length === 0 ? (
                <div className="panel empty-state">
                  暂无人物，生成蓝图后会出现人物卡。
                </div>
              ) : null}
              {activeDocument.characters.map((character) => (
                <article className="panel blueprint-card" key={character.name}>
                  <strong>{character.name}</strong>
                  <span>{character.role}</span>
                  <p>{character.motivation}</p>
                  <p>{character.arc}</p>
                  {character.traits.length ? (
                    <em>{character.traits.join(" / ")}</em>
                  ) : null}
                </article>
              ))}
            </section>
          ) : null}

          {!loadFailed && tab === "outline" ? (
            <section className="blueprint-outline">
              {activeDocument.outline.length === 0 ? (
                <div className="panel empty-state">
                  暂无章节大纲，生成蓝图后会出现章节卡。
                </div>
              ) : null}
              {activeDocument.outline.map((chapter) => (
                <article className="panel outline-card" key={chapter.chapter_number}>
                  <span>第 {chapter.chapter_number} 章</span>
                  <strong>{chapter.title}</strong>
                  <p>{chapter.goal}</p>
                  <em>{chapter.key_events.join(" / ")}</em>
                </article>
              ))}
            </section>
          ) : null}
        </main>
      </div>
    </section>
  );
}

function splitTags(value: string): string[] {
  return value
    .split(/[,，、]/)
    .map((item) => item.trim())
    .filter(Boolean);
}
