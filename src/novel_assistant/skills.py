from __future__ import annotations

import re
from pathlib import Path

from pydantic import BaseModel


_SKILL_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_FRONTMATTER_PATTERN = re.compile(r"^---\n(?P<body>.*?)\n---\n?", re.DOTALL)


class SkillSummary(BaseModel):
    id: str
    name: str
    description: str | None = None


class SkillDefinition(SkillSummary):
    content: str


class SkillStore:
    def __init__(self, root: str | Path = "skills") -> None:
        self.root = Path(root)

    def list(self) -> list[SkillSummary]:
        if not self.root.exists():
            return []

        skills = []
        for skill_dir in self.root.iterdir():
            if not skill_dir.is_dir() or not _is_safe_skill_id(skill_dir.name):
                continue
            skill = self.get(skill_dir.name)
            if skill is None:
                continue
            skills.append(
                SkillSummary(
                    id=skill.id,
                    name=skill.name,
                    description=skill.description,
                )
            )
        return sorted(skills, key=lambda skill: skill.id)

    def get(self, skill_id: str) -> SkillDefinition | None:
        if not _is_safe_skill_id(skill_id):
            return None
        skill_path = self.root / skill_id / "SKILL.md"
        if not skill_path.exists():
            return None

        raw_content = skill_path.read_text(encoding="utf-8").strip()
        metadata, content = _split_frontmatter(raw_content)
        return SkillDefinition(
            id=skill_id,
            name=metadata.get("name") or skill_id,
            description=metadata.get("description"),
            content=content.strip(),
        )


def _split_frontmatter(raw_content: str) -> tuple[dict[str, str], str]:
    match = _FRONTMATTER_PATTERN.match(raw_content)
    if match is None:
        return {}, raw_content

    metadata = {}
    for line in match.group("body").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata, raw_content[match.end() :]


def _is_safe_skill_id(skill_id: str) -> bool:
    return _SKILL_ID_PATTERN.fullmatch(skill_id) is not None
