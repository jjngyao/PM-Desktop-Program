"""Model provider profiles and Claude Code settings generation."""

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List


DEFAULT_AUTH_FIELD = "ANTHROPIC_AUTH_TOKEN"
DEFAULT_API_FORMAT = "Anthropic Messages (原生)"
DEFAULT_BASE_URL = ""

ROLE_ENV_KEYS = {
    "Haiku": "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "Sonnet": "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "Opus": "ANTHROPIC_DEFAULT_OPUS_MODEL",
}

MODEL_ROLES = ("Sonnet", "Opus", "Fable", "Haiku")


@dataclass
class ModelMapping:
    """Map a Claude Code role to provider-facing model names."""

    role: str
    display_name: str
    request_model: str
    supports_1m: bool = False


@dataclass
class ModelProfile:
    """A saved model provider configuration."""

    name: str
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    api_format: str = DEFAULT_API_FORMAT
    auth_field: str = DEFAULT_AUTH_FIELD
    default_model: str = ""
    user_agent: str = ""
    is_active: bool = False
    mappings: List[ModelMapping] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.mappings:
            self.mappings = empty_model_mappings()


def default_model_mappings() -> List[ModelMapping]:
    """Return the default DeepSeek model role mapping."""
    return [
        ModelMapping("Sonnet", "deepseek-v4-pro", "deepseek-v4-pro", False),
        ModelMapping("Opus", "deepseek-v4-pro[1m]", "deepseek-v4-pro", True),
        ModelMapping("Fable", "deepseek-v4-pro[1m]", "deepseek-v4-pro", True),
        ModelMapping("Haiku", "deepseek-v4-flash", "deepseek-v4-flash", False),
    ]


def empty_model_mappings() -> List[ModelMapping]:
    """Return empty role rows for a new model profile form."""
    return [ModelMapping(role, "", "", False) for role in MODEL_ROLES]


EMPTY_MODEL_ROLES = empty_model_mappings()


def mask_secret(value: str) -> str:
    """Mask a secret for display in JSON previews."""
    if not value:
        return ""
    if len(value) <= 4:
        return "***"
    return f"{value[:3]}{'*' * max(len(value) - 7, 4)}{value[-4:]}"


def _env_value(value: str, redact: bool) -> str:
    return mask_secret(value) if redact else value


def build_claude_settings(
    existing: Dict[str, Any],
    profile: ModelProfile,
    *,
    redact_secrets: bool = False,
) -> Dict[str, Any]:
    """Merge a model profile into a Claude Code settings object."""
    settings = copy.deepcopy(existing)
    env = dict(settings.get("env", {}))

    if profile.api_key:
        env[profile.auth_field or DEFAULT_AUTH_FIELD] = _env_value(
            profile.api_key, redact_secrets
        )
    if profile.base_url:
        env["ANTHROPIC_BASE_URL"] = profile.base_url
    if profile.default_model:
        env["ANTHROPIC_MODEL"] = profile.default_model

    for mapping in profile.mappings:
        env_key = ROLE_ENV_KEYS.get(mapping.role)
        if env_key and mapping.display_name:
            env[env_key] = mapping.display_name

    settings["env"] = env
    return settings


def completed_mappings(profile: ModelProfile) -> List[ModelMapping]:
    """Return mappings where both display and request model are provided."""
    return [
        mapping for mapping in profile.mappings
        if mapping.display_name.strip() and mapping.request_model.strip()
    ]


def validate_profile(profile: ModelProfile) -> List[str]:
    """Validate a profile before saving it."""
    errors: List[str] = []
    if not profile.name.strip():
        errors.append("请输入配置名称")
    if not profile.api_key.strip():
        errors.append("请输入 API Key")
    if not profile.base_url.strip():
        errors.append("请输入请求地址")
    if not profile.default_model.strip():
        errors.append("请输入默认兜底模型")

    for mapping in profile.mappings:
        has_display = bool(mapping.display_name.strip())
        has_request = bool(mapping.request_model.strip())
        if has_display != has_request:
            errors.append(f"{mapping.role} 的显示名称和实际请求模型必须同时填写")

    if not completed_mappings(profile):
        errors.append("至少填写一个模型映射")
    return errors


def profile_to_summary(profile: ModelProfile) -> Dict[str, Any]:
    """Return a non-sensitive profile summary for app config storage."""
    return {
        "name": profile.name,
        "base_url": profile.base_url,
        "api_format": profile.api_format,
        "auth_field": profile.auth_field,
        "default_model": profile.default_model,
        "user_agent": profile.user_agent,
        "is_active": profile.is_active,
        "mappings": [
            {
                "role": mapping.role,
                "display_name": mapping.display_name,
                "request_model": mapping.request_model,
                "supports_1m": mapping.supports_1m,
            }
            for mapping in completed_mappings(profile)
        ],
    }


def profile_from_summary(summary: Dict[str, Any]) -> ModelProfile:
    """Restore an editable profile from a non-sensitive app config summary."""
    mappings = [
        ModelMapping(
            str(mapping.get("role", "")),
            str(mapping.get("display_name", "")),
            str(mapping.get("request_model", "")),
            bool(mapping.get("supports_1m", False)),
        )
        for mapping in summary.get("mappings", [])
        if isinstance(mapping, dict)
    ]
    return ModelProfile(
        name=str(summary.get("name", "")),
        api_key="",
        base_url=str(summary.get("base_url", "")),
        api_format=str(summary.get("api_format", DEFAULT_API_FORMAT)),
        auth_field=str(summary.get("auth_field", DEFAULT_AUTH_FIELD)),
        default_model=str(summary.get("default_model", "")),
        user_agent=str(summary.get("user_agent", "")),
        is_active=bool(summary.get("is_active", False)),
        mappings=mappings,
    )


def set_active_profile(profiles: List[Dict[str, Any]], active_index: int) -> List[Dict[str, Any]]:
    """Mark one profile active and all other profiles inactive."""
    for index, profile in enumerate(profiles):
        profile["is_active"] = index == active_index
    return profiles


def toggle_active_profile(profiles: List[Dict[str, Any]], active_index: int) -> List[Dict[str, Any]]:
    """Toggle a profile between active and inactive states."""
    if active_index < 0 or active_index >= len(profiles):
        return profiles

    should_activate = not bool(profiles[active_index].get("is_active", False))
    for index, profile in enumerate(profiles):
        profile["is_active"] = should_activate and index == active_index
    return profiles
