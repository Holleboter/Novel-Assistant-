import type { ChapterSummary, QualityIssue, WorkflowRun } from "../api/client";

export type WorkflowStep = {
  label: string;
  state: "pending" | "current" | "done" | "failed";
};

export type QualityIssueGroup = {
  severity: QualityIssue["severity"];
  issues: QualityIssue[];
};

export function firstSelectableChapter(
  chapters: ChapterSummary[],
): ChapterSummary | null {
  return [...chapters].sort(
    (left, right) => left.chapter_number - right.chapter_number,
  )[0] ?? null;
}

export function defaultFinalFilename(
  chapterNumber: number,
  _chapterTitle: string | null,
): string {
  return `chapter-${String(chapterNumber).padStart(4, "0")}-final.md`;
}

export function buildWorkflowSteps(run: WorkflowRun | null): WorkflowStep[] {
  const labels = ["需求解析", "蓝图生成", "章节生成", "质量检查", "等待确认"];
  if (run === null) {
    return labels.map((label, index) => ({
      label,
      state: index === 0 ? "current" : "pending",
    }));
  }

  if (run.status === "failed") {
    const completed = completedStepCount(run);
    return labels.map((label, index) => ({
      label,
      state: index < completed ? "done" : index === completed ? "failed" : "pending",
    }));
  }

  if (run.status === "completed") {
    return labels.map((label, index) => ({
      label,
      state: index < labels.length - 1 ? "done" : "current",
    }));
  }

  const completed = completedStepCount(run);
  return labels.map((label, index) => ({
    label,
    state: index < completed ? "done" : index === completed ? "current" : "pending",
  }));
}

export function groupQualityIssuesBySeverity(
  issues: QualityIssue[],
): QualityIssueGroup[] {
  const order: QualityIssue["severity"][] = ["blocking", "high", "medium", "low"];
  return order
    .map((severity) => ({
      severity,
      issues: issues.filter((issue) => issue.severity === severity),
    }))
    .filter((group) => group.issues.length > 0);
}

function completedStepCount(run: WorkflowRun): number {
  const completedChapters = run.progress.completed_chapters || 0;
  if (completedChapters > 0) {
    return 3;
  }
  return 2;
}
