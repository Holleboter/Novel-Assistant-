from __future__ import annotations

import errno
import json
import re
from pathlib import Path
from typing import Any

from .models import ChapterDraft, RevisedChapterDraft


_CHAPTER_DIR_PATTERN = re.compile(r"^chapter-(\d{4})$")
_FINAL_FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}\.md$")


def create_project(
    project_id: str,
    title: str | None = None,
    root: str | Path = "projects",
) -> dict[str, Any]:
    """Create a project directory and persist project metadata."""
    project_dir = Path(root) / project_id
    if project_dir.exists():
        raise FileExistsError(errno.EEXIST, "Project already exists", str(project_dir))

    project_dir.mkdir(parents=True)
    metadata = {
        "project_id": project_id,
        "title": title,
    }
    _write_json(project_dir / "project.json", metadata)
    return metadata


def list_projects(root: str | Path = "projects") -> list[dict[str, Any]]:
    """Return project summaries sorted by project id."""
    root_path = Path(root)
    if not root_path.exists():
        return []

    projects: list[dict[str, Any]] = []
    for project_dir in root_path.iterdir():
        if not project_dir.is_dir():
            continue
        project_id = project_dir.name
        metadata_path = project_dir / "project.json"
        metadata = (
            json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata_path.exists()
            else {}
        )
        outline_path = project_dir / "outline.json"
        projects.append(
            {
                "project_id": metadata.get("project_id", project_id),
                "title": metadata.get("title"),
                "has_outline": outline_path.exists(),
                "outline_path": str(outline_path) if outline_path.exists() else None,
                "chapter_count": len(list_chapters(project_id, root=root_path)),
            }
        )

    return sorted(projects, key=lambda project: project["project_id"])


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


def read_chapter_content(
    project_id: str,
    chapter_number: int,
    root: str | Path = "projects",
) -> dict[str, Any]:
    """Return editable markdown content for a chapter."""
    chapter_dir = _chapter_dir(project_id, chapter_number, root)
    metadata = _read_metadata(chapter_dir)
    final_filename = metadata.get("final_filename", "final.md")
    candidates = [
        (final_filename, "final"),
        ("final.md", "final"),
        ("draft.md", "draft"),
    ]
    for filename, source in candidates:
        path = chapter_dir / filename
        if path.exists():
            return {
                "project_id": project_id,
                "chapter_number": chapter_number,
                "filename": filename,
                "source": source,
                "content": path.read_text(encoding="utf-8"),
            }
    raise FileNotFoundError(errno.ENOENT, "No chapter content found", str(chapter_dir))


def read_chapter_quality_report(
    project_id: str,
    chapter_number: int,
    root: str | Path = "projects",
) -> dict[str, Any]:
    """Return the saved quality report for a chapter."""
    report_path = _chapter_dir(project_id, chapter_number, root) / "quality-report.json"
    if not report_path.exists():
        raise FileNotFoundError(
            errno.ENOENT,
            "Quality report not found",
            str(report_path),
        )
    return json.loads(report_path.read_text(encoding="utf-8"))


def save_chapter_quality_report(
    project_id: str,
    chapter_number: int,
    quality_report: Any,
    root: str | Path = "projects",
) -> Path:
    """Persist a chapter quality report without confirming final content."""
    chapter_dir = _chapter_dir(project_id, chapter_number, root)
    chapter_dir.mkdir(parents=True, exist_ok=True)
    report_path = chapter_dir / "quality-report.json"
    _write_json(report_path, quality_report)

    metadata = _read_metadata(chapter_dir)
    files = set(metadata.get("files", []))
    files.add("quality-report.json")
    metadata.update(
        {
            "project_id": project_id,
            "chapter_number": int(chapter_number),
            "files": sorted(files),
        }
    )
    _write_json(chapter_dir / "metadata.json", metadata)
    return report_path


def confirm_chapter_content(
    project_id: str,
    chapter_number: int,
    content: str,
    filename: str = "final.md",
    root: str | Path = "projects",
) -> dict[str, Any]:
    """Persist the human-confirmed final markdown for a chapter."""
    if _FINAL_FILENAME_PATTERN.fullmatch(filename) is None:
        raise ValueError("Invalid final filename")

    chapter_dir = _chapter_dir(project_id, chapter_number, root)
    chapter_dir.mkdir(parents=True, exist_ok=True)
    final_path = chapter_dir / filename
    final_path.write_text(content, encoding="utf-8")

    metadata = _read_metadata(chapter_dir)
    files = set(metadata.get("files", []))
    files.add(filename)
    metadata.update(
        {
            "project_id": project_id,
            "chapter_number": chapter_number,
            "status": "confirmed",
            "content_source": "human_confirmed",
            "final_filename": filename,
            "files": sorted(files),
        }
    )
    _write_json(chapter_dir / "metadata.json", metadata)
    return {
        "project_id": project_id,
        "chapter_number": chapter_number,
        "filename": filename,
        "status": "confirmed",
        "content_source": "human_confirmed",
        "path": str(final_path),
    }


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
    chapter_results = result.get(
        "chapter_results",
        [
            {
                "chapter_plan": result["chapter_plan"],
                "chapter_draft": result["chapter_draft"],
                "quality_report": result["quality_report"],
                "final_chapter": result["final_chapter"],
                "graph_delta": result["graph_delta"],
            }
        ],
    )
    latest_chapter = max(
        _chapter_number(chapter_result["final_chapter"])
        for chapter_result in chapter_results
    )

    _write_json(
        project_dir / "project.json",
        {
            "project_id": project_id,
            "title": result["blueprint"].title,
            "latest_chapter": latest_chapter,
        },
    )
    _write_json(project_dir / "blueprint.json", result["blueprint"])
    _write_json(project_dir / "outline.json", result.get("outline", [result["chapter_plan"]]))
    for chapter_result in chapter_results:
        save_chapter_artifacts(
            project_id=project_id,
            chapter_plan=chapter_result["chapter_plan"],
            chapter_draft=chapter_result["chapter_draft"],
            quality_report=chapter_result["quality_report"],
            final_chapter=chapter_result["final_chapter"],
            graph_delta=chapter_result["graph_delta"],
            root=root,
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


def _chapter_dir(project_id: str, chapter_number: int, root: str | Path) -> Path:
    return Path(root) / project_id / "chapters" / f"chapter-{int(chapter_number):04d}"


def _read_metadata(chapter_dir: Path) -> dict[str, Any]:
    metadata_path = chapter_dir / "metadata.json"
    if not metadata_path.exists():
        return {}
    return json.loads(metadata_path.read_text(encoding="utf-8"))


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
