import { useEffect, useState } from "react";
import { Edit3, KeyRound, Loader2, RefreshCw, Save, Trash2 } from "lucide-react";
import type {
  ApiClient,
  LLMProfilePayload,
  LLMProfileSummary,
} from "../api/client";

type SettingsPageProps = {
  api: ApiClient;
};

type ProfileForm = {
  profile_id: string;
  name: string;
  provider: string;
  model: string;
  api_key: string;
  base_url: string;
  temperature: string;
  max_tokens: string;
  timeout_seconds: string;
  clear_api_key: boolean;
};

const emptyForm: ProfileForm = {
  profile_id: "",
  name: "",
  provider: "deepseek",
  model: "deepseek-chat",
  api_key: "",
  base_url: "",
  temperature: "0.7",
  max_tokens: "4000",
  timeout_seconds: "120",
  clear_api_key: false,
};

export function SettingsPage({ api }: SettingsPageProps) {
  const [profiles, setProfiles] = useState<LLMProfileSummary[]>([]);
  const [form, setForm] = useState<ProfileForm>(emptyForm);
  const [editingProfileId, setEditingProfileId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function loadSettings() {
    setLoading(true);
    setError(null);
    try {
      setProfiles(await api.listLLMProfiles());
    } catch (err) {
      setError(err instanceof Error ? err.message : "设置加载失败");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadSettings();
  }, []);

  function updateForm(field: keyof ProfileForm, value: string | boolean) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function startEdit(profile: LLMProfileSummary) {
    setEditingProfileId(profile.id);
    setForm({
      profile_id: profile.id,
      name: profile.name,
      provider: profile.provider,
      model: profile.model,
      api_key: "",
      base_url: profile.base_url ?? "",
      temperature: String(profile.temperature),
      max_tokens: String(profile.max_tokens),
      timeout_seconds: String(profile.timeout_seconds),
      clear_api_key: false,
    });
    setNotice(null);
    setError(null);
  }

  function resetForm() {
    setEditingProfileId(null);
    setForm(emptyForm);
  }

  async function handleSubmit() {
    if (!form.profile_id.trim() || !form.provider.trim() || !form.model.trim()) {
      setError("Profile ID、Provider、Model 必填");
      return;
    }
    const validationError = validateProfileForm(form);
    if (validationError) {
      setError(validationError);
      return;
    }

    setBusy("profile-save");
    setError(null);
    const payload = buildProfilePayload(form, editingProfileId === null);
    try {
      if (editingProfileId) {
        await api.updateLLMProfile(editingProfileId, payload);
        setNotice("模型配置已更新");
      } else {
        await api.createLLMProfile(payload);
        setNotice("模型配置已创建");
      }
      resetForm();
      await loadSettings();
    } catch (err) {
      setError(err instanceof Error ? err.message : "模型配置保存失败");
    } finally {
      setBusy(null);
    }
  }

  async function handleDelete(profileId: string) {
    setBusy(`delete-${profileId}`);
    setError(null);
    try {
      await api.deleteLLMProfile(profileId);
      if (editingProfileId === profileId) {
        resetForm();
      }
      setNotice("模型配置已删除");
      await loadSettings();
    } catch (err) {
      setError(err instanceof Error ? err.message : "模型配置删除失败");
    } finally {
      setBusy(null);
    }
  }

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="eyebrow">运行配置</p>
          <h1>设置</h1>
        </div>
        <button className="icon-button" onClick={loadSettings} title="刷新设置">
          {loading ? <Loader2 className="spin" size={18} /> : <RefreshCw size={18} />}
        </button>
      </header>
      {error ? <div className="alert error">{error}</div> : null}
      {notice ? <div className="alert success">{notice}</div> : null}
      <div className="settings-grid">
        <section className="panel">
          <div className="panel-header">
            <h2>{editingProfileId ? "编辑 LLM Profile" : "新增 LLM Profile"}</h2>
            <KeyRound size={18} />
          </div>
          <div className="profile-form">
            <label>
              Profile ID
              <input
                value={form.profile_id}
                onChange={(event) => updateForm("profile_id", event.target.value)}
                disabled={editingProfileId !== null}
                placeholder="deepseek"
              />
            </label>
            <label>
              名称
              <input
                value={form.name}
                onChange={(event) => updateForm("name", event.target.value)}
                placeholder="DeepSeek Chat"
              />
            </label>
            <label>
              Provider
              <input
                value={form.provider}
                onChange={(event) => updateForm("provider", event.target.value)}
                placeholder="deepseek / qwen / openai"
              />
            </label>
            <label>
              Model
              <input
                value={form.model}
                onChange={(event) => updateForm("model", event.target.value)}
                placeholder="deepseek-chat"
              />
            </label>
            <label className="wide-field">
              Base URL
              <input
                value={form.base_url}
                onChange={(event) => updateForm("base_url", event.target.value)}
                placeholder="https://api.deepseek.com/v1"
              />
            </label>
            <label className="wide-field">
              API Key
              <input
                value={form.api_key}
                onChange={(event) => updateForm("api_key", event.target.value)}
                type="password"
                placeholder={editingProfileId ? "留空则保留原 Key" : "可稍后再填"}
              />
            </label>
            <label>
              Temperature
              <input
                value={form.temperature}
                onChange={(event) => updateForm("temperature", event.target.value)}
                inputMode="decimal"
              />
            </label>
            <label>
              Max Tokens
              <input
                value={form.max_tokens}
                onChange={(event) => updateForm("max_tokens", event.target.value)}
                inputMode="numeric"
              />
            </label>
            <label>
              Timeout
              <input
                value={form.timeout_seconds}
                onChange={(event) => updateForm("timeout_seconds", event.target.value)}
                inputMode="numeric"
              />
            </label>
            {editingProfileId ? (
              <label className="checkbox-row wide-field">
                <input
                  checked={form.clear_api_key}
                  onChange={(event) => updateForm("clear_api_key", event.target.checked)}
                  type="checkbox"
                />
                清空已保存 API Key
              </label>
            ) : null}
            <div className="form-actions wide-field">
              <button
                className="primary-button"
                onClick={handleSubmit}
                disabled={busy === "profile-save"}
              >
                {busy === "profile-save" ? <Loader2 className="spin" size={17} /> : <Save size={17} />}
                <span>{editingProfileId ? "保存修改" : "创建配置"}</span>
              </button>
              <button className="secondary-button" onClick={resetForm}>
                重置
              </button>
            </div>
          </div>
        </section>
        <section className="panel">
          <div className="panel-header">
            <h2>LLM Profiles</h2>
            <span>{profiles.length} 个</span>
          </div>
          <div className="list-stack">
            {profiles.length === 0 ? <div className="empty-state">暂无模型配置</div> : null}
            {profiles.map((profile) => (
              <div className="config-row" key={profile.id}>
                <div>
                  <strong>{profile.name}</strong>
                  <span>{profile.provider} / {profile.model}</span>
                </div>
                <span className={profile.api_key_set ? "pill success" : "pill muted"}>
                  {profile.api_key_set ? "Key 已配置" : "无 Key"}
                </span>
                <div className="row-actions">
                  <button className="icon-button" onClick={() => startEdit(profile)} title="编辑">
                    <Edit3 size={16} />
                  </button>
                  <button
                    className="icon-button danger"
                    onClick={() => void handleDelete(profile.id)}
                    disabled={busy === `delete-${profile.id}`}
                    title="删除"
                  >
                    {busy === `delete-${profile.id}` ? <Loader2 className="spin" size={16} /> : <Trash2 size={16} />}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}

function buildProfilePayload(form: ProfileForm, includeProfileId: boolean): LLMProfilePayload {
  const payload: LLMProfilePayload = {
    ...(includeProfileId ? { profile_id: form.profile_id.trim() } : {}),
    name: form.name.trim() || form.profile_id.trim(),
    provider: form.provider.trim(),
    model: form.model.trim(),
    base_url: form.base_url.trim() || null,
    temperature: parseOptionalNumber(form.temperature),
    max_tokens: parseOptionalNumber(form.max_tokens),
    timeout_seconds: parseOptionalNumber(form.timeout_seconds),
  };

  if (form.clear_api_key) {
    payload.api_key = null;
  } else if (form.api_key.trim()) {
    payload.api_key = form.api_key.trim();
  }

  return payload;
}

function parseOptionalNumber(value: string): number | null {
  const trimmed = value.trim();
  return trimmed ? Number(trimmed) : null;
}

function validateProfileForm(form: ProfileForm): string | null {
  const temperature = parseOptionalNumber(form.temperature);
  if (temperature !== null && (!Number.isFinite(temperature) || temperature < 0 || temperature > 2)) {
    return "Temperature 需要在 0 到 2 之间";
  }

  const maxTokens = parseOptionalNumber(form.max_tokens);
  if (maxTokens !== null && (!Number.isInteger(maxTokens) || maxTokens <= 0)) {
    return "Max Tokens 必须是大于 0 的整数";
  }

  const timeoutSeconds = parseOptionalNumber(form.timeout_seconds);
  if (
    timeoutSeconds !== null &&
    (!Number.isInteger(timeoutSeconds) || timeoutSeconds <= 0)
  ) {
    return "Timeout 必须是大于 0 的整数";
  }

  return null;
}
