from __future__ import annotations

from .llm_client import LLMClient
from .models import (
    ChapterDraft,
    ChapterPlan,
    GraphDelta,
    QualityIssue,
    QualityReport,
    RevisedChapterDraft,
)


class DeterministicWritingPipeline:
    """Deterministic writing pipeline for the MVP demo and fast tests."""

    def draft_chapter(
        self,
        plan: ChapterPlan,
        graph_context: dict | None = None,
    ) -> ChapterDraft:
        context = graph_context or {}
        protagonist = plan.pov_character or _first_value(context.get("protagonists")) or "主角"
        event_sentences = [
            f"{protagonist}经历了“{event}”，这件事把他推向更深的谜团。"
            for event in plan.key_events
        ]
        if not event_sentences:
            event_sentences = [f"{protagonist}沿着旧线索继续追查，发现真相比想象中更近。"]

        content = "\n".join(
            [
                f"《{plan.title}》",
                "",
                f"雨声压低了整条街的喧哗，{protagonist}守在茶馆柜台后，指尖还沾着冷掉的茶香。",
                f"这一章的目标很清楚：{plan.goal}",
                *event_sentences,
                "当最后一盏灯重新亮起时，柜台上多了一封没有邮戳的信。",
                f"{protagonist}拆开信封，看见第一行字像从未来落下：不要相信雨停之后第一个敲门的人。",
                "他把信贴进怀里，决定从今晚开始追查旧案，也追查那个尚未发生的明天。",
            ]
        )

        return ChapterDraft(
            chapter_number=plan.chapter_number,
            title=plan.title,
            content=content,
            summary=f"{protagonist}在雨夜收到异常来信，并决定追查隐藏在旧案后的真相。",
            word_count=len(content),
        )

    def quality_check(
        self,
        draft: ChapterDraft,
        plan: ChapterPlan,
        graph_context: dict | None = None,
    ) -> QualityReport:
        issues: list[QualityIssue] = []
        if plan.goal not in draft.content:
            issues.append(
                QualityIssue(
                    severity="high",
                    category="大纲贴合",
                    description="正文没有明确回应章节目标。",
                    suggestion="补写主角收到线索并主动追查的段落。",
                )
            )
        for event in plan.key_events:
            if event not in draft.content:
                issues.append(
                    QualityIssue(
                        severity="high",
                        category="关键事件",
                        description=f"正文缺少计划中的关键事件：{event}",
                        suggestion=f"把“{event}”写入章节行动链。",
                    )
                )
        if len(draft.content.strip()) < 40:
            issues.append(
                QualityIssue(
                    severity="medium",
                    category="篇幅与节奏",
                    description="章节内容过短，缺少足够的场景推进。",
                    suggestion="增加环境、动作和人物反应，让转折更完整。",
                )
            )

        serious_count = sum(1 for issue in issues if issue.severity in {"high", "blocking"})
        score = max(60, 92 - serious_count * 18 - (len(issues) - serious_count) * 5)
        return QualityReport(score=score, issues=issues)

    def revise_chapter(
        self,
        draft: ChapterDraft,
        report: QualityReport,
        plan: ChapterPlan | None = None,
    ) -> RevisedChapterDraft:
        if report.passed:
            return RevisedChapterDraft(
                original=draft,
                revised_content=draft.content,
                revision_notes=["质检通过，保持原稿。"],
            )

        additions: list[str] = []
        if plan is not None:
            additions.append(f"补充推进：{plan.goal}")
            additions.extend(f"补足事件：{event}" for event in plan.key_events if event not in draft.content)
        additions.extend(issue.suggestion for issue in report.issues if issue.suggestion)
        revised_content = draft.content.rstrip() + "\n\n" + "\n".join(dict.fromkeys(additions))

        return RevisedChapterDraft(
            original=draft,
            revised_content=revised_content,
            revision_notes=additions or ["根据质检意见补强章节因果与场景细节。"],
        )

    def extract_graph_delta(
        self,
        project_id: str,
        final_chapter: ChapterDraft | RevisedChapterDraft,
    ) -> GraphDelta:
        chapter_number = _chapter_number(final_chapter)
        title = _title(final_chapter)
        content = _content(final_chapter)
        chapter_id = f"{project_id}:chapter:{chapter_number}"
        event_id = f"{project_id}:event:{chapter_number}:future-letter"

        return GraphDelta(
            project_id=project_id,
            source_chapter_number=chapter_number,
            node_upserts=[
                {
                    "label": "Chapter",
                    "id": chapter_id,
                    "properties": {
                        "project_id": project_id,
                        "chapter_number": chapter_number,
                        "title": title,
                        "summary": content[:120],
                    },
                },
                {
                    "label": "Event",
                    "id": event_id,
                    "properties": {
                        "project_id": project_id,
                        "chapter_number": chapter_number,
                        "name": "收到未来来信",
                        "summary": "主角在雨夜收到未来来信，并决定追查旧案。",
                        "evidence": content[:120],
                    },
                },
                {
                    "label": "Novel",
                    "id": project_id,
                    "properties": {"latest_chapter": chapter_number},
                },
            ],
            relationship_upserts=[
                {
                    "source_label": "Chapter",
                    "source_id": chapter_id,
                    "target_label": "Event",
                    "target_id": event_id,
                    "type": "CONTAINS_EVENT",
                    "properties": {"source_chapter": chapter_number},
                }
            ],
        )


class LLMBackedWritingPipeline(DeterministicWritingPipeline):
    """Writing pipeline that delegates chapter drafting to a configured LLM."""

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        draft_max_tokens: int = 1200,
    ):
        self.llm_client = llm_client or LLMClient()
        self.draft_max_tokens = draft_max_tokens

    def draft_chapter(
        self,
        plan: ChapterPlan,
        graph_context: dict | None = None,
    ) -> ChapterDraft:
        response = self.llm_client.complete(
            system_prompt=(
                "你是小说章节写作助手。请严格根据章节计划写作，"
                "保留关键事件、主角行动动机和章节钩子。只输出章节正文。"
            ),
            user_prompt=_chapter_prompt(plan, graph_context or {}),
            max_tokens=self.draft_max_tokens,
        )
        content = response.content.strip()
        return ChapterDraft(
            chapter_number=plan.chapter_number,
            title=plan.title,
            content=content,
            summary=content[:120],
            word_count=len(content),
        )


def _first_value(values: object) -> str | None:
    if isinstance(values, list) and values:
        return str(values[0])
    return None


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


def _chapter_prompt(plan: ChapterPlan, graph_context: dict) -> str:
    active_hooks = graph_context.get("active_hooks", [])
    protagonists = graph_context.get("protagonists", [])
    key_events = "\n".join(f"- {event}" for event in plan.key_events) or "- 推进主线"
    hooks = "\n".join(f"- {hook}" for hook in active_hooks) or "- 无"
    protagonist_line = ", ".join(protagonists) if protagonists else plan.pov_character or "主角"
    return "\n".join(
        [
            "硬性约束：",
            f"- 第一行必须是《{plan.title}》。",
            f"- 必须使用视角人物：{plan.pov_character or protagonist_line}，不得擅自改名。",
            "- 必须逐项写入下面列出的关键事件，不要替换成无关桥段。",
            f"章节编号：第 {plan.chapter_number} 章",
            f"章节标题：{plan.title}",
            f"视角人物：{plan.pov_character or protagonist_line}",
            f"章节目标：{plan.goal}",
            "必须包含的关键事件：",
            key_events,
            "当前活跃钩子：",
            hooks,
            "写作要求：",
            "- 使用自然中文，不要输出解释。",
            "- 正文开头使用章节标题。",
            "- 让角色行动推动情节，不要只做设定说明。",
        ]
    )
