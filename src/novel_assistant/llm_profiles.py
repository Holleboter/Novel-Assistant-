from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel


class LLMProfile(BaseModel):
    id: str
    name: str
    provider: str
    model: str
    base_url: str | None = None
    api_key: str | None = None
    temperature: float = 0.7
    max_tokens: int = 4000
    timeout_seconds: int = 120


class PublicLLMProfile(BaseModel):
    id: str
    name: str
    provider: str
    model: str
    base_url: str | None = None
    api_key_set: bool
    temperature: float
    max_tokens: int
    timeout_seconds: int


class LLMProfileStore:
    def __init__(self, path: str | Path = "data/llm-profiles.json") -> None:
        self.path = Path(path)

    def list(self) -> list[LLMProfile]:
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return [LLMProfile.model_validate(profile) for profile in data]

    def list_public(self) -> list[PublicLLMProfile]:
        return [
            PublicLLMProfile(
                id=profile.id,
                name=profile.name,
                provider=profile.provider,
                model=profile.model,
                base_url=profile.base_url,
                api_key_set=profile.api_key is not None,
                temperature=profile.temperature,
                max_tokens=profile.max_tokens,
                timeout_seconds=profile.timeout_seconds,
            )
            for profile in self.list()
        ]

    def get(self, profile_id: str) -> LLMProfile | None:
        return next(
            (profile for profile in self.list() if profile.id == profile_id),
            None,
        )

    def upsert(self, profile: LLMProfile) -> LLMProfile:
        profiles = self.list()
        for index, existing_profile in enumerate(profiles):
            if existing_profile.id == profile.id:
                profiles[index] = profile
                self._write(profiles)
                return profile

        profiles.append(profile)
        self._write(profiles)
        return profile

    def delete(self, profile_id: str) -> bool:
        profiles = self.list()
        remaining_profiles = [
            profile for profile in profiles if profile.id != profile_id
        ]
        if len(remaining_profiles) == len(profiles):
            return False

        self._write(remaining_profiles)
        return True

    def _write(self, profiles: list[LLMProfile]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                [profile.model_dump(mode="json") for profile in profiles],
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
