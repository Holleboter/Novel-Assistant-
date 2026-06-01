import json

from pydantic import BaseModel

from novel_assistant import storage
from novel_assistant.models import (
    ChapterDraft,
    ChapterPlan,
    GraphDelta,
    QualityReport,
    RevisedChapterDraft,
)
from novel_assistant.storage import save_outline, save_workflow_result
from novel_assistant.workflow import build_workflow, initial_state


class OutlineChapter(BaseModel):
    chapter_number: int
    title: str


class FakeGraphRepository:
    def ensure_constraints(self):
        return None

    def upsert_initial_graph(self, project_id, blueprint, characters):
        return None

    def apply_delta(self, delta):
        return None


def test_save_workflow_result_writes_chapter_artifacts(tmp_path):
    app = build_workflow(graph_repository=FakeGraphRepository())
    result = app.invoke(initial_state("写一本雨夜悬疑奇幻小说"))

    project_dir = save_workflow_result(result, root=tmp_path)
    chapter_dir = project_dir / "chapters" / "chapter-0001"

    assert project_dir.name == "novel-demo"
    assert (project_dir / "project.json").exists()
    assert (project_dir / "blueprint.json").exists()
    assert (chapter_dir / "plan.json").exists()
    assert (chapter_dir / "draft.md").read_text(encoding="utf-8").startswith("《")
    assert (chapter_dir / "quality-report.json").exists()
    assert (chapter_dir / "final.md").read_text(encoding="utf-8").startswith("《")
    assert (chapter_dir / "graph-delta.json").exists()
    metadata = json.loads((chapter_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["project_id"] == "novel-demo"
    assert metadata["chapter_number"] == 1


def test_save_outline_writes_json_with_chinese_titles_and_chapter_numbers(tmp_path):
    outline = [
        OutlineChapter(chapter_number=1, title="雨夜来客"),
        {"chapter_number": 2, "title": "旧城谜影"},
        {
            "chapter_number": 3,
            "title": "终章",
            "beats": ["真相揭晓", {"chapter_number": 3, "title": "余波"}],
        },
    ]

    outline_path = save_outline("novel-demo", outline, root=tmp_path)

    assert outline_path == tmp_path / "novel-demo" / "outline.json"
    assert outline_path.exists()
    saved_outline = json.loads(outline_path.read_text(encoding="utf-8"))
    assert saved_outline[0]["title"] == "雨夜来客"
    assert saved_outline[0]["chapter_number"] == 1
    assert saved_outline[1]["title"] == "旧城谜影"
    assert saved_outline[1]["chapter_number"] == 2
    assert saved_outline[2]["beats"][1]["title"] == "余波"


def test_load_outline_reads_json_with_chinese_titles_and_chapter_numbers(tmp_path):
    outline = [
        {"chapter_number": 1, "title": "\u96e8\u591c\u6765\u5ba2"},
        {"chapter_number": 2, "title": "\u65e7\u57ce\u8c1c\u5f71"},
    ]
    outline_path = tmp_path / "novel-demo" / "outline.json"
    outline_path.parent.mkdir(parents=True)
    outline_path.write_text(json.dumps(outline, ensure_ascii=False), encoding="utf-8")

    loaded_outline = storage.load_outline("novel-demo", root=tmp_path)

    assert loaded_outline == outline


def test_load_outline_raises_when_outline_missing(tmp_path):
    try:
        storage.load_outline("missing-project", root=tmp_path)
    except FileNotFoundError as exc:
        assert exc.filename == str(tmp_path / "missing-project" / "outline.json")
    else:
        raise AssertionError("Expected FileNotFoundError")


def test_save_chapter_artifacts_writes_files_and_metadata_with_chinese_title(tmp_path):
    chapter_dir = storage.save_chapter_artifacts(
        "novel-demo",
        ChapterPlan(
            chapter_number=12,
            title="\u96e8\u591c\u6765\u5ba2",
            goal="\u63ed\u5f00\u7b2c\u4e00\u4e2a\u8c1c\u56e2",
            key_events=["\u706f\u4e0b\u76f8\u9022"],
        ),
        ChapterDraft(
            chapter_number=12,
            title="\u96e8\u591c\u6765\u5ba2",
            content="\u521d\u7a3f\u5185\u5bb9",
        ),
        QualityReport(score=92),
        RevisedChapterDraft(
            original=ChapterDraft(
                chapter_number=12,
                title="\u96e8\u591c\u6765\u5ba2",
                content="\u521d\u7a3f\u5185\u5bb9",
            ),
            revised_content="\u7ec8\u7a3f\u5185\u5bb9",
        ),
        GraphDelta(project_id="novel-demo", source_chapter_number=12),
        root=tmp_path,
    )

    assert chapter_dir == tmp_path / "novel-demo" / "chapters" / "chapter-0012"
    assert json.loads((chapter_dir / "plan.json").read_text(encoding="utf-8"))[
        "title"
    ] == "\u96e8\u591c\u6765\u5ba2"
    assert (chapter_dir / "draft.md").read_text(encoding="utf-8") == "\u521d\u7a3f\u5185\u5bb9"
    assert json.loads((chapter_dir / "quality-report.json").read_text(encoding="utf-8"))[
        "score"
    ] == 92
    assert (chapter_dir / "final.md").read_text(encoding="utf-8") == "\u7ec8\u7a3f\u5185\u5bb9"
    assert (chapter_dir / "graph-delta.json").exists()
    metadata = json.loads((chapter_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["project_id"] == "novel-demo"
    assert metadata["chapter_number"] == 12
    assert metadata["title"] == "\u96e8\u591c\u6765\u5ba2"


def test_list_chapters_returns_metadata_sorted_by_chapter_number(tmp_path):
    chapters_dir = tmp_path / "novel-demo" / "chapters"
    for number, title in [(10, "\u7ec8\u5c40"), (2, "\u65e7\u57ce"), (1, "\u96e8\u591c")]:
        chapter_dir = chapters_dir / f"chapter-{number:04d}"
        chapter_dir.mkdir(parents=True)
        (chapter_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "project_id": "novel-demo",
                    "chapter_number": number,
                    "title": title,
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    chapters = storage.list_chapters("novel-demo", root=tmp_path)

    assert [chapter["chapter_number"] for chapter in chapters] == [1, 2, 10]
    assert [chapter["title"] for chapter in chapters] == [
        "\u96e8\u591c",
        "\u65e7\u57ce",
        "\u7ec8\u5c40",
    ]


def test_list_chapters_returns_empty_list_when_no_chapters_exist(tmp_path):
    assert storage.list_chapters("novel-demo", root=tmp_path) == []


def test_read_chapter_content_prefers_confirmed_final_file(tmp_path):
    chapter_dir = tmp_path / "novel-demo" / "chapters" / "chapter-0001"
    chapter_dir.mkdir(parents=True)
    (chapter_dir / "draft.md").write_text("draft content", encoding="utf-8")
    (chapter_dir / "final.md").write_text("final content", encoding="utf-8")

    content = storage.read_chapter_content("novel-demo", 1, root=tmp_path)

    assert content == {
        "project_id": "novel-demo",
        "chapter_number": 1,
        "filename": "final.md",
        "source": "final",
        "content": "final content",
    }


def test_confirm_chapter_content_writes_named_final_file_and_metadata(tmp_path):
    chapter_dir = tmp_path / "novel-demo" / "chapters" / "chapter-0001"
    chapter_dir.mkdir(parents=True)
    (chapter_dir / "draft.md").write_text("draft content", encoding="utf-8")
    (chapter_dir / "metadata.json").write_text(
        json.dumps(
            {
                "project_id": "novel-demo",
                "chapter_number": 1,
                "title": "Rain Letter",
                "files": ["draft.md", "metadata.json"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = storage.confirm_chapter_content(
        "novel-demo",
        1,
        content="human edited final",
        filename="rain-letter-final.md",
        root=tmp_path,
    )

    assert result["filename"] == "rain-letter-final.md"
    assert (chapter_dir / "rain-letter-final.md").read_text(encoding="utf-8") == (
        "human edited final"
    )
    metadata = json.loads((chapter_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["status"] == "confirmed"
    assert metadata["content_source"] == "human_confirmed"
    assert metadata["final_filename"] == "rain-letter-final.md"
    assert "rain-letter-final.md" in metadata["files"]


def test_confirm_chapter_content_rejects_unsafe_filename(tmp_path):
    chapter_dir = tmp_path / "novel-demo" / "chapters" / "chapter-0001"
    chapter_dir.mkdir(parents=True)

    try:
        storage.confirm_chapter_content(
            "novel-demo",
            1,
            content="human edited final",
            filename="../escape.md",
            root=tmp_path,
        )
    except ValueError as exc:
        assert "Invalid final filename" in str(exc)
    else:
        raise AssertionError("Expected ValueError")
