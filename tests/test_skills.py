from novel_assistant.skills import SkillStore


def test_skill_store_lists_skill_markdown_files(tmp_path):
    skill_dir = tmp_path / "skills" / "humanizer-zh"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        """---
name: humanizer-zh
description: 去除 AI 味
---

请把文本润色得更自然。
""",
        encoding="utf-8",
    )

    store = SkillStore(tmp_path / "skills")

    assert [skill.model_dump() for skill in store.list()] == [
        {
            "id": "humanizer-zh",
            "name": "humanizer-zh",
            "description": "去除 AI 味",
        }
    ]


def test_skill_store_loads_skill_content(tmp_path):
    skill_dir = tmp_path / "skills" / "humanizer-zh"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("请把文本润色得更自然。", encoding="utf-8")

    store = SkillStore(tmp_path / "skills")
    skill = store.get("humanizer-zh")

    assert skill is not None
    assert skill.id == "humanizer-zh"
    assert skill.content == "请把文本润色得更自然。"
    assert store.get("../escape") is None
