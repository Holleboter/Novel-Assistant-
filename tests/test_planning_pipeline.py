from novel_assistant.planning_pipeline import (
    DeterministicStoryPlanner,
    LLMBackedStoryPlanner,
)


class FakeLLMClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def complete(self, **kwargs):
        self.calls.append(kwargs)

        class Response:
            def __init__(self, content):
                self.content = content

        return Response(self.responses.pop(0))


def test_deterministic_story_planner_builds_mvp_structures():
    planner = DeterministicStoryPlanner()

    requirement = planner.analyze_requirement("写一个雨夜悬疑故事")
    blueprint = planner.build_blueprint(requirement)
    characters = planner.build_characters(requirement, blueprint)
    chapter_plan = planner.plan_chapter(requirement, blueprint, characters)

    assert requirement.premise == "写一个雨夜悬疑故事"
    assert blueprint.title == "雨廊来信"
    assert characters[0].name == "沈砚"
    assert chapter_plan.chapter_number == 1
    assert chapter_plan.pov_character == "沈砚"


def test_llm_story_planner_parses_structured_json_outputs():
    client = FakeLLMClient(
        [
            """
            {
              "premise": "雨夜茶馆收到未来来信",
              "genre": "悬疑奇幻",
              "target_audience": "青年读者",
              "themes": ["命运选择"],
              "constraints": ["第一章形成追查动机"]
            }
            """,
            """
            ```json
            {
              "title": "雨夜来信",
              "logline": "茶馆账房收到未来来信，循着旧案找回真相。",
              "setting": "架空江南雨城",
              "central_conflict": "主角必须在救下旧友和保全城市之间选择。",
              "themes": ["命运选择"]
            }
            ```
            """,
            """
            [
              {
                "name": "沈砚",
                "role": "主角",
                "motivation": "查清旧案真相",
                "arc": "从逃避过去到主动承担",
                "traits": ["谨慎", "敏锐"]
              }
            ]
            """,
            """
            {
              "chapter_number": 1,
              "title": "雨夜来信",
              "goal": "让沈砚收到未来来信，并决定追查旧案。",
              "key_events": ["茶馆忽然停电", "未来来信出现"],
              "pov_character": "沈砚"
            }
            """,
        ]
    )
    planner = LLMBackedStoryPlanner(llm_client=client)

    requirement = planner.analyze_requirement("写一个雨夜悬疑故事")
    blueprint = planner.build_blueprint(requirement)
    characters = planner.build_characters(requirement, blueprint)
    chapter_plan = planner.plan_chapter(requirement, blueprint, characters)

    assert requirement.genre == "悬疑奇幻"
    assert blueprint.title == "雨夜来信"
    assert characters[0].name == "沈砚"
    assert chapter_plan.key_events == ["茶馆忽然停电", "未来来信出现"]
    assert len(client.calls) == 4
    assert all("只输出 JSON" in call["system_prompt"] for call in client.calls)
    assert all("禁止照抄 schema" in call["system_prompt"] for call in client.calls)
    assert all("必须保留用户输入" in call["system_prompt"] for call in client.calls)


def test_llm_story_planner_normalizes_string_lists():
    client = FakeLLMClient(
        [
            """
            {
              "premise": "雨夜茶馆收到未来来信",
              "genre": "悬疑奇幻",
              "target_audience": "青年读者",
              "themes": "命运选择",
              "constraints": "第一章形成追查动机"
            }
            """,
            """
            [
              {
                "name": "沈砚",
                "role": "主角",
                "motivation": "查清旧案真相",
                "arc": "从逃避过去到主动承担",
                "traits": "谨慎"
              }
            ]
            """,
            """
            {
              "chapter_number": 1,
              "title": "雨夜来信",
              "goal": "让沈砚收到未来来信。",
              "key_events": "茶馆忽然停电",
              "pov_character": "沈砚"
            }
            """,
        ]
    )
    planner = LLMBackedStoryPlanner(llm_client=client)

    requirement = planner.analyze_requirement("写一个雨夜悬疑故事")
    characters = planner.build_characters(
        requirement,
        DeterministicStoryPlanner().build_blueprint(requirement),
    )
    chapter_plan = planner.plan_chapter(
        requirement,
        DeterministicStoryPlanner().build_blueprint(requirement),
        characters,
    )

    assert requirement.themes == ["命运选择"]
    assert requirement.constraints == ["第一章形成追查动机"]
    assert characters[0].traits == ["谨慎"]
    assert chapter_plan.key_events == ["茶馆忽然停电"]
