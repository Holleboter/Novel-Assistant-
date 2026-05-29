import json

from novel_assistant.storage import save_workflow_result
from novel_assistant.workflow import build_workflow, initial_state


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
