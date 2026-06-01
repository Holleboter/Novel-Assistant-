from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from .planning_pipeline import DeterministicStoryPlanner
from .storage import save_outline


class OutlineRequest(BaseModel):
    project_id: str
    user_input: str
    chapter_count: int = Field(default=12, ge=1, le=200)
    save: bool = False


def create_app(
    planner: Any | None = None,
    storage_root: str | Path = "projects",
) -> FastAPI:
    app = FastAPI()
    story_planner = planner or DeterministicStoryPlanner()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/outline")
    def outline(request: OutlineRequest) -> dict[str, Any]:
        requirement = story_planner.analyze_requirement(request.user_input)
        blueprint = story_planner.build_blueprint(requirement)
        characters = story_planner.build_characters(requirement, blueprint)
        chapters = story_planner.plan_chapters(
            requirement,
            blueprint,
            characters,
            chapter_count=request.chapter_count,
        )
        outline_path = None
        if request.save:
            outline_path = str(
                save_outline(request.project_id, chapters, root=storage_root)
            )
        return {
            "project_id": request.project_id,
            "blueprint": jsonable_encoder(blueprint),
            "characters": jsonable_encoder(characters),
            "outline": jsonable_encoder(chapters),
            "outline_path": outline_path,
        }

    return app


app = create_app()
