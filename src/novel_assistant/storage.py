from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import ChapterDraft, RevisedChapterDraft


def save_workflow_result(result: dict[str, Any], root: str | Path = "projects") -> Path:
    """Persist the MVP workflow result as Markdown plus JSON artifacts."""
    project_id = result["project_id"]
    project_dir = Path(root) / project_id
    chapter = result["final_chapter"]
    draft = result["chapter_draft"]
    chapter_number = _chapter_number(chapter)
    chapter_dir = project_dir / "chapters" / f"chapter-{chapter_number:04d}"
    chapter_dir.mkdir(parents=True, exist_ok=True)

    _write_json(
        project_dir / "project.json",
        {
            "project_id": project_id,
            "title": result["blueprint"].title,
            "latest_chapter": chapter_number,
        },
    )
    _write_json(project_dir / "blueprint.json", result["blueprint"])
    _write_json(chapter_dir / "plan.json", result["chapter_plan"])
    _write_text(chapter_dir / "draft.md", _content(draft))
    _write_json(chapter_dir / "quality-report.json", result["quality_report"])
    _write_text(chapter_dir / "final.md", _content(chapter))
    _write_json(chapter_dir / "graph-delta.json", result["graph_delta"])
    _write_json(
        chapter_dir / "metadata.json",
        {
            "project_id": project_id,
            "chapter_number": chapter_number,
            "title": _title(chapter),
            "files": [
                "plan.json",
                "draft.md",
                "quality-report.json",
                "final.md",
                "graph-delta.json",
            ],
        },
    )
    return project_dir


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_to_jsonable(value), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def _to_jsonable(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    return value


def _chapter_number(chapter: ChapterDraft | RevisedChapterDraft) -> int:
    if isinstance(chapter, RevisedChapterDraft):
        return chapter.original.chapter_number
    return chapter.chapter_number


def _title(chapter: ChapterDraft | RevisedChapterDraft) -> str:
    if isinstance(chapter, RevisedChapterDraft):
        return chapter.original.title
    return chapter.title


def _content(chapter: ChapterDraft | RevisedChapterDraft) -> str:
    if isinstance(chapter, RevisedChapterDraft):
        return chapter.revised_content
    return chapter.content
