from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from .models import ChapterPlan
from .planning_pipeline import DeterministicStoryPlanner
from .storage import (
    list_chapters,
    load_outline,
    save_chapter_artifacts,
    save_outline,
)
from .writing_pipeline import DeterministicWritingPipeline


class OutlineRequest(BaseModel):
    project_id: str
    user_input: str
    chapter_count: int = Field(default=12, ge=1, le=200)
    save: bool = False


def create_app(
    planner: Any | None = None,
    writing_pipeline: Any | None = None,
    storage_root: str | Path = "projects",
) -> FastAPI:
    app = FastAPI()
    story_planner = planner or DeterministicStoryPlanner()
    writer = writing_pipeline or DeterministicWritingPipeline()

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

    @app.get("/projects/{project_id}")
    def project(project_id: str) -> dict[str, Any]:
        project_dir = Path(storage_root) / project_id
        if not project_dir.exists():
            raise HTTPException(status_code=404, detail="Project not found")

        outline_path = project_dir / "outline.json"
        return {
            "project_id": project_id,
            "has_outline": outline_path.exists(),
            "outline_path": str(outline_path) if outline_path.exists() else None,
            "chapters": list_chapters(project_id, root=storage_root),
        }

    @app.get("/projects/{project_id}/chapters")
    def chapters(project_id: str) -> list[Any]:
        project_dir = Path(storage_root) / project_id
        if not project_dir.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        return list_chapters(project_id, root=storage_root)

    @app.post("/projects/{project_id}/chapters/{chapter_number}/draft")
    def draft_chapter(project_id: str, chapter_number: int) -> dict[str, Any]:
        project_dir = Path(storage_root) / project_id
        outline_path = project_dir / "outline.json"
        if not project_dir.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        if not outline_path.exists():
            raise HTTPException(status_code=404, detail="Outline not found")

        plan = _find_chapter_plan(load_outline(project_id, root=storage_root), chapter_number)
        if plan is None:
            raise HTTPException(status_code=404, detail="Chapter plan not found")

        graph_context = {
            "active_hooks": plan.key_events,
            "protagonists": [plan.pov_character] if plan.pov_character else [],
        }
        chapter_draft = writer.draft_chapter(plan, graph_context)
        quality_report = writer.quality_check(chapter_draft, plan, graph_context)
        final_chapter = (
            writer.revise_chapter(chapter_draft, quality_report, plan)
            if quality_report.revision_required
            else chapter_draft
        )
        graph_delta = writer.extract_graph_delta(project_id, final_chapter)
        chapter_dir = save_chapter_artifacts(
            project_id=project_id,
            chapter_plan=plan,
            chapter_draft=chapter_draft,
            quality_report=quality_report,
            final_chapter=final_chapter,
            graph_delta=graph_delta,
            root=storage_root,
        )
        return {
            "chapter_number": plan.chapter_number,
            "title": plan.title,
            "passed": quality_report.passed,
            "chapter_dir": str(chapter_dir),
        }

    return app


def _find_chapter_plan(outline: list[Any], chapter_number: int) -> ChapterPlan | None:
    for chapter in outline:
        plan = chapter if isinstance(chapter, ChapterPlan) else ChapterPlan.model_validate(chapter)
        if plan.chapter_number == chapter_number:
            return plan
    return None


app = create_app()
