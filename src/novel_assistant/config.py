from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Neo4jSettings(BaseSettings):
    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: str = "change_me"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="NEO4J_",
        extra="ignore",
    )


class LLMSettings(BaseSettings):
    provider: str = "openai_compatible"
    model: str = ""
    api_key: str | None = None
    base_url: str | None = None
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=4000, gt=0)
    timeout_seconds: int = Field(default=120, gt=0)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LLM_",
        extra="ignore",
    )

    @field_validator("api_key", "base_url", mode="before")
    @classmethod
    def blank_optional_values_are_missing(cls, value: str | None) -> str | None:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @model_validator(mode="after")
    def normalize_provider_base_url(self) -> "LLMSettings":
        if (
            self.provider == "deepseek"
            and self.base_url is not None
            and self.base_url.rstrip("/") == "https://api.deepseek.com"
        ):
            self.base_url = "https://api.deepseek.com/v1"
        return self
