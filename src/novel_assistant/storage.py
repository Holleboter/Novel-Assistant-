from __future__ import annotations

import errno
import json
import re
from pathlib import Path
from typing import Any

from .models import ChapterDraft, RevisedChapterDraft


_CHAPTER_DIR_PATTERN = re.compile(r"^chapter-(\d{4})$")


def load_outline(
    project_id: str, root: str | Path = "projects"
) -> list[dict[str, Any]]:
    """Load a project outline from JSON."""
    outline_path = Path(root) / project_id / "outline.json"
    if not outline_path.exists():
        raise FileNotFoundError(
            errno.ENOENT, "No such file or directory", str(outline_path)
        )
    return json.loads(outline_path.read_text(encoding="utf-8"))


def list_chapters(
    project_id: str, root: str | Path = "projects"
) -> list[dict[str, Any]]:
    """Return chapter metadata sorted by chapter number."""
    chapters_dir = Path(root) / project_id / "chapters"
    if not chapters_dir.exists():
        return []

    chapters: list[dict[str, Any]] = []
    for chapter_dir in chapters_dir.iterdir():
        if not chapter_dir.is_dir():
            continue
        match = _CHAPTER_DIR_PATTERN.match(chapter_dir.name)
        if match is None:
            continue

        chapter_number = int(match.group(1))
        metadata_path = chapter_dir / "metadata.json"
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            metadata.setdefault("chapter_number", chapter_number)
            chapters.append(metadata)
        else:
            chapters.append(
                {
                    "project_id": project_id,
                    "chapter_number": chapter_number,
                    "title": None,
                    "files": [],
                }
            )

    return sorted(chapters, key=lambda chapter: chapter["chapter_number"])


def save_chapter_artifacts(
    project_id: str,
    chapter_plan: Any,
    chapter_draft: Any,
    quality_report: Any,
    final_chapter: Any,
    graph_delta: Any,
    root: str | Path = "projects",
) -> Path:
    """Persist a generated chapter's artifacts."""
    chapter_number = _field(chapter_plan, "chapter_number")
    chapter_dir = (
        Path(root) / project_id / "chapters" / f"chapter-{int(chapter_number):04d}"
    )
    chapter_dir.mkdir(parents=True, exist_ok=True)

    _write_json(chapter_dir / "plan.json", chapter_plan)
    _write_text(chapter_dir / "draft.md", _content_text(chapter_draft))
    _write_json(chapter_dir / "quality-report.json", quality_report)
    _write_text(chapter_dir / "final.md", _content_text(final_chapter))
    _write_json(chapter_dir / "graph-delta.json", graph_delta)
    _write_json(
        chapter_dir / "metadata.json",
        {
            "project_id": project_id,
            "chapter_number": int(chapter_number),
            "title": _field(chapter_plan, "title"),
            "files": [
                "plan.json",
                "draft.md",
                "quality-report.json",
                "final.md",
                "graph-delta.json",
            ],
        },
    )
    return chapter_dir


def save_outline(
    project_id: str, outline: list[Any], root: str | Path = "projects"
) -> Path:
    """Persist a project outline as JSON."""
    outline_path = Path(root) / project_id / "outline.json"
    _write_json(outline_path, outline)
    return outline_path


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


def _field(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value[name]
    return getattr(value, name)


def _content_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if "revised_content" in value:
            return value["revised_content"]
        return value["content"]
    if hasattr(value, "revised_content"):
        return value.revised_content
    return value.content


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
