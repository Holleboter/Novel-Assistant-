from novel_assistant.workflow import build_workflow, initial_state


class FakeGraphRepository:
    def __init__(self):
        self.initial_writes = []
        self.delta_writes = []

    def ensure_constraints(self):
        return None

    def upsert_initial_graph(self, project_id, blueprint, characters):
        self.initial_writes.append(
            {
                "project_id": project_id,
                "blueprint": blueprint,
                "characters": characters,
            }
        )

    def apply_delta(self, delta):
        self.delta_writes.append(delta)


def test_initial_state_uses_demo_project_id():
    state = initial_state("写一个雨夜悬疑故事")

    assert state["project_id"] == "novel-demo"
    assert state["user_input"] == "写一个雨夜悬疑故事"


def test_initial_state_accepts_project_id_override():
    state = initial_state("write a mystery", project_id="rain-case")

    assert state["project_id"] == "rain-case"
    assert state["user_input"] == "write a mystery"


def test_workflow_generates_first_chapter_and_writes_graph_updates():
    repo = FakeGraphRepository()
    app = build_workflow(graph_repository=repo)

    result = app.invoke(initial_state("写一本悬疑奇幻小说，主角在雨夜茶馆收到未来来信。"))

    assert result["project_id"] == "novel-demo"
    assert result["final_chapter"].chapter_number == 1
    assert result["final_chapter"].title
    assert result["quality_report"].passed is True
    assert repo.initial_writes
    assert repo.initial_writes[0]["project_id"] == "novel-demo"
    assert all(
        character.id.startswith("novel-demo:char-")
        for character in repo.initial_writes[0]["characters"]
    )
    assert repo.delta_writes
    assert repo.delta_writes[0].node_upserts


def test_run_demo_returns_workflow_result_without_real_neo4j(monkeypatch):
    from novel_assistant import demo

    repo = FakeGraphRepository()

    class FakeRepositoryFactory:
        def __call__(self):
            return repo

    monkeypatch.setattr(demo, "GraphRepository", FakeRepositoryFactory())

    result = demo.run_demo("写一个雨夜悬疑故事", save=False)

    assert result["final_chapter"].chapter_number == 1
    assert result["final_chapter"].content.startswith("《雨夜来信》")
    assert repo.initial_writes
    assert repo.delta_writes


def test_run_demo_can_use_llm_pipeline_without_real_neo4j(monkeypatch):
    from novel_assistant import demo

    repo = FakeGraphRepository()

    class FakeRepositoryFactory:
        def __call__(self):
            return repo

    class FakeLLMClient:
        def __init__(self):
            self.responses = [
                '{"premise":"雨夜茶馆收到未来来信","genre":"悬疑奇幻","target_audience":"青年读者","themes":["命运选择"],"constraints":["第一章形成追查动机"]}',
                '{"title":"雨夜来信","logline":"茶馆账房收到未来来信。","setting":"雨城","central_conflict":"主角追查旧案。","themes":["命运选择"]}',
                '[{"name":"沈砚","role":"主角","motivation":"追查旧案","arc":"从逃避到承担","traits":["谨慎"]}]',
                '{"chapter_number":1,"title":"雨夜来信","goal":"让沈砚收到未来来信，并决定追查旧案。","key_events":["茶馆忽然停电","未来来信出现"],"pov_character":"沈砚"}',
                "《雨夜来信》\n\n沈砚收到未来来信，决定追查旧案。",
            ]

        def complete(self, **kwargs):
            class Response:
                def __init__(self, content):
                    self.content = content

            return Response(self.responses.pop(0))

    monkeypatch.setattr(demo, "GraphRepository", FakeRepositoryFactory())

    result = demo.run_demo(
        "写一个雨夜悬疑故事",
        save=False,
        use_llm=True,
        llm_client=FakeLLMClient(),
    )

    assert "未来来信" in result["chapter_draft"].content
    assert repo.delta_writes
