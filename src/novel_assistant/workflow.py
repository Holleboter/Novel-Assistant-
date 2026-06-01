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
    requirement: UserRequirement
    blueprint: StoryBlueprint
    characters: list[CharacterProfile]
    initial_graph_written: bool
    chapter_plan: ChapterPlan
    graph_context: dict[str, Any]
    chapter_draft: ChapterDraft
    quality_report: QualityReport
    final_chapter: ChapterDraft | RevisedChapterDraft
    graph_delta: GraphDelta
    graph_delta_written: bool


def initial_state(
    user_input: str,
    project_id: str = "novel-demo",
) -> NovelAgentState:
    return {"project_id": project_id, "user_input": user_input}


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

    def plan_chapter(state: NovelAgentState) -> NovelAgentState:
        chapter_plan = planner.plan_chapter(
            state["requirement"],
            state["blueprint"],
            state["characters"],
        )
        return {
            **state,
            "chapter_plan": chapter_plan,
            "graph_context": {
                "protagonists": [character.name for character in state["characters"][:1]],
                "active_hooks": chapter_plan.key_events,
            },
        }

    def write_chapter(state: NovelAgentState) -> NovelAgentState:
        draft = writer.draft_chapter(state["chapter_plan"], state["graph_context"])
        return {**state, "chapter_draft": draft}

    def quality_check(state: NovelAgentState) -> NovelAgentState:
        report = writer.quality_check(
            state["chapter_draft"],
            state["chapter_plan"],
            state["graph_context"],
        )
        return {**state, "quality_report": report}

    def revise_or_accept(state: NovelAgentState) -> NovelAgentState:
        if state["quality_report"].revision_required:
            final_chapter = writer.revise_chapter(
                state["chapter_draft"],
                state["quality_report"],
                state["chapter_plan"],
            )
        else:
            final_chapter = state["chapter_draft"]
        return {**state, "final_chapter": final_chapter}

    def extract_and_write_delta(state: NovelAgentState) -> NovelAgentState:
        delta = writer.extract_graph_delta(state["project_id"], state["final_chapter"])
        graph_repository.apply_delta(delta)
        return {**state, "graph_delta": delta, "graph_delta_written": True}

    graph = StateGraph(NovelAgentState)
    graph.add_node("analyze_requirement", analyze_requirement)
    graph.add_node("blueprint", build_blueprint)
    graph.add_node("characters", build_characters)
    graph.add_node("write_initial_graph", write_initial_graph)
    graph.add_node("chapter_plan", plan_chapter)
    graph.add_node("write_chapter", write_chapter)
    graph.add_node("quality_check", quality_check)
    graph.add_node("revise_or_accept", revise_or_accept)
    graph.add_node("write_graph_delta", extract_and_write_delta)

    graph.set_entry_point("analyze_requirement")
    graph.add_edge("analyze_requirement", "blueprint")
    graph.add_edge("blueprint", "characters")
    graph.add_edge("characters", "write_initial_graph")
    graph.add_edge("write_initial_graph", "chapter_plan")
    graph.add_edge("chapter_plan", "write_chapter")
    graph.add_edge("write_chapter", "quality_check")
    graph.add_edge("quality_check", "revise_or_accept")
    graph.add_edge("revise_or_accept", "write_graph_delta")
    graph.add_edge("write_graph_delta", END)
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
