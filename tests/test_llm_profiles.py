import json

from novel_assistant.llm_profiles import LLMProfile, LLMProfileStore


def test_list_returns_empty_list_when_file_does_not_exist(tmp_path):
    store = LLMProfileStore(tmp_path / "missing.json")

    assert store.list() == []


def test_upsert_adds_profile_and_preserves_api_key_on_disk(tmp_path):
    path = tmp_path / "llm-profiles.json"
    store = LLMProfileStore(path)
    profile = LLMProfile(
        id="openai-default",
        name="OpenAI Default",
        provider="openai",
        model="gpt-4.1-mini",
        base_url="https://api.openai.com/v1",
        api_key="secret-key",
        temperature=0.4,
        max_tokens=2048,
        timeout_seconds=45,
    )

    saved = store.upsert(profile)

    assert saved == profile
    assert store.list() == [profile]
    raw_profiles = json.loads(path.read_text(encoding="utf-8"))
    assert raw_profiles[0]["api_key"] == "secret-key"
    assert raw_profiles[0]["temperature"] == 0.4
    assert raw_profiles[0]["max_tokens"] == 2048
    assert raw_profiles[0]["timeout_seconds"] == 45


def test_upsert_updates_existing_profile_by_id(tmp_path):
    store = LLMProfileStore(tmp_path / "llm-profiles.json")
    store.upsert(
        LLMProfile(
            id="default",
            name="Old Name",
            provider="openai",
            model="gpt-4.1-mini",
            base_url="https://api.openai.com/v1",
            api_key="old-key",
        )
    )

    updated = store.upsert(
        LLMProfile(
            id="default",
            name="New Name",
            provider="openai",
            model="gpt-4.1",
            base_url="https://api.openai.com/v1",
            api_key="new-key",
        )
    )

    assert updated.name == "New Name"
    assert store.list() == [updated]
    assert store.get("default") == updated


def test_delete_removes_profile_and_reports_whether_it_existed(tmp_path):
    store = LLMProfileStore(tmp_path / "llm-profiles.json")
    store.upsert(
        LLMProfile(
            id="default",
            name="Default",
            provider="openai",
            model="gpt-4.1-mini",
            base_url="https://api.openai.com/v1",
            api_key=None,
        )
    )

    assert store.delete("default") is True
    assert store.list() == []
    assert store.delete("default") is False


def test_public_list_redacts_api_key_and_reports_key_presence(tmp_path):
    store = LLMProfileStore(tmp_path / "llm-profiles.json")
    store.upsert(
        LLMProfile(
            id="with-key",
            name="With Key",
            provider="openai",
            model="gpt-4.1-mini",
            base_url="https://api.openai.com/v1",
            api_key="secret-key",
        )
    )
    store.upsert(
        LLMProfile(
            id="without-key",
            name="Without Key",
            provider="openai",
            model="gpt-4.1-mini",
            base_url="https://api.openai.com/v1",
            api_key=None,
        )
    )

    public_profiles = store.list_public()

    assert [profile.model_dump() for profile in public_profiles] == [
        {
            "id": "with-key",
            "name": "With Key",
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "base_url": "https://api.openai.com/v1",
            "api_key_set": True,
            "temperature": 0.7,
            "max_tokens": 4000,
            "timeout_seconds": 120,
        },
        {
            "id": "without-key",
            "name": "Without Key",
            "provider": "openai",
            "model": "gpt-4.1-mini",
            "base_url": "https://api.openai.com/v1",
            "api_key_set": False,
            "temperature": 0.7,
            "max_tokens": 4000,
            "timeout_seconds": 120,
        },
    ]
    assert all("api_key" not in profile.model_dump() for profile in public_profiles)
