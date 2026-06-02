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

  it("loads a saved chapter quality report", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        score: 72,
        passed: false,
        revision_required: true,
        issues: [
          {
            severity: "high",
            category: "continuity",
            description: "The clue appears too early.",
            suggestion: "Move the clue setup.",
          },
        ],
      }),
    });
    const client = createApiClient("http://localhost:8000", fetcher);

    const result = await client.getChapterQualityReport("novel-demo", 1);

    expect(fetcher).toHaveBeenCalledWith(
      "http://localhost:8000/projects/novel-demo/chapters/1/quality-report",
      {
        headers: { "Content-Type": "application/json" },
      },
    );
    expect(result.issues[0].severity).toBe("high");
  });

  it("loads, saves, and generates project blueprints", async () => {
    const blueprintDocument = {
      project_id: "novel-demo",
      blueprint: {
        title: "Rain Letter",
        logline: "A future letter arrives.",
        setting: "Old river city",
        central_conflict: "Truth or safety.",
        themes: ["truth"],
      },
      characters: [
        {
          name: "Lin",
          role: "Protagonist",
          motivation: "Find the truth",
          arc: "Avoidance to responsibility",
          traits: ["careful"],
        },
      ],
      outline: [
        {
          chapter_number: 1,
          title: "Rain Letter",
          goal: "Find the first clue",
          key_events: ["Lights fail"],
          pov_character: "Lin",
        },
      ],
    };
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({ ok: true, json: async () => blueprintDocument })
      .mockResolvedValueOnce({ ok: true, json: async () => blueprintDocument })
      .mockResolvedValueOnce({ ok: true, json: async () => blueprintDocument });
    const client = createApiClient("http://localhost:8000", fetcher);

    await client.getProjectBlueprint("novel-demo");
    await client.saveProjectBlueprint("novel-demo", blueprintDocument);
    await client.generateProjectBlueprint("novel-demo", {
      user_input: "write a rainy mystery",
      chapter_count: 3,
    });

    expect(fetcher).toHaveBeenNthCalledWith(
      1,
      "http://localhost:8000/projects/novel-demo/blueprint",
      { headers: { "Content-Type": "application/json" } },
    );
    expect(fetcher).toHaveBeenNthCalledWith(
      2,
      "http://localhost:8000/projects/novel-demo/blueprint",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetcher).toHaveBeenNthCalledWith(
      3,
      "http://localhost:8000/projects/novel-demo/blueprint/generate",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("manages runtime LLM profiles", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: "qwen",
          name: "Qwen",
          provider: "qwen",
          model: "qwen-plus",
          base_url: null,
          api_key_set: true,
          temperature: 0.4,
          max_tokens: 3200,
          timeout_seconds: 60,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: "qwen",
          name: "Qwen Max",
          provider: "qwen",
          model: "qwen-max",
          base_url: null,
          api_key_set: false,
          temperature: 0.4,
          max_tokens: 3200,
          timeout_seconds: 60,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 204,
        json: async () => null,
      });
    const client = createApiClient("http://localhost:8000", fetcher);

    await client.createLLMProfile({
      profile_id: "qwen",
      name: "Qwen",
      provider: "qwen",
      model: "qwen-plus",
      api_key: "secret",
      temperature: 0.4,
      max_tokens: 3200,
      timeout_seconds: 60,
    });
    await client.updateLLMProfile("qwen", {
      name: "Qwen Max",
      provider: "qwen",
      model: "qwen-max",
      api_key: null,
    });
    await client.deleteLLMProfile("qwen");

    expect(fetcher).toHaveBeenNthCalledWith(
      1,
      "http://localhost:8000/llm/profiles",
      expect.objectContaining({ method: "POST" }),
    );
    expect(fetcher).toHaveBeenNthCalledWith(
      2,
      "http://localhost:8000/llm/profiles/qwen",
      expect.objectContaining({ method: "PUT" }),
    );
    expect(fetcher).toHaveBeenNthCalledWith(
      3,
      "http://localhost:8000/llm/profiles/qwen",
      expect.objectContaining({ method: "DELETE" }),
    );
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
