from __future__ import annotations

from types import SimpleNamespace
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from .models import (
    ChapterDraft,
    ChapterPlan,
    CharacterProfile,
    GraphDelta,
    QualityReport,
    RevisedChapterDraft,
    StoryBlueprint,
    UserRequirement,
)
from .planning_pipeline import DeterministicStoryPlanner
from .writing_pipeline import DeterministicWritingPipeline


class NovelAgentState(TypedDict, total=False):
    project_id: str
    user_input: str
    chapter_count: int
    start_chapter: int
    end_chapter: int
    requirement: UserRequirement
    blueprint: StoryBlueprint
    characters: list[CharacterProfile]
    initial_graph_written: bool
    outline: list[ChapterPlan]
    chapter_plan: ChapterPlan
    graph_context: dict[str, Any]
    chapter_draft: ChapterDraft
    quality_report: QualityReport
    final_chapter: ChapterDraft | RevisedChapterDraft
    graph_delta: GraphDelta
    chapter_results: list[dict[str, Any]]
    graph_delta_written: bool


def initial_state(
    user_input: str,
    project_id: str = "novel-demo",
    chapter_count: int = 1,
    start_chapter: int = 1,
    end_chapter: int | None = None,
) -> NovelAgentState:
    return {
        "project_id": project_id,
        "user_input": user_input,
        "chapter_count": chapter_count,
        "start_chapter": start_chapter,
        "end_chapter": end_chapter or start_chapter,
    }


def build_workflow(
    graph_repository: Any,
    writing_pipeline: DeterministicWritingPipeline | None = None,
    story_planner: DeterministicStoryPlanner | None = None,
):
    writer = writing_pipeline or DeterministicWritingPipeline()
    planner = story_planner or DeterministicStoryPlanner()

    def analyze_requirement(state: NovelAgentState) -> NovelAgentState:
        return {
            **state,
            "requirement": planner.analyze_requirement(state["user_input"]),
        }

    def build_blueprint(state: NovelAgentState) -> NovelAgentState:
        return {
            **state,
            "blueprint": planner.build_blueprint(state["requirement"]),
        }

    def build_characters(state: NovelAgentState) -> NovelAgentState:
        return {
            **state,
            "characters": planner.build_characters(
                state["requirement"],
                state["blueprint"],
            ),
        }

    def write_initial_graph(state: NovelAgentState) -> NovelAgentState:
        if hasattr(graph_repository, "ensure_constraints"):
            graph_repository.ensure_constraints()
        graph_repository.upsert_initial_graph(
            state["project_id"],
            _repository_blueprint(state["blueprint"], state["requirement"]),
            [
                _repository_character(state["project_id"], index, character)
                for index, character in enumerate(state["characters"], start=1)
            ],
        )
        return {**state, "initial_graph_written": True}

    def plan_chapters(state: NovelAgentState) -> NovelAgentState:
        outline = planner.plan_chapters(
            state["requirement"],
            state["blueprint"],
            state["characters"],
            chapter_count=state.get("chapter_count", 1),
        )
        return {**state, "outline": outline}

    def generate_chapters(state: NovelAgentState) -> NovelAgentState:
        chapter_results: list[dict[str, Any]] = []
        start_chapter = state.get("start_chapter", 1)
        end_chapter = state.get("end_chapter", start_chapter)
        selected_plans = [
            plan
            for plan in state["outline"]
            if start_chapter <= plan.chapter_number <= end_chapter
        ]
        expected_chapter_numbers = set(range(start_chapter, end_chapter + 1))
        selected_chapter_numbers = {plan.chapter_number for plan in selected_plans}
        missing_chapter_numbers = sorted(
            expected_chapter_numbers - selected_chapter_numbers
        )
        if missing_chapter_numbers:
            raise ValueError(f"Missing chapter plans: {missing_chapter_numbers}")

        for chapter_plan in selected_plans:
            graph_context = {
                "protagonists": [chapter_plan.pov_character]
                if chapter_plan.pov_character
                else [],
                "active_hooks": chapter_plan.key_events,
            }
            chapter_draft = writer.draft_chapter(chapter_plan, graph_context)
            quality_report = writer.quality_check(
                chapter_draft,
                chapter_plan,
                graph_context,
            )
            final_chapter = (
                writer.revise_chapter(chapter_draft, quality_report, chapter_plan)
                if quality_report.revision_required
                else chapter_draft
            )
            graph_delta = writer.extract_graph_delta(state["project_id"], final_chapter)
            graph_repository.apply_delta(graph_delta)
            chapter_results.append(
                {
                    "chapter_plan": chapter_plan,
                    "graph_context": graph_context,
                    "chapter_draft": chapter_draft,
                    "quality_report": quality_report,
                    "final_chapter": final_chapter,
                    "graph_delta": graph_delta,
                }
            )

        first_result = chapter_results[0]
        return {
            **state,
            "chapter_results": chapter_results,
            "chapter_plan": first_result["chapter_plan"],
            "graph_context": first_result["graph_context"],
            "chapter_draft": first_result["chapter_draft"],
            "quality_report": first_result["quality_report"],
            "final_chapter": first_result["final_chapter"],
            "graph_delta": first_result["graph_delta"],
            "graph_delta_written": True,
        }

    graph = StateGraph(NovelAgentState)
    graph.add_node("analyze_requirement", analyze_requirement)
    graph.add_node("blueprint", build_blueprint)
    graph.add_node("characters", build_characters)
    graph.add_node("write_initial_graph", write_initial_graph)
    graph.add_node("outline", plan_chapters)
    graph.add_node("generate_chapters", generate_chapters)

    graph.set_entry_point("analyze_requirement")
    graph.add_edge("analyze_requirement", "blueprint")
    graph.add_edge("blueprint", "characters")
    graph.add_edge("characters", "write_initial_graph")
    graph.add_edge("write_initial_graph", "outline")
    graph.add_edge("outline", "generate_chapters")
    graph.add_edge("generate_chapters", END)
    return graph.compile()


def _repository_blueprint(
    blueprint: StoryBlueprint,
    requirement: UserRequirement,
) -> SimpleNamespace:
    return SimpleNamespace(
        title=blueprint.title,
        genre=requirement.genre,
        premise=requirement.premise,
        main_conflict=blueprint.central_conflict,
        worldview=blueprint.setting,
        protagonist_arc="沈砚从逃避过去到主动承担选择。",
        ending_direction="沈砚公开旧案真相，修正未来灾难。",
    )


def _repository_character(
    project_id: str,
    index: int,
    character: CharacterProfile,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=f"{project_id}:char-{index}",
        name=character.name,
        role=character.role,
        identity=character.role,
        goal=character.motivation,
        motivation=character.motivation,
        weakness="尚未完全信任他人",
        growth_arc=character.arc,
        current_state="第一章登场",
    )
