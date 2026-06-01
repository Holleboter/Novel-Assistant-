from __future__ import annotations

import re
from uuid import uuid4
from pathlib import Path
from typing import Any, Literal

from fastapi import Body, FastAPI, HTTPException, Response
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

from .config import LLMSettings
from .graph_repository import GraphRepository
from .llm_client import LLMClient
from .llm_profiles import LLMProfile, LLMProfileStore, PublicLLMProfile
from .models import ChapterPlan
from .models import ChapterDraft
from .planning_pipeline import DeterministicStoryPlanner, LLMBackedStoryPlanner
from .skills import SkillStore
from .storage import (
    confirm_chapter_content,
    create_project,
    list_projects,
    list_chapters,
    load_outline,
    read_chapter_content,
    read_chapter_quality_report,
    save_chapter_artifacts,
    save_chapter_quality_report,
    save_outline,
    save_workflow_result,
)
from .writing_pipeline import DeterministicWritingPipeline, LLMBackedWritingPipeline
from .workflow import build_workflow, initial_state
from .workflow_runs import WorkflowRunStore


_PROJECT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


class OutlineRequest(BaseModel):
    project_id: str
    user_input: str
    chapter_count: int = Field(default=12, ge=1, le=200)
    save: bool = False
    mode: Literal["deterministic", "llm"] = "deterministic"
    llm_profile: str | None = None


class DraftRequest(BaseModel):
    mode: Literal["deterministic", "llm"] = "deterministic"
    llm_profile: str | None = None


class ProjectRequest(BaseModel):
    project_id: str = Field(pattern=_PROJECT_ID_PATTERN.pattern)
    title: str | None = None


class BatchDraftRequest(DraftRequest):
    start_chapter: int = Field(ge=1)
    end_chapter: int = Field(ge=1)

    @model_validator(mode="after")
    def end_chapter_must_not_precede_start(self) -> "BatchDraftRequest":
        if self.end_chapter < self.start_chapter:
            raise ValueError("end_chapter must be greater than or equal to start_chapter")
        return self


class NovelGenerationWorkflowRequest(BaseModel):
    project_id: str = Field(pattern=_PROJECT_ID_PATTERN.pattern)
    user_input: str
    chapter_count: int = Field(default=1, ge=1, le=200)
    start_chapter: int = Field(default=1, ge=1)
    end_chapter: int | None = Field(default=None, ge=1)
    save: bool = True
    mode: Literal["deterministic", "llm"] = "deterministic"
    llm_profile: str | None = None

    @model_validator(mode="after")
    def chapter_range_must_fit_outline(self) -> "NovelGenerationWorkflowRequest":
        if self.end_chapter is None:
            self.end_chapter = self.start_chapter
        if self.end_chapter < self.start_chapter:
            raise ValueError("end_chapter must be greater than or equal to start_chapter")
        if self.end_chapter > self.chapter_count:
            raise ValueError("end_chapter must be less than or equal to chapter_count")
        return self


class LLMProfileRequest(BaseModel):
    profile_id: str | None = None
    name: str | None = None
    provider: str
    model: str
    api_key: str | None = None
    base_url: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, gt=0)
    timeout_seconds: int | None = Field(default=None, gt=0)


class SkillApplyRequest(BaseModel):
    skill_id: str
    content: str
    llm_profile: str | None = None


class ConfirmChapterRequest(BaseModel):
    content: str
    filename: str = "final.md"


class QualityReportRequest(BaseModel):
    content: str


def create_app(
    planner: Any | None = None,
    writing_pipeline: Any | None = None,
    storage_root: str | Path = "projects",
    profile_store: Any | None = None,
    llm_client_factory: Any | None = None,
    graph_repository: Any | None = None,
    workflow_run_store: WorkflowRunStore | None = None,
    skill_store: SkillStore | None = None,
) -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
        allow_methods=["*"],
        allow_headers=["*"],
    )
    story_planner = planner or DeterministicStoryPlanner()
    writer = writing_pipeline or DeterministicWritingPipeline()
    profiles = profile_store or LLMProfileStore()
    make_llm_client = llm_client_factory or _default_llm_client_factory
    workflow_runs = workflow_run_store or WorkflowRunStore()
    skills = skill_store or SkillStore()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/llm/profiles")
    def list_llm_profiles() -> list[dict[str, Any]]:
        return [_public_profile(profile).model_dump() for profile in profiles.list()]

    @app.post("/llm/profiles")
    def create_llm_profile(request: LLMProfileRequest) -> dict[str, Any]:
        if request.profile_id is None:
            raise HTTPException(status_code=422, detail="profile_id is required")
        profile = _make_profile(request.profile_id, request)
        return _public_profile(profiles.upsert(profile)).model_dump()

    @app.put("/llm/profiles/{profile_id}")
    def update_llm_profile(profile_id: str, request: LLMProfileRequest) -> dict[str, Any]:
        existing_profile = profiles.get(profile_id)
        if existing_profile is None:
            raise HTTPException(status_code=404, detail="LLM profile not found")
        profile = _make_profile(profile_id, request, existing=existing_profile)
        return _public_profile(profiles.upsert(profile)).model_dump()

    @app.delete("/llm/profiles/{profile_id}", status_code=204)
    def delete_llm_profile(profile_id: str) -> Response:
        deleted = profiles.delete(profile_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="LLM profile not found")
        return Response(status_code=204)

    @app.get("/skills")
    def list_skills() -> list[dict[str, Any]]:
        return [skill.model_dump() for skill in skills.list()]

    @app.post("/skills/apply")
    def apply_skill(request: SkillApplyRequest) -> dict[str, str]:
        skill = skills.get(request.skill_id)
        if skill is None:
            raise HTTPException(status_code=404, detail="Skill not found")
        profile = _require_profile(profiles, request.llm_profile)
        response = make_llm_client(profile).complete(
            system_prompt=skill.content,
            user_prompt=request.content,
        )
        return {
            "skill_id": skill.id,
            "content": response.content,
        }

    @app.post("/outline")
    def outline(request: OutlineRequest) -> dict[str, Any]:
        _validate_project_id(request.project_id)
        active_planner = story_planner
        if request.mode == "llm":
            profile = _require_profile(profiles, request.llm_profile)
            active_planner = LLMBackedStoryPlanner(llm_client=make_llm_client(profile))

        requirement = active_planner.analyze_requirement(request.user_input)
        blueprint = active_planner.build_blueprint(requirement)
        characters = active_planner.build_characters(requirement, blueprint)
        chapters = active_planner.plan_chapters(
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

    @app.post("/workflows/novel-generation")
    def novel_generation_workflow(
        request: NovelGenerationWorkflowRequest,
    ) -> dict[str, Any]:
        _validate_project_id(request.project_id)
        workflow_id = _new_workflow_id(request.project_id)
        request_payload = request.model_dump(mode="json")
        workflow_runs.create(
            workflow_id=workflow_id,
            project_id=request.project_id,
            request=request_payload,
        )
        try:
            active_planner = story_planner
            active_writer = writer
            if request.mode == "llm":
                profile = _require_profile(profiles, request.llm_profile)
                llm_client = make_llm_client(profile)
                active_planner = LLMBackedStoryPlanner(llm_client=llm_client)
                active_writer = LLMBackedWritingPipeline(llm_client=llm_client)

            repository = graph_repository or GraphRepository()
            should_close_repository = graph_repository is None
            workflow = build_workflow(
                graph_repository=repository,
                writing_pipeline=active_writer,
                story_planner=active_planner,
            )
            result = workflow.invoke(
                initial_state(
                    request.user_input,
                    project_id=request.project_id,
                    chapter_count=request.chapter_count,
                    start_chapter=request.start_chapter,
                    end_chapter=request.end_chapter,
                )
            )
            project_dir = (
                save_workflow_result(result, root=storage_root)
                if request.save
                else None
            )
            response = _workflow_response(result, project_dir, workflow_id)
            workflow_runs.complete(
                workflow_id,
                result=response,
                progress=_workflow_progress(response),
            )
            return response
        except HTTPException as exc:
            workflow_runs.fail(workflow_id, error=str(exc.detail))
            raise
        except Exception as exc:
            workflow_runs.fail(workflow_id, error=str(exc))
            raise
        finally:
            if (
                "repository" in locals()
                and should_close_repository
                and hasattr(repository, "close")
            ):
                repository.close()

    @app.get("/workflows/{workflow_id}")
    def workflow_run(workflow_id: str) -> dict[str, Any]:
        run = workflow_runs.get(workflow_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Workflow run not found")
        return run.model_dump(mode="json")

    @app.get("/projects")
    def projects() -> list[dict[str, Any]]:
        return list_projects(root=storage_root)

    @app.post("/projects", status_code=201)
    def create_project_endpoint(request: ProjectRequest) -> dict[str, Any]:
        try:
            project_metadata = create_project(
                request.project_id,
                title=request.title,
                root=storage_root,
            )
        except FileExistsError as exc:
            raise HTTPException(status_code=409, detail="Project already exists") from exc

        project_dir = Path(storage_root) / request.project_id
        return {
            "project_id": project_metadata["project_id"],
            "title": project_metadata["title"],
            "project_path": str(project_dir),
            "has_outline": False,
            "chapter_count": 0,
        }

    @app.get("/projects/{project_id}")
    def project(project_id: str) -> dict[str, Any]:
        _validate_project_id(project_id)
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

    @app.get("/projects/{project_id}/outline")
    def project_outline(project_id: str) -> list[Any]:
        _validate_project_id(project_id)
        project_dir = Path(storage_root) / project_id
        if not project_dir.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        try:
            return load_outline(project_id, root=storage_root)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Outline not found") from exc

    @app.get("/projects/{project_id}/chapters")
    def chapters(project_id: str) -> list[Any]:
        _validate_project_id(project_id)
        project_dir = Path(storage_root) / project_id
        if not project_dir.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        return list_chapters(project_id, root=storage_root)

    @app.get("/projects/{project_id}/chapters/{chapter_number}/content")
    def chapter_content(project_id: str, chapter_number: int) -> dict[str, Any]:
        _validate_project_id(project_id)
        try:
            return read_chapter_content(project_id, chapter_number, root=storage_root)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Chapter content not found") from exc

    @app.get("/projects/{project_id}/chapters/{chapter_number}/quality-report")
    def chapter_quality_report(project_id: str, chapter_number: int) -> dict[str, Any]:
        _validate_project_id(project_id)
        try:
            return read_chapter_quality_report(
                project_id,
                chapter_number,
                root=storage_root,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Quality report not found") from exc

    @app.post("/projects/{project_id}/chapters/{chapter_number}/quality-report")
    def check_chapter_quality(
        project_id: str,
        chapter_number: int,
        request: QualityReportRequest,
    ) -> dict[str, Any]:
        _validate_project_id(project_id)
        project_dir = Path(storage_root) / project_id
        outline_path = project_dir / "outline.json"
        if not project_dir.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        if not outline_path.exists():
            raise HTTPException(status_code=404, detail="Outline not found")

        plan = _find_chapter_plan(load_outline(project_id, root=storage_root), chapter_number)
        if plan is None:
            raise HTTPException(status_code=404, detail="Chapter plan not found")

        draft = ChapterDraft(
            chapter_number=chapter_number,
            title=plan.title,
            content=request.content,
            word_count=len(request.content),
        )
        graph_context = {
            "active_hooks": plan.key_events,
            "protagonists": [plan.pov_character] if plan.pov_character else [],
        }
        quality_report = writer.quality_check(draft, plan, graph_context)
        save_chapter_quality_report(
            project_id,
            chapter_number,
            quality_report,
            root=storage_root,
        )
        return jsonable_encoder(quality_report)

    @app.post("/projects/{project_id}/chapters/{chapter_number}/confirm")
    def confirm_chapter(
        project_id: str,
        chapter_number: int,
        request: ConfirmChapterRequest,
    ) -> dict[str, Any]:
        _validate_project_id(project_id)
        try:
            return confirm_chapter_content(
                project_id,
                chapter_number,
                content=request.content,
                filename=request.filename,
                root=storage_root,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/projects/{project_id}/chapters/draft-batch")
    def draft_chapter_batch(
        project_id: str,
        request: BatchDraftRequest,
    ) -> dict[str, Any]:
        _validate_project_id(project_id)
        project_dir = Path(storage_root) / project_id
        outline_path = project_dir / "outline.json"
        if not project_dir.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        if not outline_path.exists():
            raise HTTPException(status_code=404, detail="Outline not found")

        outline = load_outline(project_id, root=storage_root)
        active_writer = _writer_for_request(request)
        results = []
        for chapter_number in range(request.start_chapter, request.end_chapter + 1):
            plan = _find_chapter_plan(outline, chapter_number)
            if plan is None:
                raise HTTPException(status_code=404, detail="Chapter plan not found")
            results.append(_draft_chapter_from_plan(project_id, plan, active_writer))

        return {
            "project_id": project_id,
            "start_chapter": request.start_chapter,
            "end_chapter": request.end_chapter,
            "results": results,
        }

    @app.post("/projects/{project_id}/chapters/{chapter_number}/draft")
    def draft_chapter(
        project_id: str,
        chapter_number: int,
        request: DraftRequest | None = Body(default=None),
    ) -> dict[str, Any]:
        _validate_project_id(project_id)
        project_dir = Path(storage_root) / project_id
        outline_path = project_dir / "outline.json"
        if not project_dir.exists():
            raise HTTPException(status_code=404, detail="Project not found")
        if not outline_path.exists():
            raise HTTPException(status_code=404, detail="Outline not found")

        plan = _find_chapter_plan(load_outline(project_id, root=storage_root), chapter_number)
        if plan is None:
            raise HTTPException(status_code=404, detail="Chapter plan not found")

        active_writer = _writer_for_request(request or DraftRequest())
        return _draft_chapter_from_plan(project_id, plan, active_writer)

    def _writer_for_request(draft_request: DraftRequest) -> Any:
        if draft_request.mode == "llm":
            profile = _require_profile(profiles, draft_request.llm_profile)
            return LLMBackedWritingPipeline(llm_client=make_llm_client(profile))
        return writer

    def _draft_chapter_from_plan(
        project_id: str,
        plan: ChapterPlan,
        active_writer: Any,
    ) -> dict[str, Any]:
        graph_context = {
            "active_hooks": plan.key_events,
            "protagonists": [plan.pov_character] if plan.pov_character else [],
        }
        chapter_draft = active_writer.draft_chapter(plan, graph_context)
        quality_report = active_writer.quality_check(chapter_draft, plan, graph_context)
        final_chapter = (
            active_writer.revise_chapter(chapter_draft, quality_report, plan)
            if quality_report.revision_required
            else chapter_draft
        )
        graph_delta = active_writer.extract_graph_delta(project_id, final_chapter)
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


def _validate_project_id(project_id: str) -> None:
    if _PROJECT_ID_PATTERN.fullmatch(project_id) is None:
        raise HTTPException(status_code=422, detail="Invalid project_id")


def _new_workflow_id(project_id: str) -> str:
    return f"{project_id}-{uuid4().hex[:12]}"


def _workflow_response(
    result: dict[str, Any],
    project_dir: Path | None,
    workflow_id: str,
) -> dict[str, Any]:
    chapter_plan = result["chapter_plan"]
    quality_report = result["quality_report"]
    chapter_number = chapter_plan.chapter_number
    outline = result.get("outline", [chapter_plan])
    chapter_results = result.get(
        "chapter_results",
        [
            {
                "chapter_plan": chapter_plan,
                "quality_report": quality_report,
            }
        ],
    )
    chapter_dir = (
        project_dir / "chapters" / f"chapter-{chapter_number:04d}"
        if project_dir is not None
        else None
    )
    chapters = []
    for chapter_result in chapter_results:
        result_plan = chapter_result["chapter_plan"]
        result_report = chapter_result["quality_report"]
        result_chapter_dir = (
            project_dir / "chapters" / f"chapter-{result_plan.chapter_number:04d}"
            if project_dir is not None
            else None
        )
        chapters.append(
            {
                "chapter_number": result_plan.chapter_number,
                "title": result_plan.title,
                "passed": result_report.passed,
                "chapter_dir": str(result_chapter_dir)
                if result_chapter_dir is not None
                else None,
            }
        )
    return {
        "workflow_id": workflow_id,
        "status": "completed",
        "project_id": result["project_id"],
        "project_path": str(project_dir) if project_dir is not None else None,
        "chapter_count": len(outline),
        "generated_chapter_count": len(chapters),
        "chapter_number": chapter_number,
        "title": chapter_plan.title,
        "passed": quality_report.passed,
        "chapters": chapters,
        "artifacts": {
            "project_dir": str(project_dir) if project_dir is not None else None,
            "outline_path": str(project_dir / "outline.json")
            if project_dir is not None
            else None,
            "chapter_dir": str(chapter_dir) if chapter_dir is not None else None,
        },
    }


def _workflow_progress(response: dict[str, Any]) -> dict[str, Any]:
    chapters = response["chapters"]
    current_chapter = chapters[-1]["chapter_number"] if chapters else None
    return {
        "total_chapters": response["chapter_count"],
        "completed_chapters": response["generated_chapter_count"],
        "current_chapter": current_chapter,
    }


def _find_chapter_plan(outline: list[Any], chapter_number: int) -> ChapterPlan | None:
    for chapter in outline:
        plan = chapter if isinstance(chapter, ChapterPlan) else ChapterPlan.model_validate(chapter)
        if plan.chapter_number == chapter_number:
            return plan
    return None


def _default_llm_client_factory(profile: LLMProfile) -> LLMClient:
    payload = profile.model_dump()
    settings_payload = {
        key: value
        for key, value in payload.items()
        if key
        in {
            "provider",
            "model",
            "api_key",
            "base_url",
            "temperature",
            "max_tokens",
            "timeout_seconds",
        }
        and value is not None
    }
    return LLMClient(settings=LLMSettings(_env_file=None, **settings_payload))


def _make_profile(
    profile_id: str,
    request: LLMProfileRequest,
    existing: LLMProfile | None = None,
) -> LLMProfile:
    fields_set = request.model_fields_set
    return LLMProfile(
        id=profile_id,
        name=request.name or (existing.name if existing else profile_id),
        provider=request.provider,
        model=request.model,
        api_key=(
            request.api_key
            if "api_key" in fields_set or existing is None
            else existing.api_key
        ),
        base_url=(
            request.base_url
            if "base_url" in fields_set or existing is None
            else existing.base_url
        ),
        temperature=(
            request.temperature
            if request.temperature is not None
            else (existing.temperature if existing else 0.7)
        ),
        max_tokens=(
            request.max_tokens
            if request.max_tokens is not None
            else (existing.max_tokens if existing else 4000)
        ),
        timeout_seconds=(
            request.timeout_seconds
            if request.timeout_seconds is not None
            else (existing.timeout_seconds if existing else 120)
        ),
    )


def _public_profile(profile: LLMProfile) -> PublicLLMProfile:
    return PublicLLMProfile(
        id=profile.id,
        name=profile.name,
        provider=profile.provider,
        model=profile.model,
        base_url=profile.base_url,
        api_key_set=profile.api_key is not None,
        temperature=profile.temperature,
        max_tokens=profile.max_tokens,
        timeout_seconds=profile.timeout_seconds,
    )


def _require_profile(profile_store: LLMProfileStore, profile_id: str | None) -> LLMProfile:
    selected_profile_id = profile_id or "default"
    profile = profile_store.get(selected_profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="LLM profile not found")
    return profile


app = create_app()
