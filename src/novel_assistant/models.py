from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class UserRequirement(BaseModel):
    premise: str
    genre: str
    target_audience: str | None = None
    themes: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class StoryBlueprint(BaseModel):
    title: str
    logline: str
    setting: str
    central_conflict: str
    themes: list[str] = Field(default_factory=list)


class CharacterProfile(BaseModel):
    name: str
    role: str
    motivation: str
    arc: str
    traits: list[str] = Field(default_factory=list)


class CharacterRelationship(BaseModel):
    source: str
    target: str
    relation: str
    description: str | None = None


class ChapterPlan(BaseModel):
    chapter_number: int
    title: str
    goal: str
    key_events: list[str] = Field(default_factory=list)
    pov_character: str | None = None


class ChapterDraft(BaseModel):
    chapter_number: int
    title: str
    content: str
    summary: str | None = None
    word_count: int | None = Field(default=None, ge=0)


class QualityIssue(BaseModel):
    severity: Literal["low", "medium", "high", "blocking"]
    category: str
    description: str
    suggestion: str | None = None


class QualityReport(BaseModel):
    score: int = Field(ge=0, le=100)
    issues: list[QualityIssue] = Field(default_factory=list)
    revision_required: bool | None = None
    passed: bool | None = None

    @model_validator(mode="after")
    def derive_status(self) -> "QualityReport":
        has_serious_issue = any(
            issue.severity in {"high", "blocking"} for issue in self.issues
        )
        revision_required = has_serious_issue or self.score < 85
        self.revision_required = revision_required
        self.passed = not revision_required
        return self


class RevisedChapterDraft(BaseModel):
    original: ChapterDraft
    revised_content: str
    revision_notes: list[str] = Field(default_factory=list)


class GraphDelta(BaseModel):
    project_id: str | None = None
    source_chapter_number: int | None = None
    node_upserts: list[dict[str, Any]] = Field(default_factory=list)
    relationship_upserts: list[dict[str, Any]] = Field(default_factory=list)
    status_updates: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_delta_shape(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "node_upserts" not in data:
            data["node_upserts"] = [
                *data.get("new_nodes", []),
                *data.get("updated_nodes", []),
            ]
        if "relationship_upserts" not in data:
            data["relationship_upserts"] = data.get("new_relationships", [])
        return data

    @property
    def new_nodes(self) -> list[dict[str, Any]]:
        return self.node_upserts

    @property
    def new_relationships(self) -> list[dict[str, Any]]:
        return self.relationship_upserts

    @property
    def updated_nodes(self) -> list[dict[str, Any]]:
        return []
