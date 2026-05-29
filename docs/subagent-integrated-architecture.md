# Novel-Assistant Subagent 整合方案

## 1. 目标

本文件整理三个 subagent 的职责、设计产出和接口边界，作为 Novel-Assistant 第一阶段开发的统一架构依据。

当前三个 subagent：

```text
CoreAgent    -> Core / LangGraph Agent
GraphAgent   -> Graph / Neo4j Agent
WritingAgent -> Writing Pipeline Agent
```

项目第一阶段目标：

```text
用户创意
-> 小说蓝图
-> 人物 / 世界观 / 大纲
-> Neo4j 图谱写入
-> 第一章计划
-> 图谱上下文检索
-> 第一章正文生成
-> 质检
-> 自动修订
-> 章节事实抽取
-> Neo4j 图谱回写
```

## 2. 总体架构

```text
              +--------------------+
              |      User Input     |
              +----------+---------+
                         |
                         v
              +--------------------+
              |     CoreAgent       |
              | LangGraph Workflow  |
              +----+-----------+---+
                   |           |
       calls       |           | calls
                   v           v
        +----------------+   +----------------------+
        |   GraphAgent   |   |    WritingAgent      |
        | Neo4j Graph    |   | Generation / QC      |
        +-------+--------+   +----------+-----------+
                |                       |
                v                       v
        +---------------+       +------------------+
        |     Neo4j     |       | Chapter Artifacts |
        | Knowledge DB  |       | Reports / Deltas  |
        +---------------+       +------------------+
```

分工原则：

- CoreAgent 只负责编排，不直接写 Cypher，不直接写生成 prompt 细节。
- GraphAgent 只负责图谱建模、查询、写入、可视化导出，不生成正文。
- WritingAgent 只负责结构化创作、质检、修订、事实抽取，不直接操作 Neo4j。

## 3. CoreAgent 方案整理

### 3.1 负责范围

CoreAgent 负责 LangGraph 工作流、状态结构、节点编排、人工确认点和失败恢复。

核心模块建议：

```text
src/novel_assistant/workflow.py
src/novel_assistant/models.py
src/novel_assistant/ports/graph_store.py
src/novel_assistant/ports/writing_pipeline.py
src/novel_assistant/services/context_builder.py
```

### 3.2 LangGraph 节点

第一阶段节点：

```text
analyze_requirement
generate_blueprint
generate_characters
generate_worldview
write_initial_graph
generate_outline
confirm_story_direction
prepare_chapter_plan
retrieve_chapter_context
write_chapter
quality_check
revise_chapter
extract_state_delta
update_long_term_state
finalize_run
```

第一版可先简化为：

```text
analyze_requirement
generate_blueprint
generate_characters
write_initial_graph
prepare_chapter_plan
write_chapter
quality_check
revise_or_accept
extract_graph_delta
update_graph
```

### 3.3 状态字段

`NovelAgentState` 至少包含：

```text
run_id
project_id
user_input
requirement
blueprint
characters
relationships
world_rules
outline
chapter_plans
current_chapter_plan
retrieved_context
chapter_draft
quality_report
revised_chapter
final_chapter
graph_delta
state_delta
graph_write_result
graph_update_result
errors
node_logs
artifacts
```

### 3.4 CoreAgent 对外依赖

依赖 GraphAgent：

```python
create_or_update_story_graph(request)
get_context_for_chapter(request)
apply_graph_delta(delta)
export_graph_view(project_id, view)
detect_graph_conflicts(delta)
```

依赖 WritingAgent：

```python
draft_chapter(request)
quality_check(request)
revise_chapter(request)
extract_chapter_delta(request)
```

## 4. GraphAgent 方案整理

### 4.1 负责范围

GraphAgent 负责 Neo4j 图谱 schema、仓储层接口、写入策略、查询接口、图谱 delta 校验和可视化导出。

不负责：

```text
LangGraph 编排
章节正文生成
质检评分规则
自动修订正文
前端 UI 实现
```

### 4.2 Neo4j 节点类型

第一阶段核心节点：

```text
Novel
Character
Faction
Location
WorldRule
Arc
Chapter
Event
Hook
Theme
GraphDelta
```

节点字段摘要：

```text
Novel:
  novel_id, title, genre, status, premise, worldview_summary,
  main_conflict, target_chapters, chapter_word_count

Character:
  character_id, novel_id, name, role, goal, motivation,
  weakness, growth_arc, current_state, emotional_state, status

Chapter:
  chapter_id, novel_id, chapter_number, title, goal,
  summary, word_count, status, quality_score

Event:
  event_id, novel_id, chapter_id, title, summary,
  event_type, sequence_order, consequence, certainty, source

Hook:
  hook_id, novel_id, title, description, status,
  planted_chapter, expected_resolution_chapter, resolved_chapter, importance
```

### 4.3 Neo4j 关系类型

小说归属关系：

```text
(:Novel)-[:HAS_CHARACTER]->(:Character)
(:Novel)-[:HAS_FACTION]->(:Faction)
(:Novel)-[:HAS_LOCATION]->(:Location)
(:Novel)-[:HAS_WORLD_RULE]->(:WorldRule)
(:Novel)-[:HAS_ARC]->(:Arc)
(:Novel)-[:HAS_CHAPTER]->(:Chapter)
(:Novel)-[:HAS_HOOK]->(:Hook)
(:Novel)-[:HAS_THEME]->(:Theme)
```

人物关系：

```text
(:Character)-[:ALLY_OF]->(:Character)
(:Character)-[:ENEMY_OF]->(:Character)
(:Character)-[:MENTOR_OF]->(:Character)
(:Character)-[:RELATED_TO]->(:Character)
(:Character)-[:BELONGS_TO]->(:Faction)
(:Character)-[:LOCATED_AT]->(:Location)
```

章节与事件关系：

```text
(:Arc)-[:HAS_CHAPTER]->(:Chapter)
(:Chapter)-[:CONTAINS_EVENT]->(:Event)
(:Chapter)-[:ADVANCES_HOOK]->(:Hook)
(:Chapter)-[:RESOLVES_HOOK]->(:Hook)
(:Chapter)-[:USES_WORLD_RULE]->(:WorldRule)
(:Event)-[:INVOLVES]->(:Character)
(:Event)-[:OCCURS_AT]->(:Location)
(:Event)-[:CAUSES]->(:Event)
(:Event)-[:ADVANCES_HOOK]->(:Hook)
(:Event)-[:CHANGES_STATE_OF]->(:Character)
```

伏笔关系：

```text
(:Hook)-[:PLANTED_IN]->(:Chapter)
(:Hook)-[:ADVANCED_IN]->(:Chapter)
(:Hook)-[:RESOLVED_IN]->(:Chapter)
```

### 4.4 GraphRepository 接口

第一阶段仓储接口：

```python
class GraphRepository:
    def health_check(self) -> bool: ...
    def close(self) -> None: ...
    def ensure_constraints(self) -> None: ...

    def create_novel(self, novel: NovelCreate) -> NovelRead: ...
    def upsert_novel_blueprint(self, novel_id: str, blueprint: StoryBlueprint) -> None: ...
    def get_novel_context(self, novel_id: str) -> NovelContext: ...

    def upsert_character(self, novel_id: str, character: CharacterProfile) -> CharacterRead: ...
    def list_characters(self, novel_id: str) -> list[CharacterRead]: ...
    def update_character_state(self, novel_id: str, change: CharacterStateChange) -> None: ...

    def upsert_chapter_plan(self, novel_id: str, chapter: ChapterPlan) -> ChapterRead: ...
    def upsert_chapter_summary(self, novel_id: str, summary: ChapterSummary) -> None: ...
    def add_chapter_events(self, novel_id: str, chapter_id: str, events: list[EventModel]) -> list[EventRead]: ...

    def upsert_hook(self, novel_id: str, hook: HookModel) -> HookRead: ...
    def advance_hook(self, novel_id: str, hook_id: str, chapter_id: str, note: str) -> None: ...
    def resolve_hook(self, novel_id: str, hook_id: str, chapter_id: str, note: str) -> None: ...

    def validate_delta(self, delta: GraphDelta) -> ValidationResult: ...
    def apply_delta(self, delta: GraphDelta) -> ApplyResult: ...

    def get_relevant_context_for_chapter(
        self,
        novel_id: str,
        chapter_number: int,
        character_ids: list[str] | None = None,
        hook_ids: list[str] | None = None,
    ) -> ChapterGraphContext: ...

    def export_visualization_graph(
        self,
        novel_id: str,
        view: str,
        filters: GraphViewFilter,
    ) -> GraphVisualization: ...
```

### 4.5 约束和索引

第一版约束：

```cypher
CREATE CONSTRAINT novel_id_unique IF NOT EXISTS
FOR (n:Novel)
REQUIRE n.novel_id IS UNIQUE;

CREATE CONSTRAINT character_id_unique IF NOT EXISTS
FOR (c:Character)
REQUIRE c.character_id IS UNIQUE;

CREATE CONSTRAINT chapter_id_unique IF NOT EXISTS
FOR (c:Chapter)
REQUIRE c.chapter_id IS UNIQUE;

CREATE CONSTRAINT event_id_unique IF NOT EXISTS
FOR (e:Event)
REQUIRE e.event_id IS UNIQUE;

CREATE CONSTRAINT hook_id_unique IF NOT EXISTS
FOR (h:Hook)
REQUIRE h.hook_id IS UNIQUE;
```

第一版索引：

```cypher
CREATE INDEX character_by_novel_name IF NOT EXISTS
FOR (c:Character)
ON (c.novel_id, c.name);

CREATE INDEX chapter_by_novel_number IF NOT EXISTS
FOR (c:Chapter)
ON (c.novel_id, c.chapter_number);

CREATE INDEX hook_by_novel_status IF NOT EXISTS
FOR (h:Hook)
ON (h.novel_id, h.status);
```

### 4.6 图谱安全写入原则

```text
LLM 不持有 Neo4j Driver。
LLM 不输出 Cypher。
LLM 只能输出 BlueprintGraphDelta 或 ChapterGraphDelta。
delta 必须经过 Pydantic 校验、引用校验、枚举校验、状态机校验。
低置信度事实只记录 certainty，不直接覆盖主节点当前态。
关系变化不删除旧关系，而是设置旧关系 status = ended。
所有写入必须记录 source_type、source_id、chapter_number。
```

### 4.7 可视化导出格式

统一导出结构：

```json
{
  "novel_id": "novel_001",
  "view": "character_network",
  "generated_at": "2026-05-29T10:00:00+08:00",
  "nodes": [
    {
      "id": "char_001",
      "label": "Character",
      "type": "Character",
      "display_name": "林澈",
      "group": "protagonist",
      "status": "active",
      "properties": {
        "role": "protagonist",
        "goal": "查明王城失火真相"
      }
    }
  ],
  "edges": [
    {
      "id": "edge_char_001_char_002_ally",
      "source": "char_001",
      "target": "char_002",
      "type": "ALLY_OF",
      "label": "盟友",
      "direction": "undirected",
      "properties": {
        "since_chapter": 3,
        "strength": 0.8,
        "status": "active"
      }
    }
  ],
  "metadata": {
    "node_count": 12,
    "edge_count": 18
  }
}
```

第一阶段支持三种视图：

```text
character_network
hook_tracker
chapter_timeline
```

## 5. WritingAgent 方案整理

### 5.1 负责范围

WritingAgent 负责小说生成链路、结构化输出、章节质检、自动修订和章节后事实抽取。

不负责：

```text
LangGraph 编排
Neo4j 内部实现
Cypher 编写
前端展示
```

### 5.2 写作流水线

```text
需求解析
-> 小说蓝图生成
-> 人物设定生成
-> 世界观设定生成
-> 故事大纲生成
-> 章节计划生成
-> 章节正文生成
-> 章节质检
-> 自动修订
-> 章节后事实抽取
-> GraphDelta 输出
```

### 5.3 结构化输出

核心 schema：

```text
RequirementAnalysis
StoryBlueprint
CharacterProfile
WorldviewSpec
OutlinePlan
ChapterPlan
ChapterDraft
QualityReport
RevisionInstruction
RevisedChapterDraft
ChapterFactExtraction
GraphDelta
```

### 5.4 质检维度

第一版质检维度：

```text
character_consistency
worldview_consistency
relationship_consistency
event_causality
hook_progression
outline_alignment
pacing
repetition
ai_flavor
sensitive_content
```

问题严重度：

```text
low
medium
high
blocking
```

阻断规则：

```text
人设严重冲突 -> blocking
世界观硬规则冲突 -> blocking
主线因果不成立 -> blocking
敏感内容风险 -> blocking
关键伏笔漏推进 -> high
明显偏离大纲 -> high
节奏拖沓 / AI 味强 -> medium
局部措辞问题 -> low
```

### 5.5 修订模式

```text
local_fix        局部事实错误、称谓错误、单点逻辑错误
polish           表达增强、画面感、情绪推进
pace_compression 节奏压缩、删除重复解释
plot_rewrite     情节结构重写
de_ai            去 AI 味、减少模板化表达
```

### 5.6 章节后事实抽取

章节后输出：

```text
chapter_summary
character_state_changes
relationship_changes
new_events
new_hooks
advanced_hooks
resolved_hooks
location_changes
world_rule_mentions
confidence_notes
```

GraphDelta 原则：

```text
只新增或补充明确事实。
状态更新必须带来源章节和证据短句。
禁止模型删除节点。
关系变化追加状态，不直接覆盖历史。
伏笔状态分为 planted、advanced、resolved、dropped_risk。
```

## 6. 三方接口边界

### 6.1 CoreAgent -> GraphAgent

```python
graph_repository.ensure_constraints()
graph_repository.upsert_novel_blueprint(novel_id, blueprint)
graph_repository.upsert_character(novel_id, character)
graph_repository.get_relevant_context_for_chapter(novel_id, chapter_number, character_ids, hook_ids)
graph_repository.validate_delta(delta)
graph_repository.apply_delta(delta)
graph_repository.export_visualization_graph(novel_id, view, filters)
```

### 6.2 CoreAgent -> WritingAgent

```python
writing_pipeline.analyze_requirement(user_input)
writing_pipeline.generate_blueprint(requirement)
writing_pipeline.generate_characters(blueprint)
writing_pipeline.generate_worldview(blueprint)
writing_pipeline.generate_outline(blueprint, characters, worldview)
writing_pipeline.plan_chapter(outline, graph_context)
writing_pipeline.draft_chapter(chapter_plan, graph_context)
writing_pipeline.quality_check(chapter_draft, chapter_plan, graph_context)
writing_pipeline.revise_chapter(chapter_draft, quality_report)
writing_pipeline.extract_chapter_delta(final_chapter)
```

### 6.3 WritingAgent -> GraphAgent

WritingAgent 不直接调用 GraphAgent。它只通过 CoreAgent 间接获取图谱上下文和提交 GraphDelta。

原因：

```text
避免写作链路绕过状态机。
保证所有图谱写入都有流程记录。
方便人工确认、失败重试和审计。
```

## 7. 第一阶段 MVP 执行顺序

### M1：项目骨架

交付：

```text
pyproject.toml
src/novel_assistant/
tests/
.env.example
```

验收：

```text
pytest -q 可以运行
包可以被 import
```

### M2：模型层

交付：

```text
UserRequirement
StoryBlueprint
CharacterProfile
ChapterPlan
ChapterDraft
QualityReport
RevisedChapterDraft
GraphDelta
```

验收：

```text
所有核心模型有单元测试
质检报告能自动判断 passed / revision_required
```

### M3：Neo4j 图谱层

交付：

```text
GraphRepository
health_check
ensure_constraints
upsert_initial_graph
apply_delta
export_visualization_graph
```

验收：

```text
能连接 yubei-neo4j
能写入 Novel / Character / Chapter / Event / Hook
能执行基础查询
```

### M4：写作流水线 MVP

交付：

```text
DeterministicWritingPipeline
draft_chapter
quality_check
revise_chapter
extract_graph_delta
```

验收：

```text
输入 ChapterPlan 能得到 ChapterDraft
输入 ChapterDraft 能得到 QualityReport
质量不通过时能得到 RevisedChapterDraft
最终章节能抽取 GraphDelta
```

### M5：LangGraph 工作流

交付：

```text
NovelAgentState
build_workflow
initial_state
```

验收：

```text
输入一句小说创意
能走完蓝图 -> 人物 -> 图谱写入 -> 章节计划 -> 正文 -> 质检 -> 图谱回写
```

### M6：Demo 与文档

交付：

```text
python -m novel_assistant.demo
README.md
```

验收：

```text
demo 能输出第一章标题和正文片段
Neo4j 中能查到 Novel / Character / Chapter / Event 节点
```

## 8. 推荐 subagent 执行分工

### CoreAgent

执行：

```text
models.py 中与流程状态相关的模型
workflow.py
demo.py
workflow 测试
```

### GraphAgent

执行：

```text
graph_repository.py
Neo4j 约束和索引
图谱写入测试
图谱导出测试
```

### WritingAgent

执行：

```text
writing_pipeline.py
质量报告模型细化
章节生成测试
修订测试
GraphDelta 抽取测试
```

主 agent 负责：

```text
接口合并
测试整合
最终验收
README 和计划文档更新
```

## 9. 当前已落地文档

```text
docs/project-planning-report.md
docs/superpowers/plans/2026-05-29-novel-assistant-mvp.md
docs/subagent-integrated-architecture.md
```

## 10. 下一步建议

推荐采用 Subagent-Driven 执行：

```text
1. 主 agent 创建实现分支。
2. CoreAgent、GraphAgent、WritingAgent 按文件边界并行实现。
3. 主 agent 收敛接口命名和模型字段。
4. 跑 pytest。
5. 跑 Neo4j demo。
6. 更新 README。
7. 提交第一版 MVP。
```

第一轮实现要克制，只跑通一章闭环。不要在第一轮加入 Web UI、真实 LLM、多模型路由、EPUB 导出或复杂前端图谱。
