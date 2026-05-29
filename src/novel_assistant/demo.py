from __future__ import annotations

from .graph_repository import GraphRepository
from .llm_client import LLMClient
from .planning_pipeline import LLMBackedStoryPlanner
from .storage import save_workflow_result
from .writing_pipeline import LLMBackedWritingPipeline
from .workflow import build_workflow, initial_state


def run_demo(
    user_input: str,
    save: bool = True,
    use_llm: bool = False,
    llm_client: LLMClient | None = None,
) -> dict:
    repository = GraphRepository()
    try:
        writing_pipeline = (
            LLMBackedWritingPipeline(llm_client=llm_client)
            if use_llm
            else None
        )
        app = build_workflow(
            graph_repository=repository,
            writing_pipeline=writing_pipeline,
            story_planner=LLMBackedStoryPlanner(llm_client=llm_client)
            if use_llm
            else None,
        )
        result = app.invoke(initial_state(user_input))
        if save:
            result["project_dir"] = str(save_workflow_result(result))
        return result
    finally:
        if hasattr(repository, "close"):
            repository.close()


if __name__ == "__main__":
    demo_result = run_demo("写一本悬疑奇幻小说，主角在雨夜茶馆收到未来来信。")
    chapter = demo_result["final_chapter"]
    content = getattr(chapter, "content", None) or getattr(chapter, "revised_content")
    print(chapter.title if hasattr(chapter, "title") else chapter.original.title)
    print(content[:120])
    print(demo_result["project_dir"])
