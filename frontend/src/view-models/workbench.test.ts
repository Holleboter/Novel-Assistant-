import { describe, expect, it } from "vitest";
import {
  buildWorkflowSteps,
  defaultFinalFilename,
  firstSelectableChapter,
  groupQualityIssuesBySeverity,
} from "./workbench";

describe("workbench view model", () => {
  it("selects the first available chapter", () => {
    const chapter = firstSelectableChapter([
      { chapter_number: 2, title: "第二章" },
      { chapter_number: 1, title: "第一章" },
    ]);

    expect(chapter?.chapter_number).toBe(1);
  });

  it("creates safe default final filenames", () => {
    expect(defaultFinalFilename(3, "雨夜 来信")).toBe("chapter-0003-final.md");
    expect(defaultFinalFilename(12, "Chapter 12")).toBe("chapter-0012-final.md");
  });

  it("maps workflow runs into stable display steps", () => {
    const steps = buildWorkflowSteps({
      workflow_id: "run-1",
      project_id: "novel-demo",
      status: "completed",
      progress: {
        total_chapters: 3,
        completed_chapters: 2,
        current_chapter: 2,
      },
      request: {},
      result: null,
      error: null,
      created_at: "2026-06-01T00:00:00Z",
      updated_at: "2026-06-01T00:00:10Z",
    });

    expect(steps.map((step) => step.label)).toEqual([
      "需求解析",
      "蓝图生成",
      "章节生成",
      "质量检查",
      "等待确认",
    ]);
    expect(steps.at(-1)?.state).toBe("current");
  });

  it("groups quality issues by severity in inspector order", () => {
    const groups = groupQualityIssuesBySeverity([
      {
        severity: "low",
        category: "style",
        description: "Dialogue is flat.",
        suggestion: null,
      },
      {
        severity: "blocking",
        category: "timeline",
        description: "The event order conflicts.",
        suggestion: "Move the reveal.",
      },
      {
        severity: "high",
        category: "logic",
        description: "Motivation is unclear.",
        suggestion: null,
      },
    ]);

    expect(groups.map((group) => group.severity)).toEqual([
      "blocking",
      "high",
      "low",
    ]);
    expect(groups[0].issues[0].category).toBe("timeline");
  });
});
