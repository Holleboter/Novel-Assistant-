from pathlib import Path

from fastapi.testclient import TestClient

import novel_assistant.api as api_module
from novel_assistant.api import create_app
from novel_assistant.llm_profiles import LLMProfile
from novel_assistant.models import (
    ChapterDraft,
    ChapterPlan,
    CharacterProfile,
    GraphDelta,
    QualityReport,
    StoryBlueprint,
    UserRequirement,
)


class FakeProfileStore:
    def __init__(self, profiles=None):
        self.profiles = dict(profiles or {})
        self.calls = []

    def list(self):
        self.calls.append(("list",))
        return list(self.profiles.values())

    def get(self, profile_id):
        self.calls.append(("get", profile_id))
        return self.profiles.get(profile_id)

    def upsert(self, profile):
        self.calls.append(("upsert", profile))
        self.profiles[profile.id] = profile
        return profile

    def delete(self, profile_id):
        self.calls.append(("delete", profile_id))
        return self.profiles.pop(profile_id, None) is not None


class FakeGraphRepository:
    def __init__(self):
        self.initial_writes = []
        self.delta_writes = []

    def ensure_constraints(self):
        return None

    def upsert_initial_graph(self, project_id, blueprint, characters):
        self.initial_writes.append(
            {
                "project_id": project_id,
                "blueprint": blueprint,
                "characters": characters,
            }
        )

    def apply_delta(self, delta):
        self.delta_writes.append(delta)


class SpyPlanner:
    def __init__(self):
        self.calls = []

    def analyze_requirement(self, user_input):
        self.calls.append(("analyze_requirement", user_input))
        return UserRequirement(
            premise=user_input,
            genre="suspense",
            target_audience="adult",
            themes=["truth"],
            constraints=[],
        )

    def build_blueprint(self, requirement):
        self.calls.append(("build_blueprint", requirement.premise))
        return StoryBlueprint(
            title="Rain Letter",
            logline="A detective receives a future letter on a rainy night.",
            setting="Old river city",
            central_conflict="Save a friend or expose the citywide secret.",
            themes=requirement.themes,
        )

    def build_characters(self, requirement, blueprint):
        self.calls.append(("build_characters", requirement.premise, blueprint.title))
        return [
            CharacterProfile(
                name="Lin",
                role="Protagonist",
                motivation="Find the truth",
                arc="From avoidance to responsibility",
                traits=["careful"],
            )
        ]

    def plan_chapters(self, requirement, blueprint, characters, chapter_count=12):
        self.calls.append(
            (
                "plan_chapters",
                requirement.premise,
                blueprint.title,
                characters[0].name,
                chapter_count,
            )
        )
        return [
            ChapterPlan(
                chapter_number=number,
                title=f"Chapter {number}",
                goal="Follow the clue",
                key_events=["The rain starts"],
                pov_character=characters[0].name,
            )
            for number in range(1, chapter_count + 1)
        ]

    def plan_chapter(self, requirement, blueprint, characters):
        self.calls.append(("plan_chapter", requirement.premise, blueprint.title))
        return ChapterPlan(
            chapter_number=1,
            title="Chapter 1",
            goal="Follow the clue",
            key_events=["The rain starts"],
            pov_character=characters[0].name,
        )


def test_health_returns_ok():
    client = TestClient(create_app(planner=SpyPlanner()))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_outline_runs_planner_and_saves_to_configured_storage_root(tmp_path):
    planner = SpyPlanner()
    client = TestClient(create_app(planner=planner, storage_root=tmp_path))

    response = client.post(
        "/outline",
        json={
            "project_id": "novel-demo",
            "user_input": "写一本雨夜悬疑小说",
            "chapter_count": 3,
            "save": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["project_id"] == "novel-demo"
    assert payload["blueprint"]["title"] == "Rain Letter"
    assert payload["characters"][0]["name"] == "Lin"
    assert [chapter["chapter_number"] for chapter in payload["outline"]] == [1, 2, 3]
    assert payload["outline_path"] == str(tmp_path / "novel-demo" / "outline.json")
    assert Path(payload["outline_path"]).exists()
    assert not (Path("projects") / "novel-demo" / "outline.json").exists()
    assert planner.calls == [
        ("analyze_requirement", "写一本雨夜悬疑小说"),
        ("build_blueprint", "写一本雨夜悬疑小说"),
        ("build_characters", "写一本雨夜悬疑小说", "Rain Letter"),
        ("plan_chapters", "写一本雨夜悬疑小说", "Rain Letter", "Lin", 3),
    ]


def test_outline_rejects_invalid_chapter_count():
    client = TestClient(create_app(planner=SpyPlanner()))

    response = client.post(
        "/outline",
        json={
            "project_id": "novel-demo",
            "user_input": "写一本雨夜悬疑小说",
            "chapter_count": 0,
            "save": False,
        },
    )

    assert response.status_code == 422


def test_llm_profile_crud_returns_sanitized_profiles():
    store = FakeProfileStore(
        {
            "default": LLMProfile(
                id="default",
                name="Default",
                provider="deepseek",
                model="deepseek-chat",
                api_key="secret",
                base_url=None,
            )
        }
    )
    client = TestClient(create_app(planner=SpyPlanner(), profile_store=store))

    list_response = client.get("/llm/profiles")
    create_response = client.post(
        "/llm/profiles",
        json={
            "profile_id": "qwen",
            "name": "Qwen Plus",
            "provider": "qwen",
            "model": "qwen-plus",
            "api_key": "another-secret",
            "base_url": "https://example.test/v1",
            "temperature": 0.4,
            "max_tokens": 3200,
            "timeout_seconds": 60,
        },
    )

    assert list_response.status_code == 200
    assert list_response.json() == [
        {
            "id": "default",
            "name": "Default",
            "provider": "deepseek",
            "model": "deepseek-chat",
            "base_url": None,
            "api_key_set": True,
            "temperature": 0.7,
            "max_tokens": 4000,
            "timeout_seconds": 120,
        }
    ]
    assert "api_key" not in create_response.json()
    assert create_response.json()["api_key_set"] is True
    assert create_response.json()["temperature"] == 0.4
    assert store.profiles["qwen"].api_key == "another-secret"
    update_response = client.put(
        "/llm/profiles/qwen",
        json={
            "name": "Qwen Max",
            "provider": "qwen",
            "model": "qwen-max",
            "api_key": None,
            "base_url": None,
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["id"] == "qwen"
    assert update_response.json()["name"] == "Qwen Max"
    assert update_response.json()["model"] == "qwen-max"
    assert update_response.json()["api_key_set"] is False
    assert update_response.json()["temperature"] == 0.4
    assert store.profiles["qwen"].api_key is None
    delete_response = client.delete("/llm/profiles/qwen")
    assert delete_response.status_code == 204


def test_update_llm_profile_preserves_existing_api_key_when_omitted():
    store = FakeProfileStore(
        {
            "default": LLMProfile(
                id="default",
                name="Default",
                provider="deepseek",
                model="deepseek-chat",
                api_key="secret",
                temperature=0.2,
                max_tokens=2000,
                timeout_seconds=30,
            )
        }
    )
    client = TestClient(create_app(planner=SpyPlanner(), profile_store=store))

    response = client.put(
        "/llm/profiles/default",
        json={
            "provider": "deepseek",
            "model": "deepseek-reasoner",
        },
    )

    assert response.status_code == 200
    assert response.json()["api_key_set"] is True
    assert response.json()["temperature"] == 0.2
    assert store.profiles["default"].api_key == "secret"


def test_update_llm_profile_returns_404_when_profile_is_missing():
    client = TestClient(create_app(planner=SpyPlanner(), profile_store=FakeProfileStore()))

    response = client.put(
        "/llm/profiles/missing",
        json={"provider": "qwen", "model": "qwen-plus", "api_key": "secret"},
    )

    assert response.status_code == 404


def test_outline_uses_llm_profile_when_mode_is_llm(monkeypatch):
    store = FakeProfileStore(
        {
            "default": LLMProfile(
                id="default",
                name="Default",
                provider="deepseek",
                model="deepseek-chat",
                api_key="secret",
            )
        }
    )
    factory_calls = []
    planner_clients = []

    def fake_llm_client_factory(profile):
        factory_calls.append(profile)
        return "fake-client"

    class FakeLLMStoryPlanner(SpyPlanner):
        def __init__(self, llm_client):
            super().__init__()
            planner_clients.append(llm_client)

    monkeypatch.setattr(api_module, "LLMBackedStoryPlanner", FakeLLMStoryPlanner)
    client = TestClient(
        create_app(
            planner=SpyPlanner(),
            profile_store=store,
            llm_client_factory=fake_llm_client_factory,
        )
    )

    response = client.post(
        "/outline",
        json={
            "project_id": "novel-demo",
            "user_input": "write a mystery",
            "chapter_count": 2,
            "mode": "llm",
            "llm_profile": "default",
        },
    )

    assert response.status_code == 200
    assert planner_clients == ["fake-client"]
    assert factory_calls == [store.profiles["default"]]
    assert [chapter["chapter_number"] for chapter in response.json()["outline"]] == [1, 2]


def test_outline_returns_404_when_llm_profile_is_missing():
    client = TestClient(
        create_app(
            planner=SpyPlanner(),
            profile_store=FakeProfileStore(),
            llm_client_factory=lambda profile: "fake-client",
        )
    )

    response = client.post(
        "/outline",
        json={
            "project_id": "novel-demo",
            "user_input": "write a mystery",
            "mode": "llm",
            "llm_profile": "missing",
        },
    )

    assert response.status_code == 404


def test_novel_generation_workflow_runs_graph_and_saves_artifacts(tmp_path):
    repo = FakeGraphRepository()
    client = TestClient(
        create_app(
            planner=SpyPlanner(),
            writing_pipeline=FakeWritingPipeline(),
            storage_root=tmp_path,
            graph_repository=repo,
        )
    )

    response = client.post(
        "/workflows/novel-generation",
        json={
            "project_id": "novel-demo",
            "user_input": "write a rainy mystery",
            "chapter_count": 3,
            "start_chapter": 1,
            "end_chapter": 2,
            "save": True,
        },
    )
    projects_response = client.get("/projects")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["workflow_id"]
    assert payload["project_id"] == "novel-demo"
    assert payload["project_path"] == str(tmp_path / "novel-demo")
    assert payload["chapter_count"] == 3
    assert payload["generated_chapter_count"] == 2
    assert payload["chapter_number"] == 1
    assert payload["title"] == "Chapter 1"
    assert payload["passed"] is True
    assert [chapter["chapter_number"] for chapter in payload["chapters"]] == [1, 2]
    assert payload["artifacts"]["outline_path"] == str(
        tmp_path / "novel-demo" / "outline.json"
    )
    assert payload["artifacts"]["chapter_dir"] == str(
        tmp_path / "novel-demo" / "chapters" / "chapter-0001"
    )
    assert (tmp_path / "novel-demo" / "project.json").exists()
    assert (tmp_path / "novel-demo" / "blueprint.json").exists()
    assert (tmp_path / "novel-demo" / "outline.json").exists()
    assert (tmp_path / "novel-demo" / "chapters" / "chapter-0001" / "final.md").exists()
    assert (tmp_path / "novel-demo" / "chapters" / "chapter-0002" / "final.md").exists()
    assert projects_response.json()[0]["has_outline"] is True
    assert projects_response.json()[0]["chapter_count"] == 2
    assert repo.initial_writes[0]["project_id"] == "novel-demo"
    assert len(repo.delta_writes) == 2


def test_novel_generation_workflow_can_run_without_saving(tmp_path):
    repo = FakeGraphRepository()
    client = TestClient(
        create_app(
            planner=SpyPlanner(),
            writing_pipeline=FakeWritingPipeline(),
            storage_root=tmp_path,
            graph_repository=repo,
        )
    )

    response = client.post(
        "/workflows/novel-generation",
        json={
            "project_id": "novel-demo",
            "user_input": "write a rainy mystery",
            "chapter_count": 2,
            "start_chapter": 1,
            "end_chapter": 2,
            "save": False,
        },
    )

    assert response.status_code == 200
    assert response.json()["project_path"] is None
    assert response.json()["generated_chapter_count"] == 2
    assert not (tmp_path / "novel-demo").exists()
    assert repo.initial_writes
    assert len(repo.delta_writes) == 2


def test_create_project_persists_metadata_and_list_projects_returns_summary(tmp_path):
    client = TestClient(create_app(planner=SpyPlanner(), storage_root=tmp_path))

    create_response = client.post(
        "/projects",
        json={"project_id": "novel-demo", "title": "Rain Letter"},
    )
    list_response = client.get("/projects")

    assert create_response.status_code == 201
    assert create_response.json() == {
        "project_id": "novel-demo",
        "title": "Rain Letter",
        "project_path": str(tmp_path / "novel-demo"),
        "has_outline": False,
        "chapter_count": 0,
    }
    assert (tmp_path / "novel-demo" / "project.json").exists()
    assert list_response.status_code == 200
    assert list_response.json() == [
        {
            "project_id": "novel-demo",
            "title": "Rain Letter",
            "has_outline": False,
            "outline_path": None,
            "chapter_count": 0,
        }
    ]


def test_create_project_returns_409_when_project_exists(tmp_path):
    client = TestClient(create_app(planner=SpyPlanner(), storage_root=tmp_path))
    client.post("/projects", json={"project_id": "novel-demo", "title": "Rain Letter"})

    response = client.post(
        "/projects",
        json={"project_id": "novel-demo", "title": "Rain Letter Again"},
    )

    assert response.status_code == 409


def test_get_project_outline_returns_saved_outline(tmp_path):
    project_dir = tmp_path / "novel-demo"
    project_dir.mkdir()
    outline_path = project_dir / "outline.json"
    outline_path.write_text(
        """[
          {
            "chapter_number": 1,
            "title": "Rain Letter",
            "goal": "Find the first clue",
            "key_events": ["Lights fail"],
            "pov_character": "Lin"
          }
        ]""",
        encoding="utf-8",
    )
    client = TestClient(create_app(planner=SpyPlanner(), storage_root=tmp_path))

    response = client.get("/projects/novel-demo/outline")

    assert response.status_code == 200
    assert response.json() == [
        {
            "chapter_number": 1,
            "title": "Rain Letter",
            "goal": "Find the first clue",
            "key_events": ["Lights fail"],
            "pov_character": "Lin",
        }
    ]


def test_get_project_returns_404_when_project_directory_is_missing(tmp_path):
    client = TestClient(create_app(planner=SpyPlanner(), storage_root=tmp_path))

    response = client.get("/projects/missing-project")

    assert response.status_code == 404


def test_get_project_returns_outline_status_and_chapters(tmp_path, monkeypatch):
    project_dir = tmp_path / "novel-demo"
    project_dir.mkdir()
    outline_path = project_dir / "outline.json"
    outline_path.write_text("[]", encoding="utf-8")
    monkeypatch.setattr(
        api_module,
        "list_chapters",
        lambda project_id, root: [{"chapter_number": 1, "title": "Chapter 1"}],
    )
    client = TestClient(create_app(planner=SpyPlanner(), storage_root=tmp_path))

    response = client.get("/projects/novel-demo")

    assert response.status_code == 200
    assert response.json() == {
        "project_id": "novel-demo",
        "has_outline": True,
        "outline_path": str(outline_path),
        "chapters": [{"chapter_number": 1, "title": "Chapter 1"}],
    }


def test_get_project_chapters_returns_storage_list(tmp_path, monkeypatch):
    (tmp_path / "novel-demo").mkdir()
    monkeypatch.setattr(
        api_module,
        "list_chapters",
        lambda project_id, root: [{"chapter_number": 2, "title": "Second"}],
    )
    client = TestClient(create_app(planner=SpyPlanner(), storage_root=tmp_path))

    response = client.get("/projects/novel-demo/chapters")

    assert response.status_code == 200
    assert response.json() == [{"chapter_number": 2, "title": "Second"}]


def test_post_chapter_draft_generates_and_saves_artifacts(tmp_path, monkeypatch):
    project_dir = tmp_path / "novel-demo"
    project_dir.mkdir()
    (project_dir / "outline.json").write_text(
        """[
          {
            "chapter_number": 1,
            "title": "Rain Letter",
            "goal": "Find the first clue",
            "key_events": ["Lights fail"],
            "pov_character": "Lin"
          }
        ]""",
        encoding="utf-8",
    )
    save_calls = []

    def fake_save_chapter_artifacts(**kwargs):
        save_calls.append(kwargs)
        return tmp_path / "novel-demo" / "chapters" / "chapter-0001"

    monkeypatch.setattr(api_module, "save_chapter_artifacts", fake_save_chapter_artifacts)
    pipeline = FakeWritingPipeline()
    client = TestClient(
        create_app(
            planner=SpyPlanner(),
            storage_root=tmp_path,
            writing_pipeline=pipeline,
        )
    )

    response = client.post("/projects/novel-demo/chapters/1/draft")

    assert response.status_code == 200
    assert response.json() == {
        "chapter_number": 1,
        "title": "Rain Letter",
        "passed": True,
        "chapter_dir": str(tmp_path / "novel-demo" / "chapters" / "chapter-0001"),
    }
    assert [call[0] for call in pipeline.calls] == [
        "draft_chapter",
        "quality_check",
        "extract_graph_delta",
    ]
    saved = save_calls[0]
    assert saved["project_id"] == "novel-demo"
    assert saved["chapter_plan"].title == "Rain Letter"
    assert saved["chapter_draft"].content == "Draft for Rain Letter"
    assert saved["final_chapter"].content == "Draft for Rain Letter"
    assert saved["quality_report"].passed is True
    assert saved["root"] == tmp_path


def test_post_chapter_draft_uses_llm_profile_when_mode_is_llm(tmp_path, monkeypatch):
    project_dir = tmp_path / "novel-demo"
    project_dir.mkdir()
    (project_dir / "outline.json").write_text(
        """[
          {
            "chapter_number": 1,
            "title": "Rain Letter",
            "goal": "Find the first clue",
            "key_events": ["Lights fail"],
            "pov_character": "Lin"
          }
        ]""",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        api_module,
        "save_chapter_artifacts",
        lambda **kwargs: tmp_path / "novel-demo" / "chapters" / "chapter-0001",
    )
    store = FakeProfileStore(
        {
            "default": LLMProfile(
                id="default",
                name="Default",
                provider="deepseek",
                model="deepseek-chat",
                api_key="secret",
            )
        }
    )
    factory_calls = []
    pipeline_clients = []

    def fake_llm_client_factory(profile):
        factory_calls.append(profile)
        return "fake-client"

    class FakeLLMWritingPipeline(FakeWritingPipeline):
        def __init__(self, llm_client):
            super().__init__()
            pipeline_clients.append(llm_client)

    monkeypatch.setattr(api_module, "LLMBackedWritingPipeline", FakeLLMWritingPipeline)
    client = TestClient(
        create_app(
            planner=SpyPlanner(),
            storage_root=tmp_path,
            profile_store=store,
            llm_client_factory=fake_llm_client_factory,
        )
    )

    response = client.post(
        "/projects/novel-demo/chapters/1/draft",
        json={"mode": "llm", "llm_profile": "default"},
    )

    assert response.status_code == 200
    assert pipeline_clients == ["fake-client"]
    assert factory_calls == [store.profiles["default"]]


def test_post_chapter_draft_batch_generates_requested_range(tmp_path, monkeypatch):
    project_dir = tmp_path / "novel-demo"
    project_dir.mkdir()
    (project_dir / "outline.json").write_text(
        """[
          {
            "chapter_number": 1,
            "title": "Rain Letter",
            "goal": "Find the first clue",
            "key_events": ["Lights fail"],
            "pov_character": "Lin"
          },
          {
            "chapter_number": 2,
            "title": "Broken Clock",
            "goal": "Decode the second clue",
            "key_events": ["The clock stops"],
            "pov_character": "Lin"
          },
          {
            "chapter_number": 3,
            "title": "Quiet Bridge",
            "goal": "Meet the witness",
            "key_events": ["A witness disappears"],
            "pov_character": "Lin"
          }
        ]""",
        encoding="utf-8",
    )
    save_calls = []

    def fake_save_chapter_artifacts(**kwargs):
        save_calls.append(kwargs)
        chapter_number = kwargs["chapter_plan"].chapter_number
        return tmp_path / "novel-demo" / "chapters" / f"chapter-{chapter_number:04d}"

    monkeypatch.setattr(api_module, "save_chapter_artifacts", fake_save_chapter_artifacts)
    pipeline = FakeWritingPipeline()
    client = TestClient(
        create_app(
            planner=SpyPlanner(),
            storage_root=tmp_path,
            writing_pipeline=pipeline,
        )
    )

    response = client.post(
        "/projects/novel-demo/chapters/draft-batch",
        json={"start_chapter": 1, "end_chapter": 2},
    )

    assert response.status_code == 200
    assert response.json() == {
        "project_id": "novel-demo",
        "start_chapter": 1,
        "end_chapter": 2,
        "results": [
            {
                "chapter_number": 1,
                "title": "Rain Letter",
                "passed": True,
                "chapter_dir": str(tmp_path / "novel-demo" / "chapters" / "chapter-0001"),
            },
            {
                "chapter_number": 2,
                "title": "Broken Clock",
                "passed": True,
                "chapter_dir": str(tmp_path / "novel-demo" / "chapters" / "chapter-0002"),
            },
        ],
    }
    assert [call["chapter_plan"].chapter_number for call in save_calls] == [1, 2]
    assert [call[0] for call in pipeline.calls] == [
        "draft_chapter",
        "quality_check",
        "extract_graph_delta",
        "draft_chapter",
        "quality_check",
        "extract_graph_delta",
    ]


def test_post_chapter_draft_batch_rejects_invalid_range(tmp_path):
    project_dir = tmp_path / "novel-demo"
    project_dir.mkdir()
    (project_dir / "outline.json").write_text("[]", encoding="utf-8")
    client = TestClient(create_app(planner=SpyPlanner(), storage_root=tmp_path))

    response = client.post(
        "/projects/novel-demo/chapters/draft-batch",
        json={"start_chapter": 3, "end_chapter": 1},
    )

    assert response.status_code == 422


def test_post_chapter_draft_returns_404_when_llm_profile_is_missing(tmp_path):
    project_dir = tmp_path / "novel-demo"
    project_dir.mkdir()
    (project_dir / "outline.json").write_text(
        """[
          {
            "chapter_number": 1,
            "title": "Rain Letter",
            "goal": "Find the first clue",
            "key_events": ["Lights fail"],
            "pov_character": "Lin"
          }
        ]""",
        encoding="utf-8",
    )
    client = TestClient(
        create_app(
            planner=SpyPlanner(),
            storage_root=tmp_path,
            profile_store=FakeProfileStore(),
            llm_client_factory=lambda profile: "fake-client",
        )
    )

    response = client.post(
        "/projects/novel-demo/chapters/1/draft",
        json={"mode": "llm", "llm_profile": "missing"},
    )

    assert response.status_code == 404


class FakeWritingPipeline:
    def __init__(self):
        self.calls = []

    def draft_chapter(self, plan, graph_context=None):
        self.calls.append(("draft_chapter", plan.chapter_number, graph_context))
        return ChapterDraft(
            chapter_number=plan.chapter_number,
            title=plan.title,
            content=f"Draft for {plan.title}",
            summary="summary",
            word_count=21,
        )

    def quality_check(self, draft, plan, graph_context=None):
        self.calls.append(("quality_check", draft.chapter_number, plan.chapter_number))
        return QualityReport(score=95, issues=[])

    def revise_chapter(self, draft, report, plan=None):
        self.calls.append(("revise_chapter", draft.chapter_number))
        return draft

    def extract_graph_delta(self, project_id, final_chapter):
        self.calls.append(("extract_graph_delta", project_id, final_chapter.chapter_number))
        return GraphDelta(project_id=project_id, source_chapter_number=final_chapter.chapter_number)
