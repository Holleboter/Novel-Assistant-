from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import LLMSettings


Transport = Callable[[str, dict[str, str], dict[str, Any], int], dict[str, Any]]

DEFAULT_BASE_URLS = {
    "deepseek": "https://api.deepseek.com/v1",
    "qwen": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "moonshot": "https://api.moonshot.cn/v1",
    "openai": "https://api.openai.com/v1",
}


class LLMConfigurationError(ValueError):
    """Raised when required LLM settings are missing."""


class LLMRequestError(RuntimeError):
    """Raised when the LLM endpoint returns an unusable response."""


@dataclass(frozen=True)
class LLMResponse:
    content: str
    model: str | None = None
    usage: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


class LLMClient:
    def __init__(
        self,
        settings: LLMSettings | None = None,
        transport: Transport | None = None,
    ):
        self.settings = settings or LLMSettings()
        self.transport = transport or _urllib_transport

    def complete(
        self,
        user_prompt: str | None = None,
        system_prompt: str | None = None,
        messages: Sequence[Mapping[str, str]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse:
        self._validate_settings()
        payload = {
            "model": self.settings.model,
            "messages": self._build_messages(user_prompt, system_prompt, messages),
            "temperature": self.settings.temperature if temperature is None else temperature,
            "max_tokens": self.settings.max_tokens if max_tokens is None else max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }
        raw = self.transport(
            self._chat_completions_url(),
            headers,
            payload,
            self.settings.timeout_seconds,
        )
        return _parse_chat_completion(raw)

    def _validate_settings(self) -> None:
        missing = []
        if not self.settings.model:
            missing.append("LLM_MODEL")
        if not self.settings.api_key:
            missing.append("LLM_API_KEY")
        if not self._base_url():
            missing.append("LLM_BASE_URL")
        if missing:
            raise LLMConfigurationError(
                "Missing required LLM settings: " + ", ".join(missing)
            )

    def _base_url(self) -> str | None:
        return self.settings.base_url or DEFAULT_BASE_URLS.get(self.settings.provider)

    def _chat_completions_url(self) -> str:
        base_url = self._base_url()
        if base_url is None:
            raise LLMConfigurationError("Missing required LLM settings: LLM_BASE_URL")
        return base_url.rstrip("/") + "/chat/completions"

    def _build_messages(
        self,
        user_prompt: str | None,
        system_prompt: str | None,
        messages: Sequence[Mapping[str, str]] | None,
    ) -> list[dict[str, str]]:
        if messages is not None and user_prompt is not None:
            raise LLMConfigurationError("Use either messages or user_prompt, not both")
        if messages is not None:
            return [
                {"role": message["role"], "content": message["content"]}
                for message in messages
            ]
        if not user_prompt:
            raise LLMConfigurationError("user_prompt is required when messages is omitted")
        built_messages = []
        if system_prompt:
            built_messages.append({"role": "system", "content": system_prompt})
        built_messages.append({"role": "user", "content": user_prompt})
        return built_messages


def _parse_chat_completion(raw: dict[str, Any]) -> LLMResponse:
    try:
        content = raw["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMRequestError("No assistant content in LLM response") from exc
    if not isinstance(content, str) or not content.strip():
        raise LLMRequestError("No assistant content in LLM response")
    return LLMResponse(
        content=content,
        model=raw.get("model"),
        usage=raw.get("usage", {}),
        raw=raw,
    )


def _urllib_transport(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: int,
) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise LLMRequestError(f"LLM HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise LLMRequestError(f"LLM request failed: {exc.reason}") from exc
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise LLMRequestError("LLM response is not valid JSON") from exc
