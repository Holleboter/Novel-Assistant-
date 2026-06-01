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

`/outline` 主要用于生成和保存大纲；Workflow API 是一站式链路，会执行需求解析、蓝图生成、人物生成、第一章规划、章节草稿、质检、必要修订、图谱回写和文件保存。

当前 v1 是同步接口，并且只生成第一章。LLM 模式下可能耗时较长，前端应展示 loading，避免重复提交。

```bash
curl -X POST http://127.0.0.1:8000/workflows/novel-generation ^
  -H "Content-Type: application/json" ^
  -d "{\"project_id\":\"novel-demo\",\"user_input\":\"写一本雨夜悬疑小说\",\"save\":true,\"mode\":\"llm\",\"llm_profile\":\"deepseek-default\"}"
```

返回示例：

```json
{
  "workflow_id": "novel-demo-a1b2c3d4e5f6",
  "status": "completed",
  "project_id": "novel-demo",
  "project_path": "projects/novel-demo",
  "chapter_number": 1,
  "title": "Rain Letter",
  "passed": true,
  "artifacts": {
    "project_dir": "projects/novel-demo",
    "chapter_dir": "projects/novel-demo/chapters/chapter-0001"
  }
}
```

`save=false` 时仍会执行 LangGraph 编排和图谱写入，但不会把项目文件保存到本地目录。后续可以把这个同步接口升级为异步任务，使用 `workflow_id` 查询进度和运行记录。

当前 API 还支持：

```text
GET  /llm/profiles
POST /llm/profiles
PUT  /llm/profiles/{profile_id}
DELETE /llm/profiles/{profile_id}
POST /workflows/novel-generation
POST /projects
GET  /projects
GET  /projects/{project_id}/outline
GET  /projects/{project_id}
GET  /projects/{project_id}/chapters
POST /projects/{project_id}/chapters/{chapter_number}/draft
POST /projects/{project_id}/chapters/draft-batch
```
