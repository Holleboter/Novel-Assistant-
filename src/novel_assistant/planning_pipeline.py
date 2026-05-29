from __future__ import annotations

import json
from typing import Any

from .llm_client import LLMClient, LLMRequestError
from .models import ChapterPlan, CharacterProfile, StoryBlueprint, UserRequirement


class DeterministicStoryPlanner:
    """Deterministic story planner for fast tests and offline demos."""

    def analyze_requirement(self, user_input: str) -> UserRequirement:
        return UserRequirement(
            premise=user_input,
            genre="悬疑奇幻",
            target_audience="青年读者",
            themes=["自我和解", "命运选择"],
            constraints=["第一章必须形成追查动机", "使用正常中文正文"],
        )

    def build_blueprint(self, requirement: UserRequirement) -> StoryBlueprint:
        return StoryBlueprint(
            title="雨廊来信",
            logline="失忆茶馆账房在雨夜收到未来来信，循着旧案找回被改写的真相。",
            setting="架空江南雨城",
            central_conflict="主角必须在救下旧友和保全整座城市之间做出选择。",
            themes=requirement.themes,
        )

    def build_characters(
        self,
        requirement: UserRequirement,
        blueprint: StoryBlueprint,
    ) -> list[CharacterProfile]:
        return [
            CharacterProfile(
                name="沈砚",
                role="主角",
                motivation="查清失忆前参与过的旧案真相",
                arc="从逃避过去到主动承担选择后果",
                traits=["谨慎", "敏锐", "重情"],
            ),
            CharacterProfile(
                name="陆青",
                role="旧友",
                motivation="阻止未来灾难提前发生",
                arc="从独自背负秘密到重新信任沈砚",
                traits=["沉着", "固执"],
            ),
        ]

    def plan_chapter(
        self,
        requirement: UserRequirement,
        blueprint: StoryBlueprint,
        characters: list[CharacterProfile],
        chapter_number: int = 1,
    ) -> ChapterPlan:
        protagonist = characters[0].name if characters else "主角"
        return ChapterPlan(
            chapter_number=chapter_number,
            title="雨夜来信",
            goal=f"让{protagonist}收到来自未来的信，并决定追查旧案。",
            key_events=["茶馆忽然停电", f"一封写着{protagonist}名字的信出现在柜台"],
            pov_character=protagonist,
        )


class LLMBackedStoryPlanner:
    """Story planner that asks an OpenAI-compatible LLM for structured JSON."""

    def __init__(self, llm_client: LLMClient | None = None):
        self.llm_client = llm_client or LLMClient()

    def analyze_requirement(self, user_input: str) -> UserRequirement:
        data = self._complete_json(
            "请把用户的小说需求整理成 UserRequirement JSON。premise 必须忠实保留原始需求中的核心场景、人物线索和剧情钩子。",
            {
                "user_input": user_input,
                "required_fields": [
                    "premise",
                    "genre",
                    "target_audience",
                    "themes",
                    "constraints",
                ],
            },
        )
        _normalize_list_fields(data, ["themes", "constraints"])
        return UserRequirement(**data)

    def build_blueprint(self, requirement: UserRequirement) -> StoryBlueprint:
        data = self._complete_json(
            "请根据需求生成小说蓝图 StoryBlueprint JSON。必须围绕 premise 展开，不得更换主场景或核心钩子。",
            {
                "requirement": requirement.model_dump(mode="json"),
                "required_fields": [
                    "title",
                    "logline",
                    "setting",
                    "central_conflict",
                    "themes",
                ],
            },
        )
        _normalize_list_fields(data, ["themes"])
        return StoryBlueprint(**data)

    def build_characters(
        self,
        requirement: UserRequirement,
        blueprint: StoryBlueprint,
    ) -> list[CharacterProfile]:
        data = self._complete_json(
            "请生成主要人物列表 CharacterProfile JSON 数组。",
            {
                "requirement": requirement.model_dump(mode="json"),
                "blueprint": blueprint.model_dump(mode="json"),
                "required_fields": [
                    "name",
                    "role",
                    "motivation",
                    "arc",
                    "traits",
                ],
            },
        )
        if not isinstance(data, list):
            raise LLMRequestError("Character planner response must be a JSON array")
        for item in data:
            _normalize_list_fields(item, ["traits"])
        return [CharacterProfile(**item) for item in data]

    def plan_chapter(
        self,
        requirement: UserRequirement,
        blueprint: StoryBlueprint,
        characters: list[CharacterProfile],
        chapter_number: int = 1,
    ) -> ChapterPlan:
        data = self._complete_json(
            "请生成第一章计划 ChapterPlan JSON。",
            {
                "chapter_number": chapter_number,
                "requirement": requirement.model_dump(mode="json"),
                "blueprint": blueprint.model_dump(mode="json"),
                "characters": [character.model_dump(mode="json") for character in characters],
                "required_fields": [
                    "chapter_number",
                    "title",
                    "goal",
                    "key_events",
                    "pov_character",
                ],
            },
        )
        _normalize_list_fields(data, ["key_events"])
        return ChapterPlan(**data)

    def _complete_json(self, task: str, payload: dict[str, Any]) -> Any:
        response = self.llm_client.complete(
            system_prompt=(
                "你是小说策划结构化助手。只输出 JSON，不要输出解释、Markdown 或多余文字。"
                "字段值必须是根据输入创作出的具体中文内容，禁止照抄 schema，"
                "禁止使用 string、integer、未命名、未知故事等占位内容。"
                "必须保留用户输入中的核心场景、角色线索和剧情钩子，不得替换成无关主线。"
            ),
            user_prompt=task + "\n\n输入：\n" + json.dumps(payload, ensure_ascii=False),
            temperature=0.3,
            max_tokens=1200,
        )
        return _parse_json_payload(response.content)


def _parse_json_payload(content: str) -> Any:
    text = content.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMRequestError("LLM planner response is not valid JSON") from exc


def _normalize_list_fields(data: Any, fields: list[str]) -> None:
    if not isinstance(data, dict):
        return
    for field in fields:
        value = data.get(field)
        if isinstance(value, str):
            data[field] = [value]
