from novel_assistant.models import ChapterDraft, ChapterPlan, RevisedChapterDraft
from novel_assistant.writing_pipeline import DeterministicWritingPipeline, LLMBackedWritingPipeline


def test_draft_chapter_generates_normal_chinese_content():
    pipeline = DeterministicWritingPipeline()
    plan = ChapterPlan(
        chapter_number=1,
        title="雨夜来信",
        goal="让沈砚收到来自未来的信，并决定追查旧案。",
        key_events=["茶馆忽然停电", "一封写着沈砚名字的信出现在柜台"],
        pov_character="沈砚",
    )

    draft = pipeline.draft_chapter(plan, graph_context={"active_hooks": []})

    assert draft.chapter_number == 1
    assert draft.title == "雨夜来信"
    assert "沈砚" in draft.content
    assert "茶馆忽然停电" in draft.content
    assert "乱码" not in draft.content
    assert draft.word_count == len(draft.content)


def test_quality_check_passes_for_complete_draft():
    pipeline = DeterministicWritingPipeline()
    plan = ChapterPlan(
        chapter_number=1,
        title="雨夜来信",
        goal="让沈砚收到来自未来的信，并决定追查旧案。",
        key_events=["茶馆忽然停电", "一封写着沈砚名字的信出现在柜台"],
        pov_character="沈砚",
    )
    draft = pipeline.draft_chapter(plan, graph_context={})

    report = pipeline.quality_check(draft, plan)

    assert report.score >= 85
    assert report.passed is True
    assert report.revision_required is False


def test_revise_chapter_returns_revised_draft_when_quality_fails():
    pipeline = DeterministicWritingPipeline()
    plan = ChapterPlan(
        chapter_number=1,
        title="雨夜来信",
        goal="让沈砚收到来自未来的信，并决定追查旧案。",
        key_events=["茶馆忽然停电"],
        pov_character="沈砚",
    )
    weak_draft = ChapterDraft(
        chapter_number=1,
        title="雨夜来信",
        content="沈砚看见一封信。",
        summary="沈砚收到信。",
        word_count=8,
    )
    report = pipeline.quality_check(weak_draft, plan)

    revised = pipeline.revise_chapter(weak_draft, report, plan)

    assert isinstance(revised, RevisedChapterDraft)
    assert "茶馆忽然停电" in revised.revised_content
    assert revised.revision_notes


def test_extract_graph_delta_records_chapter_facts():
    pipeline = DeterministicWritingPipeline()
    final_chapter = ChapterDraft(
        chapter_number=1,
        title="雨夜来信",
        content="雨夜里，沈砚在茶馆收到未来来信，并决定追查陆青失踪旧案。",
        summary="沈砚收到未来来信并开始追查旧案。",
        word_count=31,
    )

    delta = pipeline.extract_graph_delta("novel-demo", final_chapter)

    assert delta.new_nodes
    assert delta.new_relationships
    assert any(node.get("label") == "Chapter" for node in delta.new_nodes)
    assert any(node.get("label") == "Event" for node in delta.new_nodes)


def test_llm_backed_pipeline_uses_llm_client_for_draft_chapter():
    calls = []

    class FakeLLMClient:
        def complete(self, **kwargs):
            calls.append(kwargs)

            class Response:
                content = "《雨夜来信》\n\n沈砚在茶馆忽然停电时收到未来来信，并决定追查旧案。"

            return Response()

    pipeline = LLMBackedWritingPipeline(llm_client=FakeLLMClient())
    plan = ChapterPlan(
        chapter_number=1,
        title="雨夜来信",
        goal="让沈砚收到来自未来的信，并决定追查旧案。",
        key_events=["茶馆忽然停电", "未来来信出现"],
        pov_character="沈砚",
    )

    draft = pipeline.draft_chapter(plan, graph_context={"active_hooks": ["未来来信"]})

    assert draft.title == "雨夜来信"
    assert "未来来信" in draft.content
    assert draft.word_count == len(draft.content)
    assert calls
    assert "小说章节写作助手" in calls[0]["system_prompt"]
    assert "茶馆忽然停电" in calls[0]["user_prompt"]
    assert "第一行必须是《雨夜来信》" in calls[0]["user_prompt"]
    assert "不得擅自改名" in calls[0]["user_prompt"]
    assert calls[0]["max_tokens"] == 1200
