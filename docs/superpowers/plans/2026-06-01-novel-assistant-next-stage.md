# Novel Assistant Next Stage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the next product stage for Novel Assistant: a usable frontend creation workbench, runtime model/Skill operation UI, graph center, and novel-world timeline visualization.

**Architecture:** Keep the existing FastAPI backend as the source of truth. Add a React + Vite + TypeScript frontend that calls existing APIs first, then extend backend APIs only where the UI needs new structured data. Neo4j-backed graph features remain behind service boundaries so the UI can work with exported graph/timeline JSON without depending on Cypher details.

**Tech Stack:** FastAPI, pytest, LangGraph, Neo4j, React, Vite, TypeScript, Tailwind CSS, React Flow or Cytoscape.js for graph/timeline visualization.

---

## Current Baseline

Implemented backend capabilities:

- Runtime LLM profile management.
- Project creation and project listing.
- Outline and chapter APIs.
- LangGraph novel-generation workflow.
- Workflow run status persistence.
- Skill loading and Skill-based polishing.
- Human-confirmed final chapter save as a custom `.md` file.

Existing important files:

- `src/novel_assistant/api.py`
- `src/novel_assistant/storage.py`
- `src/novel_assistant/workflow.py`
- `src/novel_assistant/workflow_runs.py`
- `src/novel_assistant/skills.py`
- `src/novel_assistant/llm_profiles.py`
- `tests/test_api.py`
- `tests/test_storage.py`
- `tests/test_workflow.py`
- `tests/test_workflow_runs.py`
- `tests/test_skills.py`
- `tests/test_llm_profiles.py`

---

## Product Direction

The next stage should deliver a real creative product, not only API demos.

Recommended page structure:

```text
Home / Project Hub
├─ Inspiration Assistant
├─ Project List
└─ Model / Skill quick status

Creation Workbench
├─ Left: chapter list
├─ Middle: Markdown editor
├─ Right: quality report / suggestions / character graph preview / workflow status
└─ Top: save final, re-QA, one-click polish, version/run history, Skill selector, filename input

Blueprint Center
├─ Novel premise
├─ Worldview
├─ Characters
├─ Outline
└─ Generation controls

Graph Center
├─ Character graph
├─ World graph
├─ Story timeline
├─ Chapter structure
└─ Foreshadowing table

Settings
├─ LLM profiles
├─ Skill management
└─ Neo4j connection status
```

---

## Subagent Assignment

### CoreAgent

Responsible for backend API contracts, workflow state, chapter confirmation, timeline event data, and quality report structures.

Primary files:

- `src/novel_assistant/api.py`
- `src/novel_assistant/storage.py`
- `src/novel_assistant/workflow.py`
- `src/novel_assistant/workflow_runs.py`
- `tests/test_api.py`
- `tests/test_storage.py`
- `tests/test_workflow.py`

### GraphAgent

Responsible for graph schema, timeline event model, Neo4j query/export design, and visualization-ready JSON.

Primary files:

- `src/novel_assistant/graph.py` if present in later implementation
- `src/novel_assistant/graph_store.py` if present in later implementation
- `src/novel_assistant/api.py`
- `tests/test_api.py`
- `docs/subagent-integrated-architecture.md`

### WritingAgent

Responsible for Skill polishing flow, AI flavor removal flow, quality report dimensions, suggestion output format, and final chapter content rules.

Primary files:

- `src/novel_assistant/skills.py`
- `src/novel_assistant/workflow.py`
- `src/novel_assistant/storage.py`
- `tests/test_skills.py`
- `tests/test_workflow.py`

### FrontendAgent

Responsible for React app shell, project hub, creation workbench, graph center, settings pages, API client, and interaction states.

Primary files to create:

- `frontend/package.json`
- `frontend/index.html`
- `frontend/src/main.tsx`
- `frontend/src/App.tsx`
- `frontend/src/api/client.ts`
- `frontend/src/pages/ProjectHub.tsx`
- `frontend/src/pages/CreationWorkbench.tsx`
- `frontend/src/pages/GraphCenter.tsx`
- `frontend/src/pages/Settings.tsx`
- `frontend/src/components/ChapterSidebar.tsx`
- `frontend/src/components/MarkdownEditor.tsx`
- `frontend/src/components/InspectorPanel.tsx`
- `frontend/src/components/WorkbenchToolbar.tsx`
- `frontend/src/components/WorkflowStatusTimeline.tsx`
- `frontend/src/components/StoryTimelineView.tsx`
- `frontend/src/styles.css`

---

## Phase 1: Frontend Foundation

**Goal:** Create a runnable frontend app connected to the existing backend.

**Files:**

- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/styles.css`
- Modify: `README.md`

- [ ] Create Vite React TypeScript app structure under `frontend/`.
- [ ] Add Tailwind CSS or a compact CSS token system.
- [ ] Add API base URL configuration through `VITE_API_BASE_URL`.
- [ ] Implement API client methods for existing backend endpoints:

```text
GET /projects
GET /projects/{project_id}
GET /projects/{project_id}/chapters
GET /projects/{project_id}/chapters/{chapter_number}/content
POST /projects/{project_id}/chapters/{chapter_number}/confirm
GET /skills
POST /skills/apply
GET /llm/profiles
GET /workflows/{workflow_id}
```

- [ ] Add loading, empty, and error states for all API calls.
- [ ] Run frontend build.
- [ ] Run backend tests.
- [ ] Commit as `feat: scaffold frontend app`.

Verification:

```powershell
python -m pytest -q
cd frontend
npm install
npm run build
```

Expected result:

```text
Backend tests pass.
Frontend production build completes.
```

---

## Phase 2: Project Hub With Inspiration Assistant

**Goal:** Give users a first screen where they can manage projects and talk with the assistant for story inspiration.

**Files:**

- Create: `frontend/src/pages/ProjectHub.tsx`
- Create: `frontend/src/components/InspirationAssistant.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/api/client.ts`
- Optionally modify: `src/novel_assistant/api.py`
- Test: `tests/test_api.py`

- [ ] Display project list from `GET /projects`.
- [ ] Show project title, status, chapter count, latest update time if available.
- [ ] Add entry action: open creation workbench.
- [ ] Add inspiration chat panel with local message state first.
- [ ] If backend ideation endpoint is needed, add `POST /assistant/ideation`.
- [ ] Keep ideation output separate from final project files until the user creates or updates a project.
- [ ] Commit as `feat: add project hub`.

Recommended ideation response shape:

```json
{
  "ideas": [
    {
      "title": "string",
      "premise": "string",
      "genre": "string",
      "main_conflict": "string",
      "suggested_next_action": "create_project"
    }
  ]
}
```

Verification:

```powershell
python -m pytest -q
cd frontend
npm run build
```

---

## Phase 3: Creation Workbench MVP

**Goal:** Build the main writing interface: chapter list, editable chapter body, right inspector, and top action bar.

**Files:**

- Create: `frontend/src/pages/CreationWorkbench.tsx`
- Create: `frontend/src/components/ChapterSidebar.tsx`
- Create: `frontend/src/components/MarkdownEditor.tsx`
- Create: `frontend/src/components/InspectorPanel.tsx`
- Create: `frontend/src/components/WorkbenchToolbar.tsx`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/App.tsx`

- [ ] Left panel: load chapter list.
- [ ] Middle panel: load selected chapter content.
- [ ] Middle panel: allow human editing without immediately saving final file.
- [ ] Top toolbar: add Skill selector, polish button, re-QA button, final filename input, confirm save button.
- [ ] Right panel: implement tabs:

```text
质检报告
修改建议
人物图谱
运行状态
```

- [ ] Confirm save calls `POST /projects/{project_id}/chapters/{chapter_number}/confirm`.
- [ ] Skill polish calls `POST /skills/apply` and replaces editor content only after user accepts.
- [ ] Commit as `feat: add creation workbench`.

Verification:

```powershell
cd frontend
npm run build
```

Manual checks:

- Open a project.
- Select a chapter.
- Edit text.
- Apply Skill polishing.
- Save final `.md` with a custom filename.
- Confirm the editor does not create multiple final files unless the user explicitly saves another filename.

---

## Phase 4: Workflow Status UI

**Goal:** Make LangGraph execution visible and understandable to users.

**Files:**

- Create: `frontend/src/components/WorkflowStatusTimeline.tsx`
- Modify: `frontend/src/components/InspectorPanel.tsx`
- Modify: `frontend/src/api/client.ts`
- Optionally modify: `src/novel_assistant/workflow_runs.py`
- Test: `tests/test_workflow_runs.py`

- [ ] Poll `GET /workflows/{workflow_id}` when a workflow id exists.
- [ ] Render workflow status as a vertical timeline:

```text
需求解析
蓝图生成
大纲生成
章节草稿
Skill 润色
质量检查
等待人工确认
最终保存
```

- [ ] Show `running`, `completed`, and `failed` states with clear labels.
- [ ] Display failed step error text in a collapsed details section.
- [ ] Add retry button only after backend retry API exists; before that, show disabled state with clear reason.
- [ ] Commit as `feat: show workflow status in workbench`.

Verification:

```powershell
python -m pytest -q
cd frontend
npm run build
```

---

## Phase 5: Graph Center MVP

**Goal:** Create a dedicated graph page instead of forcing all graph details into the right inspector.

**Files:**

- Create: `frontend/src/pages/GraphCenter.tsx`
- Create: `frontend/src/components/GraphView.tsx`
- Create: `frontend/src/components/GraphInspector.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/api/client.ts`
- Modify: `src/novel_assistant/api.py`
- Test: `tests/test_api.py`

- [ ] Add graph center route.
- [ ] Add tabs:

```text
人物图谱
世界图谱
剧情时间线
章节结构
伏笔线索
```

- [ ] Backend adds visualization-ready graph export endpoint:

```text
GET /projects/{project_id}/graph/view?view=characters
GET /projects/{project_id}/graph/view?view=world
GET /projects/{project_id}/graph/view?view=chapters
```

- [ ] Response shape:

```json
{
  "nodes": [
    {
      "id": "character:main",
      "label": "主角",
      "type": "Character",
      "summary": "string"
    }
  ],
  "edges": [
    {
      "id": "edge:1",
      "source": "character:main",
      "target": "faction:1",
      "label": "隶属",
      "type": "BELONGS_TO"
    }
  ]
}
```

- [ ] UI supports zoom, fit view, node click, and right-side detail.
- [ ] Large graphs must support filters by node type and relationship type.
- [ ] Commit as `feat: add graph center`.

Verification:

```powershell
python -m pytest -q
cd frontend
npm run build
```

---

## Phase 6: Story Timeline Visualization

**Goal:** Add a novel-world timeline view that tracks events, chapter order, foreshadowing, and continuity.

**Files:**

- Create: `frontend/src/components/StoryTimelineView.tsx`
- Modify: `frontend/src/pages/GraphCenter.tsx`
- Modify: `src/novel_assistant/api.py`
- Modify: `src/novel_assistant/storage.py`
- Test: `tests/test_api.py`
- Test: `tests/test_storage.py`

- [ ] Add timeline event storage support.
- [ ] Add timeline API:

```text
GET /projects/{project_id}/timeline
POST /projects/{project_id}/timeline/events
PUT /projects/{project_id}/timeline/events/{event_id}
DELETE /projects/{project_id}/timeline/events/{event_id}
```

- [ ] Timeline event shape:

```json
{
  "event_id": "evt_001",
  "title": "主角第一次获得线索",
  "summary": "主角发现旧案与当前危机有关。",
  "time_label": "第一卷 第三章",
  "sequence_order": 30,
  "chapter_number": 3,
  "event_type": "foreshadowing",
  "participants": ["char_main"],
  "location": "旧城区",
  "consequence": "引出幕后势力",
  "related_event_ids": ["evt_009"],
  "status": "planned"
}
```

- [ ] Timeline UI shows events by sequence order.
- [ ] Add filters:

```text
全部
主线
支线
伏笔
回收
人物成长
世界观
```

- [ ] Event click opens detail panel.
- [ ] Timeline event links to chapter number.
- [ ] Commit as `feat: add story timeline`.

Verification:

```powershell
python -m pytest -q
cd frontend
npm run build
```

Manual checks:

- Add event.
- Edit event.
- Delete event.
- Filter by event type.
- Open related chapter from event detail.

---

## Phase 7: Quality Report And Suggestion Linkage

**Goal:** Make quality checking actionable by linking report items to editor text, timeline events, characters, and graph nodes.

**Files:**

- Modify: `src/novel_assistant/workflow.py`
- Modify: `src/novel_assistant/api.py`
- Modify: `frontend/src/components/InspectorPanel.tsx`
- Modify: `frontend/src/components/MarkdownEditor.tsx`
- Modify: `frontend/src/components/StoryTimelineView.tsx`
- Test: `tests/test_workflow.py`
- Test: `tests/test_api.py`

- [ ] Standardize quality issue shape:

```json
{
  "issue_id": "issue_001",
  "severity": "high",
  "category": "timeline_conflict",
  "message": "第 5 章角色已经知道真相，但第 8 章仍表现为未知。",
  "evidence": "第 5 章结尾与第 8 章开头冲突。",
  "chapter_number": 8,
  "related_event_ids": ["evt_014", "evt_021"],
  "related_node_ids": ["character:main"],
  "suggestion": "调整第 8 章对话，使角色隐瞒真相而不是不知道真相。"
}
```

- [ ] Right inspector displays issues grouped by severity.
- [ ] Clicking a timeline-related issue highlights related timeline events.
- [ ] Clicking a graph-related issue opens graph node detail.
- [ ] Clicking a text-related issue scrolls editor to the paragraph when location data exists.
- [ ] Commit as `feat: link quality issues to story context`.

Verification:

```powershell
python -m pytest -q
cd frontend
npm run build
```

---

## Phase 8: Settings For LLM, Skill, And Neo4j

**Goal:** Let users configure runtime model profiles and inspect system readiness without editing `.env` for normal model switching.

**Files:**

- Create: `frontend/src/pages/Settings.tsx`
- Create: `frontend/src/components/LLMProfileSettings.tsx`
- Create: `frontend/src/components/SkillSettings.tsx`
- Create: `frontend/src/components/Neo4jStatus.tsx`
- Modify: `frontend/src/api/client.ts`
- Optionally modify: `src/novel_assistant/api.py`
- Test: `tests/test_api.py`

- [ ] List LLM profiles.
- [ ] Add, edit, delete runtime LLM profiles.
- [ ] Never display raw API keys after save.
- [ ] List installed Skills.
- [ ] Show Neo4j connection status.
- [ ] Add backend health endpoint if needed:

```text
GET /health
GET /graph/health
```

- [ ] Commit as `feat: add settings pages`.

Verification:

```powershell
python -m pytest -q
cd frontend
npm run build
```

---

## Phase 9: Documentation And Release Check

**Goal:** Make the project easy to run, verify, and continue.

**Files:**

- Modify: `README.md`
- Modify: `.env.example`
- Create: `docs/frontend-usage.md`
- Create: `docs/graph-and-timeline-design.md`

- [ ] Document backend startup.
- [ ] Document frontend startup.
- [ ] Document LLM profile configuration.
- [ ] Document Skill directory format.
- [ ] Document final chapter save behavior.
- [ ] Document graph and timeline concepts.
- [ ] Run full verification.
- [ ] Commit as `docs: add frontend and graph usage guide`.

Verification:

```powershell
python -m pytest -q
cd frontend
npm run build
git status --short --branch
```

Expected result:

```text
All tests pass.
Frontend build passes.
Git status shows only intentional changes before commit.
```

---

## Recommended Execution Order

1. Phase 1: Frontend Foundation.
2. Phase 3: Creation Workbench MVP.
3. Phase 8: Settings for LLM and Skill.
4. Phase 4: Workflow Status UI.
5. Phase 5: Graph Center MVP.
6. Phase 6: Story Timeline Visualization.
7. Phase 7: Quality Report And Suggestion Linkage.
8. Phase 2: Project Hub With Inspiration Assistant.
9. Phase 9: Documentation And Release Check.

Reason:

- The workbench is the core product surface.
- Settings are required before users can comfortably switch LLMs.
- Graph and timeline become more valuable once chapter editing exists.
- Inspiration assistant is useful, but it should not delay the main creative workflow.

---

## MVP Acceptance Criteria

The next MVP is complete when:

- User can open the frontend.
- User can view projects.
- User can open a project workbench.
- User can select a chapter.
- User can edit chapter content.
- User can apply a Skill polish operation.
- User can inspect quality report and suggestions.
- User can confirm-save one final `.md` file with a custom filename.
- User can view workflow run status.
- User can open graph center.
- User can view a story timeline with chapter-linked events.
- Backend tests pass.
- Frontend build passes.

---

## Risk Control

- Do not commit `.env`.
- Do not save raw API keys in frontend state longer than necessary.
- Do not generate many final chapter files automatically.
- Do not force full Neo4j graph rendering inside the editor right panel.
- Do not make the graph view depend on a running Neo4j instance for the first frontend MVP; support empty and fallback data states.
- Do not let Skill polishing overwrite human edits without confirmation.
- Do not treat timeline events as decorative UI; they must be usable by quality checking and future generation context.

