from pathlib import Path

import pytest

from novel_assistant.config import LLMSettings, Neo4jSettings
from novel_assistant.models import (
    ChapterDraft,
    ChapterPlan,
    CharacterProfile,
    CharacterRelationship,
    GraphDelta,
    QualityIssue,
    QualityReport,
    RevisedChapterDraft,
    StoryBlueprint,
    UserRequirement,
)


def test_neo4j_settings_provide_local_defaults():
    settings = Neo4jSettings(_env_file=None)

    assert settings.uri == "bolt://localhost:7687"
    assert settings.user == "neo4j"
    assert settings.password == "change_me"


def test_neo4j_settings_can_be_loaded_from_env_file(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "NEO4J_URI=bolt://example.com:7687",
                "NEO4J_USER=writer",
                "NEO4J_PASSWORD=secret_pass",
            ]
        ),
        encoding="utf-8",
    )

    settings = Neo4jSettings(_env_file=env_file)

    assert settings.uri == "bolt://example.com:7687"
    assert settings.user == "writer"
    assert settings.password == "secret_pass"


def test_llm_settings_provide_provider_neutral_defaults():
    settings = LLMSettings(_env_file=None)

    assert settings.provider == "openai_compatible"
    assert settings.model == ""
    assert settings.api_key is None
    assert settings.base_url is None
    assert settings.temperature == 0.7
    assert settings.max_tokens == 4000
    assert settings.timeout_seconds == 120


def test_llm_settings_can_be_loaded_from_env_file(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "LLM_PROVIDER=deepseek",
                "LLM_MODEL=deepseek-chat",
                "LLM_API_KEY=test-key",
                "LLM_BASE_URL=https://api.deepseek.com",
                "LLM_TEMPERATURE=0.4",
                "LLM_MAX_TOKENS=6000",
                "LLM_TIMEOUT_SECONDS=90",
            ]
        ),
        encoding="utf-8",
    )

    settings = LLMSettings(_env_file=env_file)

    assert settings.provider == "deepseek"
    assert settings.model == "deepseek-chat"
    assert settings.api_key == "test-key"
    assert settings.base_url == "https://api.deepseek.com/v1"
    assert settings.temperature == 0.4
    assert settings.max_tokens == 6000
    assert settings.timeout_seconds == 90


def test_llm_settings_treat_blank_optional_values_as_missing(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "LLM_API_KEY=",
                "LLM_BASE_URL=",
            ]
        ),
        encoding="utf-8",
    )

    settings = LLMSettings(_env_file=env_file)

    assert settings.api_key is None
    assert settings.base_url is None


def test_llm_settings_normalize_deepseek_base_url():
    settings = LLMSettings(
        provider="deepseek",
        base_url="https://api.deepseek.com",
    )

    assert settings.base_url == "https://api.deepseek.com/v1"


def test_story_models_accept_normal_chinese_samples():
    requirement = UserRequirement(
        premise="一个失忆的茶馆账房在雨夜收到未来自己的来信。",
        genre="悬疑奇幻",
        target_audience="青年读者",
        themes=["自我和解", "命运选择"],
        constraints=["第一人称", "节奏紧凑"],
    )
    blueprint = StoryBlueprint(
        title="雨巷来信",
        logline="账房循着来信追查旧案，却发现写信人正是未来的自己。",
        setting="架空江南城",
        central_conflict="主角必须在救下挚友和保全整座城之间做选择。",
        themes=requirement.themes,
    )
    protagonist = CharacterProfile(
        name="沈砚",
        role="主角",
        motivation="查清失忆前的真相",
        arc="从逃避过去到主动承担选择",
        traits=["谨慎", "敏锐"],
    )
    relationship = CharacterRelationship(
        source="沈砚",
        target="陆青",
        relation="旧友",
        description="二人曾共同调查城中连环失踪案。",
    )
    chapter_plan = ChapterPlan(
        chapter_number=1,
        title="雨夜信笺",
        goal="让主角收到未来来信并决定追查。",
        key_events=["茶馆停电", "陌生信笺出现"],
        pov_character="沈砚",
    )
    draft = ChapterDraft(
        chapter_number=1,
        title="雨夜信笺",
        content="雨落在青石板上，茶馆最后一盏灯忽然灭了。",
        summary="沈砚收到一封署着自己名字的来信。",
        word_count=1200,
    )
    issue = QualityIssue(
        severity="medium",
        category="节奏",
        description="开头信息量略密。",
        suggestion="拆分线索，让读者逐步理解。",
    )
    report = QualityReport(score=88, issues=[issue])
    revised = RevisedChapterDraft(
        original=draft,
        revised_content="雨声先到，灯影随后晃了一下，茶馆静得只剩算盘珠声。",
        revision_notes=["放慢开场节奏", "强化雨夜氛围"],
    )
    graph_delta = GraphDelta(
        new_nodes=[{"label": "Character", "name": protagonist.name}],
        new_relationships=[
            {
                "source": relationship.source,
                "target": relationship.target,
                "type": relationship.relation,
            }
        ],
        updated_nodes=[{"label": "Story", "title": blueprint.title}],
    )

    assert requirement.genre == "悬疑奇幻"
    assert blueprint.title == "雨巷来信"
    assert protagonist.name == "沈砚"
    assert relationship.target == "陆青"
    assert chapter_plan.key_events == ["茶馆停电", "陌生信笺出现"]
    assert draft.word_count == 1200
    assert report.passed is True
    assert revised.revision_notes == ["放慢开场节奏", "强化雨夜氛围"]
    assert graph_delta.new_nodes[0]["name"] == "沈砚"


@pytest.mark.parametrize("severity", ["high", "blocking"])
def test_quality_report_fails_when_issue_is_high_or_blocking(severity: str):
    report = QualityReport(
        score=95,
        issues=[
            QualityIssue(
                severity=severity,
                category="连贯性",
                description="关键动机缺失。",
                suggestion="补充角色行动原因。",
            )
        ],
    )

    assert report.revision_required is True
    assert report.passed is False


def test_quality_report_fails_when_score_is_below_85():
    report = QualityReport(score=84, issues=[])

    assert report.revision_required is True
    assert report.passed is False


def test_quality_report_passes_when_score_is_at_least_85_without_serious_issues():
    report = QualityReport(
        score=85,
        issues=[
            QualityIssue(
                severity="low",
                category="措辞",
                description="个别句子略重复。",
                suggestion="删去重复修饰。",
            )
        ],
    )

    assert report.revision_required is False
    assert report.passed is True
