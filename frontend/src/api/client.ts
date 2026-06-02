export type Fetcher = (
  input: string,
  init?: {
    method?: string;
    headers?: Record<string, string>;
    body?: string;
  },
) => Promise<{
  ok: boolean;
  status?: number;
  json: () => Promise<unknown>;
}>;

export type ProjectSummary = {
  project_id: string;
  title: string | null;
  has_outline: boolean;
  outline_path?: string | null;
  chapter_count: number;
};

export type ProjectDetail = {
  project_id: string;
  has_outline: boolean;
  outline_path: string | null;
  chapters: ChapterSummary[];
};

export type ChapterSummary = {
  project_id?: string;
  chapter_number: number;
  title: string | null;
  files?: string[];
  status?: string;
  content_source?: string;
  final_filename?: string;
};

export type StoryBlueprint = {
  title: string;
  logline: string;
  setting: string;
  central_conflict: string;
  themes: string[];
};

export type CharacterProfile = {
  name: string;
  role: string;
  motivation: string;
  arc: string;
  traits: string[];
};

export type ChapterPlan = {
  chapter_number: number;
  title: string;
  goal: string;
  key_events: string[];
  pov_character: string | null;
};

export type BlueprintDocument = {
  project_id: string;
  blueprint: StoryBlueprint;
  characters: CharacterProfile[];
  outline: ChapterPlan[];
};

export type BlueprintGeneratePayload = {
  user_input: string;
  chapter_count?: number;
  mode?: "deterministic" | "llm";
  llm_profile?: string | null;
};

export type ChapterContent = {
  project_id: string;
  chapter_number: number;
  filename: string;
  source: "final" | "draft";
  content: string;
};

export type ConfirmChapterPayload = {
  filename: string;
  content: string;
};

export type ConfirmChapterResult = {
  project_id: string;
  chapter_number: number;
  filename: string;
  status: "confirmed";
  content_source: "human_confirmed";
  path: string;
};

export type SkillSummary = {
  id: string;
  name: string;
  description: string | null;
};

export type LLMProfileSummary = {
  id: string;
  name: string;
  provider: string;
  model: string;
  base_url: string | null;
  api_key_set: boolean;
  temperature: number;
  max_tokens: number;
  timeout_seconds: number;
};

export type LLMProfilePayload = {
  profile_id?: string | null;
  name?: string | null;
  provider: string;
  model: string;
  api_key?: string | null;
  base_url?: string | null;
  temperature?: number | null;
  max_tokens?: number | null;
  timeout_seconds?: number | null;
};

export type QualityIssue = {
  severity: "low" | "medium" | "high" | "blocking";
  category: string;
  description: string;
  suggestion?: string | null;
};

export type QualityReport = {
  score: number;
  issues: QualityIssue[];
  revision_required: boolean | null;
  passed: boolean | null;
};

export type SkillApplyPayload = {
  skill_id: string;
  content: string;
  llm_profile?: string | null;
};

export type WorkflowRun = {
  workflow_id: string;
  project_id: string;
  status: "running" | "completed" | "failed";
  progress: {
    total_chapters: number;
    completed_chapters: number;
    current_chapter: number | null;
    target_chapters?: number;
  };
  request: Record<string, unknown>;
  result: Record<string, unknown> | null;
  error: string | null;
  created_at: string;
  updated_at: string;
};

export type NovelWorkflowPayload = {
  project_id: string;
  user_input: string;
  chapter_count?: number;
  start_chapter?: number;
  end_chapter?: number | null;
  save?: boolean;
  mode?: "deterministic" | "llm";
  llm_profile?: string | null;
};

export type ApiClient = ReturnType<typeof createApiClient>;

export class ApiError extends Error {
  readonly status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function createApiClient(
  baseUrl = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
  fetcher: Fetcher = fetch as Fetcher,
) {
  const normalizedBaseUrl = baseUrl.replace(/\/+$/, "");

  async function request<T>(
    path: string,
    init?: {
      method?: string;
      body?: unknown;
    },
  ): Promise<T> {
    const response = await fetcher(`${normalizedBaseUrl}${path}`, {
      ...(init?.method ? { method: init.method } : {}),
      headers: { "Content-Type": "application/json" },
      ...(init?.body === undefined ? {} : { body: JSON.stringify(init.body) }),
    });
    if (response.status === 204) {
      return undefined as T;
    }
    const payload = await response.json();
    if (!response.ok) {
      throw new ApiError(errorMessage(payload), response.status);
    }
    return payload as T;
  }

  return {
    listProjects: () => request<ProjectSummary[]>("/projects"),
    createProject: (payload: { project_id: string; title?: string | null }) =>
      request<ProjectSummary>("/projects", { method: "POST", body: payload }),
    getProject: (projectId: string) =>
      request<ProjectDetail>(`/projects/${encodeURIComponent(projectId)}`),
    getProjectBlueprint: (projectId: string) =>
      request<BlueprintDocument>(
        `/projects/${encodeURIComponent(projectId)}/blueprint`,
      ),
    saveProjectBlueprint: (projectId: string, payload: BlueprintDocument) =>
      request<BlueprintDocument>(
        `/projects/${encodeURIComponent(projectId)}/blueprint`,
        { method: "POST", body: payload },
      ),
    generateProjectBlueprint: (
      projectId: string,
      payload: BlueprintGeneratePayload,
    ) =>
      request<BlueprintDocument>(
        `/projects/${encodeURIComponent(projectId)}/blueprint/generate`,
        { method: "POST", body: payload },
      ),
    listChapters: (projectId: string) =>
      request<ChapterSummary[]>(
        `/projects/${encodeURIComponent(projectId)}/chapters`,
      ),
    getChapterContent: (projectId: string, chapterNumber: number) =>
      request<ChapterContent>(
        `/projects/${encodeURIComponent(projectId)}/chapters/${chapterNumber}/content`,
      ),
    getChapterQualityReport: (projectId: string, chapterNumber: number) =>
      request<QualityReport>(
        `/projects/${encodeURIComponent(projectId)}/chapters/${chapterNumber}/quality-report`,
      ),
    checkChapterQuality: (
      projectId: string,
      chapterNumber: number,
      payload: { content: string },
    ) =>
      request<QualityReport>(
        `/projects/${encodeURIComponent(projectId)}/chapters/${chapterNumber}/quality-report`,
        { method: "POST", body: payload },
      ),
    confirmChapter: (
      projectId: string,
      chapterNumber: number,
      payload: ConfirmChapterPayload,
    ) =>
      request<ConfirmChapterResult>(
        `/projects/${encodeURIComponent(projectId)}/chapters/${chapterNumber}/confirm`,
        { method: "POST", body: payload },
      ),
    draftChapter: (
      projectId: string,
      chapterNumber: number,
      payload?: { mode?: "deterministic" | "llm"; llm_profile?: string | null },
    ) =>
      request<{
        chapter_number: number;
        title: string;
        passed: boolean | null;
        chapter_dir: string;
      }>(`/projects/${encodeURIComponent(projectId)}/chapters/${chapterNumber}/draft`, {
        method: "POST",
        body: payload ?? {},
      }),
    listSkills: () => request<SkillSummary[]>("/skills"),
    applySkill: (payload: SkillApplyPayload) =>
      request<{ skill_id: string; content: string }>("/skills/apply", {
        method: "POST",
        body: payload,
      }),
    listLLMProfiles: () => request<LLMProfileSummary[]>("/llm/profiles"),
    createLLMProfile: (payload: LLMProfilePayload) =>
      request<LLMProfileSummary>("/llm/profiles", {
        method: "POST",
        body: payload,
      }),
    updateLLMProfile: (profileId: string, payload: LLMProfilePayload) =>
      request<LLMProfileSummary>(`/llm/profiles/${encodeURIComponent(profileId)}`, {
        method: "PUT",
        body: payload,
      }),
    deleteLLMProfile: (profileId: string) =>
      request<void>(`/llm/profiles/${encodeURIComponent(profileId)}`, {
        method: "DELETE",
      }),
    startNovelWorkflow: (payload: NovelWorkflowPayload) =>
      request<{ workflow_id: string; status: string; project_id: string }>(
        "/workflows/novel-generation",
        { method: "POST", body: payload },
      ),
    getWorkflow: (workflowId: string) =>
      request<WorkflowRun>(`/workflows/${encodeURIComponent(workflowId)}`),
  };
}

function errorMessage(payload: unknown): string {
  if (
    payload &&
    typeof payload === "object" &&
    "detail" in payload &&
    typeof payload.detail === "string"
  ) {
    return payload.detail;
  }
  if (payload && typeof payload === "object" && "detail" in payload) {
    return JSON.stringify(payload.detail);
  }
  return "API request failed";
}
