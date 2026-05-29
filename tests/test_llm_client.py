import pytest

from novel_assistant.config import LLMSettings
from novel_assistant.llm_client import (
    LLMClient,
    LLMConfigurationError,
    LLMRequestError,
)


def test_llm_client_posts_openai_compatible_chat_payload():
    calls = []

    def fake_transport(url, headers, payload, timeout_seconds):
        calls.append(
            {
                "url": url,
                "headers": headers,
                "payload": payload,
                "timeout_seconds": timeout_seconds,
            }
        )
        return {
            "model": "deepseek-chat",
            "choices": [{"message": {"content": "收到，开始写第一章。"}}],
            "usage": {"total_tokens": 32},
        }

    client = LLMClient(
        settings=LLMSettings(
            provider="deepseek",
            model="deepseek-chat",
            api_key="test-key",
            base_url="https://api.deepseek.com",
            temperature=0.5,
            max_tokens=2048,
            timeout_seconds=30,
        ),
        transport=fake_transport,
    )

    response = client.complete(
        user_prompt="写第一章",
        system_prompt="你是小说助手。",
    )

    assert response.content == "收到，开始写第一章。"
    assert response.model == "deepseek-chat"
    assert response.usage == {"total_tokens": 32}
    assert calls[0]["url"] == "https://api.deepseek.com/v1/chat/completions"
    assert calls[0]["headers"]["Authorization"] == "Bearer test-key"
    assert calls[0]["payload"]["model"] == "deepseek-chat"
    assert calls[0]["payload"]["messages"] == [
        {"role": "system", "content": "你是小说助手。"},
        {"role": "user", "content": "写第一章"},
    ]
    assert calls[0]["payload"]["temperature"] == 0.5
    assert calls[0]["payload"]["max_tokens"] == 2048
    assert calls[0]["timeout_seconds"] == 30


def test_llm_client_accepts_message_list():
    def fake_transport(url, headers, payload, timeout_seconds):
        return {"choices": [{"message": {"content": "继续。"}}]}

    client = LLMClient(
        settings=LLMSettings(
            model="test-model",
            api_key="test-key",
            base_url="https://example.com/v1",
        ),
        transport=fake_transport,
    )

    response = client.complete(
        messages=[
            {"role": "system", "content": "保持悬疑。"},
            {"role": "user", "content": "续写。"},
        ],
    )

    assert response.content == "继续。"


def test_llm_client_requires_model_api_key_and_base_url():
    client = LLMClient(
        settings=LLMSettings(
            provider="openai_compatible",
            model="",
            api_key=None,
            base_url=None,
        )
    )

    with pytest.raises(LLMConfigurationError, match="LLM_MODEL"):
        client.complete(user_prompt="测试")


def test_llm_client_raises_request_error_for_bad_response_shape():
    def fake_transport(url, headers, payload, timeout_seconds):
        return {"choices": []}

    client = LLMClient(
        settings=LLMSettings(
            model="test-model",
            api_key="test-key",
            base_url="https://example.com/v1",
        ),
        transport=fake_transport,
    )

    with pytest.raises(LLMRequestError, match="No assistant content"):
        client.complete(user_prompt="测试")
