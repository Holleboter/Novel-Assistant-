import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  ArrowLeft,
  Check,
  FileCheck,
  Loader2,
  PlayCircle,
  RefreshCw,
  Save,
  Sparkles,
} from "lucide-react";
import { ApiError } from "../api/client";
import type {
  ApiClient,
  ChapterContent,
  ChapterSummary,
  LLMProfileSummary,
  ProjectDetail,
  QualityReport,
  SkillSummary,
  WorkflowRun,
} from "../api/client";
import {
  buildWorkflowSteps,
  defaultFinalFilename,
  firstSelectableChapter,
  groupQualityIssuesBySeverity,
} from "../view-models/workbench";

type CreationWorkbenchProps = {
  api: ApiClient;
  projectId: string;
  onBack: () => void;
};

type InspectorTab = "quality" | "suggestions" | "graph" | "workflow";
type GenerationMode = "deterministic" | "llm";

const severityLabel = {
  blocking: "阻断",
  high: "高",
  medium: "中",
  low: "低",
};

export function CreationWorkbench({
  api,
  projectId,
  onBack,
}: CreationWorkbenchProps) {
  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [chapters, setChapters] = useState<ChapterSummary[]>([]);
  const [selectedChapter, setSelectedChapter] = useState<number | null>(null);
  const [chapterContent, setChapterContent] = useState<ChapterContent | null>(null);
  const [editorContent, setEditorContent] = useState("");
  const [skills, setSkills] = useState<SkillSummary[]>([]);
  const [profiles, setProfiles] = useState<LLMProfileSummary[]>([]);
  const [selectedSkill, setSelectedSkill] = useState("");
  const [selectedProfile, setSelectedProfile] = useState("");
  const [generationMode, setGenerationMode] = useState<GenerationMode>("deterministic");
  const [finalFilename, setFinalFilename] = useState("final.md");
  const [workflowId, setWorkflowId] = useState("");
  const [workflowPrompt, setWorkflowPrompt] = useState(
    "根据当前项目蓝图和章节目标，生成本章可继续人工编辑的正文。",
  );
  const [workflowRun, setWorkflowRun] = useState<WorkflowRun | null>(null);
  const [qualityReport, setQualityReport] = useState<QualityReport | null>(null);
  const [qualityLoading, setQualityLoading] = useState(false);
  const [inspectorTab, setInspectorTab] = useState<InspectorTab>("quality");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const qualityRequestSeq = useRef(0);

  const selectedChapterMeta = useMemo(
    () => chapters.find((chapter) => chapter.chapter_number === selectedChapter) ?? null,
    [chapters, selectedChapter],
  );
  const workflowSteps = useMemo(() => buildWorkflowSteps(workflowRun), [workflowRun]);
  const qualityGroups = useMemo(
    () => groupQualityIssuesBySeverity(qualityReport?.issues ?? []),
    [qualityReport],
  );

  function openWorkflowPanel() {
    setInspectorTab("workflow");
  }

  async function loadWorkspace() {
    setLoading(true);
    setError(null);
    try {
      const [projectDetail, skillList, profileList] = await Promise.all([
        api.getProject(projectId),
        api.listSkills(),
        api.listLLMProfiles(),
      ]);
      setProject(projectDetail);
      setChapters(projectDetail.chapters);
      setSkills(skillList);
      setProfiles(profileList);
      setSelectedSkill((current) => current || skillList[0]?.id || "");
      setSelectedProfile((current) => current || profileList[0]?.id || "");
      const firstChapter = firstSelectableChapter(projectDetail.chapters);
      setSelectedChapter((current) => {
        if (
          current !== null &&
          projectDetail.chapters.some((chapter) => chapter.chapter_number === current)
        ) {
          return current;
        }
        return firstChapter?.chapter_number ?? null;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "工作台加载失败");
    } finally {
      setLoading(false);
    }
  }

  async function loadChapter(chapterNumber: number) {
    setBusy("load-chapter");
    setError(null);
    try {
      const content = await api.getChapterContent(projectId, chapterNumber);
      setChapterContent(content);
      setEditorContent(content.content);
      setFinalFilename(
        defaultFinalFilename(chapterNumber, selectedChapterMeta?.title ?? null),
      );
    } catch (err) {
      setChapterContent(null);
      setEditorContent("");
      setFinalFilename(
        defaultFinalFilename(chapterNumber, selectedChapterMeta?.title ?? null),
      );
      setError(err instanceof Error ? err.message : "章节正文加载失败");
    } finally {
      setBusy(null);
    }
  }

  async function loadQualityReport(chapterNumber: number) {
    const requestId = qualityRequestSeq.current + 1;
    qualityRequestSeq.current = requestId;
    setQualityLoading(true);
    try {
      const report = await api.getChapterQualityReport(projectId, chapterNumber);
      if (qualityRequestSeq.current === requestId) {
        setQualityReport(report);
      }
    } catch (err) {
      if (qualityRequestSeq.current === requestId) {
        setQualityReport(null);
        if (!(err instanceof ApiError && err.status === 404)) {
          setError(err instanceof Error ? err.message : "质检报告加载失败");
        }
      }
    } finally {
      if (qualityRequestSeq.current === requestId) {
        setQualityLoading(false);
      }
    }
  }

  useEffect(() => {
    void loadWorkspace();
  }, [projectId]);

  useEffect(() => {
    if (selectedChapter !== null) {
      void loadChapter(selectedChapter);
      void loadQualityReport(selectedChapter);
    }
  }, [selectedChapter]);

  async function handleDraft() {
    if (selectedChapter === null) {
      openWorkflowPanel();
      setError("请先通过 Workflow 生成章节，或选择已有章节");
      return;
    }
    setBusy("draft");
    setError(null);
    try {
      await api.draftChapter(projectId, selectedChapter, {
        mode: generationMode,
        llm_profile: generationMode === "llm" ? selectedProfile || null : null,
      });
      await loadWorkspace();
      await loadChapter(selectedChapter);
      await loadQualityReport(selectedChapter);
      setNotice("草稿已生成");
    } catch (err) {
      setError(err instanceof Error ? err.message : "草稿生成失败");
    } finally {
      setBusy(null);
    }
  }

  async function handlePolish() {
    if (!selectedSkill || !editorContent.trim()) {
      setError("请选择 Skill 并填写正文");
      return;
    }
    setBusy("polish");
    setError(null);
    try {
      const result = await api.applySkill({
        skill_id: selectedSkill,
        content: editorContent,
        llm_profile: selectedProfile || null,
      });
      setEditorContent(result.content);
      setNotice("润色已应用到编辑器");
    } catch (err) {
      setError(err instanceof Error ? err.message : "润色失败");
    } finally {
      setBusy(null);
    }
  }

  async function handleRecheckQuality() {
    if (selectedChapter === null || !editorContent.trim()) {
      setError("请选择章节并填写正文后再质检");
      return;
    }
    setBusy("quality");
    setError(null);
    const requestId = qualityRequestSeq.current + 1;
    qualityRequestSeq.current = requestId;
    try {
      const report = await api.checkChapterQuality(projectId, selectedChapter, {
        content: editorContent,
      });
      if (qualityRequestSeq.current === requestId) {
        setQualityReport(report);
        setInspectorTab("quality");
        setNotice("质检报告已更新");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "重新质检失败");
    } finally {
      setBusy(null);
    }
  }

  async function handleConfirm() {
    if (selectedChapter === null) {
      return;
    }
    setBusy("confirm");
    setError(null);
    try {
      const result = await api.confirmChapter(projectId, selectedChapter, {
        filename: finalFilename,
        content: editorContent,
      });
      setNotice(`已保存 ${result.filename}`);
      await loadWorkspace();
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setBusy(null);
    }
  }

  async function handleStartWorkflow() {
    if (!workflowPrompt.trim()) {
      setError("请先填写 Workflow 创作指令");
      return;
    }
    setBusy("workflow");
    setError(null);
    try {
      const result = await api.startNovelWorkflow({
        project_id: projectId,
        user_input: workflowPrompt.trim(),
        chapter_count: Math.max(chapters.length, selectedChapter ?? 1, 1),
        start_chapter: selectedChapter ?? 1,
        end_chapter: selectedChapter ?? 1,
        save: true,
        mode: generationMode,
        llm_profile: generationMode === "llm" ? selectedProfile || null : null,
      });
      setWorkflowId(result.workflow_id);
      await handleLoadWorkflow(result.workflow_id);
      await loadWorkspace();
      if (selectedChapter !== null) {
        await loadChapter(selectedChapter);
        await loadQualityReport(selectedChapter);
      }
      setNotice("Workflow 已完成");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Workflow 运行失败");
    } finally {
      setBusy(null);
    }
  }

  async function handleLoadWorkflow(id = workflowId) {
    if (!id.trim()) {
      setError("请输入 workflow_id");
      return;
    }
    setBusy("workflow-load");
    setError(null);
    try {
      const run = await api.getWorkflow(id.trim());
      setWorkflowRun(run);
      setInspectorTab("workflow");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Workflow 状态加载失败");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="workbench">
      <header className="workbench-header">
        <div className="workbench-primary-row">
          <button className="icon-button" onClick={onBack} title="返回项目">
            <ArrowLeft size={18} />
          </button>
          <div className="workbench-title">
            <strong>{project?.project_id ?? projectId}</strong>
            <span>{selectedChapterMeta?.title || "未选择章节"}</span>
          </div>
          <div className="workbench-status-strip">
            <span>{chapters.length} 章</span>
            <span>{selectedChapterMeta?.status === "confirmed" ? "已确认" : "草稿"}</span>
          </div>
          <div className="save-strip">
            <input
              className="filename-input"
              value={finalFilename}
              onChange={(event) => setFinalFilename(event.target.value)}
              aria-label="最终文件名"
            />
            <button
              className="primary-button"
              onClick={handleConfirm}
              disabled={busy === "confirm" || selectedChapter === null}
            >
              {busy === "confirm" ? <Loader2 className="spin" size={17} /> : <Save size={17} />}
              <span>保存 final</span>
            </button>
          </div>
        </div>
        <div className="workbench-action-row">
          <div className="toolbar-group">
            <label className="compact-field">
              Skill
              <select value={selectedSkill} onChange={(event) => setSelectedSkill(event.target.value)}>
                <option value="">选择 Skill</option>
                {skills.map((skill) => (
                  <option key={skill.id} value={skill.id}>
                    {skill.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="compact-field">
              生成模式
              <select
                value={generationMode}
                onChange={(event) => setGenerationMode(event.target.value as GenerationMode)}
              >
                <option value="deterministic">本地规则</option>
                <option value="llm">LLM</option>
              </select>
            </label>
            <label className="compact-field">
              模型
              <select
                value={selectedProfile}
                onChange={(event) => setSelectedProfile(event.target.value)}
                disabled={profiles.length === 0}
              >
                <option value="">默认模型</option>
                {profiles.map((profile) => (
                  <option key={profile.id} value={profile.id}>
                    {profile.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="toolbar-group toolbar-actions">
            <button className="toolbar-button" onClick={handlePolish} disabled={busy === "polish"}>
              {busy === "polish" ? <Loader2 className="spin" size={17} /> : <Sparkles size={17} />}
              <span>润色</span>
            </button>
            <button className="toolbar-button" onClick={handleRecheckQuality} disabled={busy === "quality"}>
              {busy === "quality" ? <Loader2 className="spin" size={17} /> : <FileCheck size={17} />}
              <span>质检</span>
            </button>
            <button className="toolbar-button" onClick={handleDraft} disabled={busy === "draft"}>
              {busy === "draft" ? <Loader2 className="spin" size={17} /> : <RefreshCw size={17} />}
              <span>生成草稿</span>
            </button>
            <button className="toolbar-button" onClick={openWorkflowPanel}>
              <PlayCircle size={17} />
              <span>Workflow</span>
            </button>
          </div>
        </div>
      </header>

      {error ? <div className="workbench-alert error">{error}</div> : null}
      {notice ? <div className="workbench-alert success">{notice}</div> : null}

      <div className="workbench-grid">
        <aside className="chapter-sidebar">
          <div className="sidebar-header">
            <strong>章节</strong>
            <span>{chapters.length}</span>
          </div>
          {loading ? <div className="empty-state">加载中</div> : null}
          {!loading && chapters.length === 0 ? (
            <div className="sidebar-empty">
              <strong>暂无章节</strong>
              <span>先运行 Workflow 生成大纲和章节草稿。</span>
              <button className="secondary-button full" onClick={openWorkflowPanel}>
                <PlayCircle size={17} />
                <span>打开运行面板</span>
              </button>
            </div>
          ) : null}
          {chapters.map((chapter) => (
            <button
              className={
                chapter.chapter_number === selectedChapter
                  ? "chapter-item active"
                  : "chapter-item"
              }
              key={chapter.chapter_number}
              onClick={() => setSelectedChapter(chapter.chapter_number)}
            >
              <span>第 {chapter.chapter_number} 章</span>
              <strong>{chapter.title || "未命名"}</strong>
              <em>{chapter.status === "confirmed" ? "已确认" : "草稿"}</em>
            </button>
          ))}
        </aside>

        <section className="editor-pane">
          <div className="editor-header">
            <div>
              <strong>{chapterContent?.filename || "正文编辑器"}</strong>
              <span>{chapterContent?.source === "final" ? "最终稿" : "草稿"}</span>
            </div>
            {busy === "load-chapter" ? <Loader2 className="spin" size={18} /> : null}
          </div>
          {selectedChapter === null && !editorContent ? (
            <div className="editor-empty-shell">
              <div className="editor-empty-panel">
                <strong>还没有可编辑章节</strong>
                <p>先运行 Workflow 生成章节草稿，之后正文会出现在这里，支持润色、质检和人工修改。</p>
                <button className="primary-button" onClick={openWorkflowPanel}>
                  <PlayCircle size={17} />
                  <span>运行 Workflow</span>
                </button>
              </div>
            </div>
          ) : (
            <textarea
              className="markdown-editor"
              value={editorContent}
              onChange={(event) => setEditorContent(event.target.value)}
              placeholder="选择章节后加载正文"
            />
          )}
        </section>

        <aside className="inspector">
          <div className="inspector-tabs">
            <button
              className={inspectorTab === "quality" ? "active" : ""}
              onClick={() => setInspectorTab("quality")}
            >
              质检
            </button>
            <button
              className={inspectorTab === "suggestions" ? "active" : ""}
              onClick={() => setInspectorTab("suggestions")}
            >
              建议
            </button>
            <button
              className={inspectorTab === "graph" ? "active" : ""}
              onClick={() => setInspectorTab("graph")}
            >
              图谱
            </button>
            <button
              className={inspectorTab === "workflow" ? "active" : ""}
              onClick={() => setInspectorTab("workflow")}
            >
              运行
            </button>
          </div>

          {inspectorTab === "quality" ? (
            <div className="inspector-body">
              <StatusLine icon={<FileCheck size={18} />} label="章节状态" value={selectedChapterMeta?.status || "草稿"} />
              <StatusLine icon={<Check size={18} />} label="内容来源" value={selectedChapterMeta?.content_source || chapterContent?.source || "未加载"} />
              {qualityLoading ? <div className="empty-state">质检报告加载中</div> : null}
              {!qualityLoading && qualityReport ? (
                <QualityReportView report={qualityReport} groups={qualityGroups} />
              ) : null}
              {!qualityLoading && !qualityReport ? (
                <div className="inspector-empty">
                  <strong>暂无质检报告</strong>
                  <span>正文生成或编辑后，可重新质检并查看阻断问题。</span>
                  <button className="secondary-button full" onClick={handleRecheckQuality}>
                    <FileCheck size={17} />
                    <span>重新质检</span>
                  </button>
                </div>
              ) : null}
            </div>
          ) : null}

          {inspectorTab === "suggestions" ? (
            <div className="inspector-body">
              {qualityReport?.issues.length ? (
                qualityReport.issues
                  .filter((issue) => issue.suggestion)
                  .map((issue) => (
                    <div className="suggestion-item" key={`${issue.category}-${issue.description}`}>
                      <strong>{issue.category}</strong>
                      <span>{issue.suggestion}</span>
                    </div>
                  ))
              ) : (
                <>
                  <div className="suggestion-item">
                    <strong>节奏</strong>
                    <span>检查每 800-1200 字是否有明确推进点。</span>
                  </div>
                  <div className="suggestion-item">
                    <strong>去 AI 味</strong>
                    <span>优先使用 Skill 润色，再人工读一遍对白和心理描写。</span>
                  </div>
                </>
              )}
            </div>
          ) : null}

          {inspectorTab === "graph" ? (
            <div className="inspector-body graph-placeholder">
              <div className="mini-node large">主角</div>
              <div className="mini-edge" />
              <div className="mini-node">事件</div>
              <p className="muted-text">这里保留当前章节人物图谱预览，完整图谱进入图谱中心。</p>
            </div>
          ) : null}

          {inspectorTab === "workflow" ? (
            <div className="inspector-body">
              <label>
                创作指令
                <textarea
                  className="workflow-prompt"
                  value={workflowPrompt}
                  onChange={(event) => setWorkflowPrompt(event.target.value)}
                />
              </label>
              <div className="workflow-control">
                <input
                  value={workflowId}
                  onChange={(event) => setWorkflowId(event.target.value)}
                  placeholder="workflow_id"
                />
                <button className="icon-button" onClick={() => void handleLoadWorkflow()}>
                  <RefreshCw size={17} />
                </button>
              </div>
              <button className="secondary-button full" onClick={handleStartWorkflow}>
                {busy === "workflow" ? <Loader2 className="spin" size={17} /> : <Sparkles size={17} />}
                <span>运行当前章</span>
              </button>
              <div className="workflow-steps">
                {workflowSteps.map((step) => (
                  <div className={`workflow-step ${step.state}`} key={step.label}>
                    <span />
                    <strong>{step.label}</strong>
                  </div>
                ))}
              </div>
              {workflowRun?.error ? <div className="alert error">{workflowRun.error}</div> : null}
            </div>
          ) : null}
        </aside>
      </div>
    </section>
  );
}

function QualityReportView({
  report,
  groups,
}: {
  report: QualityReport;
  groups: ReturnType<typeof groupQualityIssuesBySeverity>;
}) {
  return (
    <>
      <div className={report.passed ? "quality-score pass" : "quality-score warn"}>
        <span>评分</span>
        <strong>{report.score}</strong>
        <em>{report.passed ? "通过" : "需修改"}</em>
      </div>
      {groups.length === 0 ? (
        <div className="empty-state">未发现明确问题。</div>
      ) : null}
      {groups.map((group) => (
        <div className="issue-group" key={group.severity}>
          <strong>{severityLabel[group.severity]}优先级</strong>
          {group.issues.map((issue) => (
            <div className="issue-card" key={`${issue.category}-${issue.description}`}>
              <span>{issue.category}</span>
              <p>{issue.description}</p>
              {issue.suggestion ? <em>{issue.suggestion}</em> : null}
            </div>
          ))}
        </div>
      ))}
    </>
  );
}

function StatusLine({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="status-line">
      {icon}
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
