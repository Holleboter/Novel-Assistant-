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

当前 API 还支持：

```text
GET  /projects/{project_id}
GET  /projects/{project_id}/chapters
POST /projects/{project_id}/chapters/{chapter_number}/draft
```
