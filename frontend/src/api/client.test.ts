import { describe, expect, it, vi } from "vitest";
import { createApiClient } from "./client";

describe("createApiClient", () => {
  it("loads projects from the configured API base URL", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        {
          project_id: "novel-demo",
          title: "雨夜来信",
          has_outline: true,
          outline_path: "projects/novel-demo/outline.json",
          chapter_count: 2,
        },
      ],
    });
    const client = createApiClient("http://localhost:8000/", fetcher);

    const projects = await client.listProjects();

    expect(fetcher).toHaveBeenCalledWith("http://localhost:8000/projects", {
      headers: { "Content-Type": "application/json" },
    });
    expect(projects[0].project_id).toBe("novel-demo");
    expect(projects[0].chapter_count).toBe(2);
  });

  it("posts final chapter confirmation payloads", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        project_id: "novel-demo",
        chapter_number: 1,
        filename: "final.md",
        status: "confirmed",
        content_source: "human_confirmed",
        path: "projects/novel-demo/chapters/chapter-0001/final.md",
      }),
    });
    const client = createApiClient("http://localhost:8000", fetcher);

    const result = await client.confirmChapter("novel-demo", 1, {
      filename: "final.md",
      content: "human edited final",
    });

    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/projects/novel-demo/chapters/1/confirm",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: "final.md",
          content: "human edited final",
        }),
      },
    );
    expect(result.status).toBe("confirmed");
  });

  it("throws readable errors when the API responds with a failure", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: "Project not found" }),
    });
    const client = createApiClient("http://localhost:8000", fetcher);

    await expect(client.getProject("missing")).rejects.toThrow("Project not found");
  });
});
