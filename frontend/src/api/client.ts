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
    listChapters: (projectId: string) =>
      request<ChapterSummary[]>(
        `/projects/${encodeURIComponent(projectId)}/chapters`,
      ),
    getChapterContent: (projectId: string, chapterNumber: number) =>
      request<ChapterContent>(
        `/projects/${encodeURIComponent(projectId)}/chapters/${chapterNumber}/content`,
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
