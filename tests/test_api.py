from pathlib import Path

from fastapi.testclient import TestClient

from novel_assistant.api import create_app
from novel_assistant.models import ChapterPlan, CharacterProfile, StoryBlueprint, UserRequirement


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
