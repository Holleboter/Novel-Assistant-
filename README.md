# Novel-Assistant

Novel-Assistant 是一个基于 Python、LangGraph 和 Neo4j 的小说创作智能体 MVP。

第一阶段目标是跑通一条最小可用链路：

- 根据用户创意生成小说蓝图、主角设定和第一章计划。
- 使用 LangGraph 编排章节生产、质检、修订和图谱回写。
- 使用 Neo4j 保存小说、人物、章节、事件和关系。
- 使用 Markdown/JSON 保存章节正文、质检报告和图谱变更。

## 本地 Neo4j

默认连接配置：

```text
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=change_me
```

## 大模型配置

大模型先按 OpenAI-compatible 方式配置，后面可以在适配器层接入 DeepSeek、通义千问、Moonshot/Kimi、OpenAI 或本地模型服务。

```text
LLM_PROVIDER=openai_compatible
LLM_MODEL=
LLM_API_KEY=
LLM_BASE_URL=
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=4000
LLM_TIMEOUT_SECONDS=120
```

不同厂商的示例写在 [.env.example](/E:/pythonstudy-git/PycharmProjects/Novel-Assistant-/.env.example) 里，真实 key 放到本地 `.env`，不要提交到仓库。

代码中可以这样调用：

```python
from novel_assistant.llm_client import LLMClient

client = LLMClient()
response = client.complete(
    system_prompt="你是小说创作助手。",
    user_prompt="写一个 200 字的悬疑小说开头。",
)
print(response.content)
```

也可以让 demo 使用真实大模型生成章节草稿：

```python
from novel_assistant.demo import run_demo

result = run_demo(
    "写一本雨夜悬疑奇幻小说，主角在茶馆收到未来来信。",
    use_llm=True,
)
print(result["final_chapter"].content)
```

`use_llm=True` 会同时启用：

- LLM 需求解析
- LLM 小说蓝图生成
- LLM 人物生成
- LLM 第一章计划生成
- LLM 章节草稿生成

质检、修订、图谱抽取和章节保存仍走本地确定性逻辑，方便测试和控成本。

后端也支持批量生成章节大纲：

```python
from novel_assistant.planning_pipeline import LLMBackedStoryPlanner
from novel_assistant.storage import save_outline

planner = LLMBackedStoryPlanner()
requirement = planner.analyze_requirement("写一本雨夜悬疑奇幻小说。")
blueprint = planner.build_blueprint(requirement)
characters = planner.build_characters(requirement, blueprint)
outline = planner.plan_chapters(requirement, blueprint, characters, chapter_count=12)
save_outline("novel-demo", outline)
```

## 章节保存结构

生成内容默认保存到：

```text
projects/<project_id>/
  project.json
  blueprint.json
  outline.json
  chapters/
    chapter-0001/
      plan.json
      draft.md
      quality-report.json
      final.md
      graph-delta.json
      metadata.json
```

Neo4j 保存结构化事实和关系，不直接保存整章正文。
Workflow 保存链路也会写入 `outline.json`，因此通过 Workflow 生成的项目可以继续使用项目大纲查询和批量章节接口。

## 开发

```bash
python -m pip install -e ".[dev]"
pytest -q
python -m novel_assistant.demo
```

启动 API 服务：

```bash
uvicorn novel_assistant.api:app --reload
```

启动前端工作台：

```bash
cd frontend
npm install
npm run dev
```

默认前端会请求 `http://localhost:8000`，后端已允许 `localhost` / `127.0.0.1` 的本地开发端口跨域访问。如需改后端地址，可以设置：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

前端验证：

```bash
cd frontend
npm test
npm run build
```

当前前端已包含项目首页、创作工作台和设置页。创作工作台支持章节列表、正文编辑器、Skill 润色、生成草稿、确认保存 final Markdown、Workflow 状态查询和右侧 Inspector。

示例请求：

```bash
curl -X POST http://127.0.0.1:8000/outline ^
  -H "Content-Type: application/json" ^
  -d "{\"project_id\":\"novel-demo\",\"user_input\":\"写一本雨夜悬疑小说\",\"chapter_count\":3,\"save\":true}"
```

### LLM Profile API

前端可以通过 API 管理运行时大模型配置。真实 `api_key` 会保存到本地 `data/llm-profiles.json`，该文件已加入 `.gitignore`，不要提交到仓库；接口返回时不会包含真实 key，只返回 `api_key_set` 表示是否已配置。

创建配置：

```bash
curl -X POST http://127.0.0.1:8000/llm/profiles ^
  -H "Content-Type: application/json" ^
  -d "{\"profile_id\":\"deepseek-default\",\"name\":\"DeepSeek 默认\",\"provider\":\"deepseek\",\"model\":\"deepseek-chat\",\"api_key\":\"sk-xxx\",\"base_url\":\"https://api.deepseek.com/v1\",\"temperature\":0.7,\"max_tokens\":4000,\"timeout_seconds\":120}"
```

查询配置列表：

```bash
curl http://127.0.0.1:8000/llm/profiles
```

返回示例：

```json
[
  {
    "id": "deepseek-default",
    "name": "DeepSeek 默认",
    "provider": "deepseek",
    "model": "deepseek-chat",
    "base_url": "https://api.deepseek.com/v1",
    "api_key_set": true,
    "temperature": 0.7,
    "max_tokens": 4000,
    "timeout_seconds": 120
  }
]
```

更新配置：

```bash
curl -X PUT http://127.0.0.1:8000/llm/profiles/deepseek-default ^
  -H "Content-Type: application/json" ^
  -d "{\"provider\":\"deepseek\",\"model\":\"deepseek-chat\",\"api_key\":\"sk-new\",\"base_url\":\"https://api.deepseek.com/v1\"}"
```

删除配置：

```bash
curl -X DELETE http://127.0.0.1:8000/llm/profiles/deepseek-default
```

使用指定配置生成大纲：

```bash
curl -X POST http://127.0.0.1:8000/outline ^
  -H "Content-Type: application/json" ^
  -d "{\"project_id\":\"novel-demo\",\"user_input\":\"写一本雨夜悬疑小说\",\"chapter_count\":3,\"save\":true,\"mode\":\"llm\",\"llm_profile\":\"deepseek-default\"}"
```

使用指定配置生成章节草稿：

```bash
curl -X POST http://127.0.0.1:8000/projects/novel-demo/chapters/1/draft ^
  -H "Content-Type: application/json" ^
  -d "{\"mode\":\"llm\",\"llm_profile\":\"deepseek-default\"}"
```

### Project API

创建空项目：

```bash
curl -X POST http://127.0.0.1:8000/projects ^
  -H "Content-Type: application/json" ^
  -d "{\"project_id\":\"novel-demo\",\"title\":\"Rain Letter\"}"
```

查询项目列表：

```bash
curl http://127.0.0.1:8000/projects
```

返回示例：

```json
[
  {
    "project_id": "novel-demo",
    "title": "Rain Letter",
    "has_outline": true,
    "outline_path": "projects/novel-demo/outline.json",
    "chapter_count": 2
  }
]
```

查询项目大纲：

```bash
curl http://127.0.0.1:8000/projects/novel-demo/outline
```

批量生成章节草稿：

```bash
curl -X POST http://127.0.0.1:8000/projects/novel-demo/chapters/draft-batch ^
  -H "Content-Type: application/json" ^
  -d "{\"start_chapter\":1,\"end_chapter\":5,\"mode\":\"llm\",\"llm_profile\":\"deepseek-default\"}"
```

批量生成是同步接口，会逐章写入 `draft.md`、`final.md`、`quality-report.json`、`graph-delta.json` 和 `metadata.json`。当前 `project_id` 只允许字母、数字、下划线和短横线，避免把任意文件路径暴露给项目接口。

### Workflow API

`/outline` 主要用于生成和保存大纲；Workflow API 是一站式链路，会执行需求解析、蓝图生成、人物生成、多章节大纲、章节草稿、质检、必要修订、图谱回写和文件保存。

当前 v1 是同步接口，支持用 `chapter_count` 生成完整大纲，并用 `start_chapter`/`end_chapter` 指定本次要生成的章节范围。LLM 模式下可能耗时较长，前端应展示 loading，避免重复提交。

```bash
curl -X POST http://127.0.0.1:8000/workflows/novel-generation ^
  -H "Content-Type: application/json" ^
  -d "{\"project_id\":\"novel-demo\",\"user_input\":\"写一本雨夜悬疑小说\",\"chapter_count\":12,\"start_chapter\":1,\"end_chapter\":3,\"save\":true,\"mode\":\"llm\",\"llm_profile\":\"deepseek-default\"}"
```

返回示例：

```json
{
  "workflow_id": "novel-demo-a1b2c3d4e5f6",
  "status": "completed",
  "project_id": "novel-demo",
  "project_path": "projects/novel-demo",
  "chapter_count": 12,
  "generated_chapter_count": 3,
  "chapter_number": 1,
  "title": "Rain Letter",
  "passed": true,
  "chapters": [
    {
      "chapter_number": 1,
      "title": "Rain Letter",
      "passed": true,
      "chapter_dir": "projects/novel-demo/chapters/chapter-0001"
    },
    {
      "chapter_number": 2,
      "title": "Broken Clock",
      "passed": true,
      "chapter_dir": "projects/novel-demo/chapters/chapter-0002"
    },
    {
      "chapter_number": 3,
      "title": "Quiet Bridge",
      "passed": true,
      "chapter_dir": "projects/novel-demo/chapters/chapter-0003"
    }
  ],
  "artifacts": {
    "project_dir": "projects/novel-demo",
    "outline_path": "projects/novel-demo/outline.json",
    "chapter_dir": "projects/novel-demo/chapters/chapter-0001"
  }
}
```

`save=true` 会写入 `project.json`、`blueprint.json`、`outline.json` 和每章的 `draft.md`、`final.md`、`quality-report.json`、`graph-delta.json`、`metadata.json`。`save=false` 时仍会执行 LangGraph 编排和图谱写入，但不会把项目文件保存到本地目录，响应里的 `project_path`、`artifacts.*_path` 和 `chapters[].chapter_dir` 会是 `null`。

每次 Workflow 调用都会在本地创建运行记录，默认保存到 `data/workflow-runs/<workflow_id>.json`。该目录已加入 `.gitignore`，用于本地开发调试，不应提交到仓库。运行记录只保存 `llm_profile` 等请求字段，不保存真实 `api_key`。

查询 Workflow 运行记录：

```bash
curl http://127.0.0.1:8000/workflows/novel-demo-a1b2c3d4e5f6
```

返回示例：

```json
{
  "workflow_id": "novel-demo-a1b2c3d4e5f6",
  "project_id": "novel-demo",
  "status": "completed",
  "progress": {
    "total_chapters": 12,
    "completed_chapters": 3,
    "current_chapter": 3
  },
  "request": {
    "project_id": "novel-demo",
    "user_input": "写一本雨夜悬疑小说",
    "chapter_count": 12,
    "start_chapter": 1,
    "end_chapter": 3,
    "save": true,
    "mode": "llm",
    "llm_profile": "deepseek-default"
  },
  "result": {
    "workflow_id": "novel-demo-a1b2c3d4e5f6",
    "status": "completed",
    "project_id": "novel-demo",
    "generated_chapter_count": 3
  },
  "error": null,
  "created_at": "2026-06-01T12:00:00+00:00",
  "updated_at": "2026-06-01T12:01:30+00:00"
}
```

当前执行仍是同步的：`POST /workflows/novel-generation` 会先写入 `running`，成功后更新为 `completed`，异常时更新为 `failed`。下一步可以把执行过程放到后台任务里，现有 `GET /workflows/{workflow_id}` 不需要大改。

### 章节编辑 API

创作工作台可以读取章节正文，让用户在编辑器里人工修改；只有用户点击确认后，后端才保存最终 Markdown 文件。

读取章节可编辑正文：

```bash
curl http://127.0.0.1:8000/projects/novel-demo/chapters/1/content
```

读取优先级是：`metadata.json` 中的 `final_filename`、`final.md`、`draft.md`。

确认保存最终正文：

```bash
curl -X POST http://127.0.0.1:8000/projects/novel-demo/chapters/1/confirm ^
  -H "Content-Type: application/json" ^
  -d "{\"filename\":\"rain-letter-final.md\",\"content\":\"用户最终确认后的正文\"}"
```

`filename` 只允许安全的 `.md` 单文件名，例如 `rain-letter-final.md`，不能包含路径分隔符。保存后会更新 `metadata.json`：

```json
{
  "status": "confirmed",
  "content_source": "human_confirmed",
  "final_filename": "rain-letter-final.md"
}
```

### Skill API

Skill 模块会读取本地 `skills/<skill_id>/SKILL.md`，用于对章节正文执行润色、去 AI 味、风格调整等操作。`GET /skills` 只返回摘要，不返回完整 `SKILL.md` 内容。

```text
skills/
  humanizer-zh/
    SKILL.md
```

查询 Skill：

```bash
curl http://127.0.0.1:8000/skills
```

应用 Skill：

```bash
curl -X POST http://127.0.0.1:8000/skills/apply ^
  -H "Content-Type: application/json" ^
  -d "{\"skill_id\":\"humanizer-zh\",\"content\":\"AI 生成的章节正文\",\"llm_profile\":\"deepseek-default\"}"
```

返回：

```json
{
  "skill_id": "humanizer-zh",
  "content": "润色后的章节正文"
}
```

注意：`SKILL.md` 会作为 system prompt 发送给所选模型服务商，不要在 Skill 文件里写真实密钥、内网地址或不可外发资料。接口响应不会返回真实 `api_key`，也不会回显完整 `SKILL.md`。

当前 API 还支持：

```text
GET  /llm/profiles
POST /llm/profiles
PUT  /llm/profiles/{profile_id}
DELETE /llm/profiles/{profile_id}
GET  /skills
POST /skills/apply
POST /workflows/novel-generation
GET  /workflows/{workflow_id}
POST /projects
GET  /projects
GET  /projects/{project_id}/outline
GET  /projects/{project_id}
GET  /projects/{project_id}/chapters
GET  /projects/{project_id}/chapters/{chapter_number}/content
POST /projects/{project_id}/chapters/{chapter_number}/confirm
POST /projects/{project_id}/chapters/{chapter_number}/draft
POST /projects/{project_id}/chapters/draft-batch
```
