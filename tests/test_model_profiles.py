import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "project_launcher"))

from model_profiles import (  # noqa: E402
    EMPTY_MODEL_ROLES,
    ModelMapping,
    ModelProfile,
    build_claude_settings,
    mask_secret,
    profile_from_summary,
    profile_to_summary,
    set_active_profile,
    toggle_active_profile,
    validate_profile,
)


class ModelProfileTests(unittest.TestCase):
    def test_build_claude_settings_preserves_existing_config_and_writes_env(self):
        profile = ModelProfile(
            name="DeepSeek",
            api_key="sk-secret-token",
            base_url="https://api.deepseek.com/anthropic",
            auth_field="ANTHROPIC_AUTH_TOKEN",
            default_model="deepseek-v4-pro[1m]",
            mappings=[
                ModelMapping("Haiku", "deepseek-v4-flash", "deepseek-v4-flash", False),
                ModelMapping("Sonnet", "deepseek-v4-pro", "deepseek-v4-pro", False),
                ModelMapping("Opus", "deepseek-v4-pro[1m]", "deepseek-v4-pro", True),
                ModelMapping("Fable", "deepseek-v4-pro[1m]", "deepseek-v4-pro", True),
            ],
        )
        existing = {"autoUpdatesChannel": "stable", "permissions": {"allow": ["Bash"]}}

        settings = build_claude_settings(existing, profile)

        self.assertEqual(settings["autoUpdatesChannel"], "stable")
        self.assertEqual(settings["permissions"], {"allow": ["Bash"]})
        self.assertEqual(settings["env"]["ANTHROPIC_AUTH_TOKEN"], "sk-secret-token")
        self.assertEqual(settings["env"]["ANTHROPIC_BASE_URL"], "https://api.deepseek.com/anthropic")
        self.assertEqual(settings["env"]["ANTHROPIC_DEFAULT_HAIKU_MODEL"], "deepseek-v4-flash")
        self.assertEqual(settings["env"]["ANTHROPIC_DEFAULT_SONNET_MODEL"], "deepseek-v4-pro")
        self.assertEqual(settings["env"]["ANTHROPIC_DEFAULT_OPUS_MODEL"], "deepseek-v4-pro[1m]")
        self.assertEqual(settings["env"]["ANTHROPIC_MODEL"], "deepseek-v4-pro[1m]")

    def test_build_claude_settings_preview_masks_api_key(self):
        profile = ModelProfile(
            name="DeepSeek",
            api_key="sk-1234567890abcdef",
            base_url="https://api.deepseek.com/anthropic",
        )

        settings = build_claude_settings({}, profile, redact_secrets=True)

        self.assertEqual(settings["env"]["ANTHROPIC_AUTH_TOKEN"], "sk-************cdef")
        self.assertNotIn("sk-1234567890abcdef", str(settings))

    def test_empty_profile_does_not_write_default_env_values(self):
        profile = ModelProfile(name="", api_key="", base_url="", default_model="")

        settings = build_claude_settings({"autoUpdatesChannel": "latest"}, profile)

        self.assertEqual(settings, {"autoUpdatesChannel": "latest", "env": {}})

    def test_empty_model_roles_have_no_default_model_values(self):
        roles = EMPTY_MODEL_ROLES

        self.assertEqual([mapping.role for mapping in roles], ["Sonnet", "Opus", "Fable", "Haiku"])
        self.assertTrue(all(mapping.display_name == "" for mapping in roles))
        self.assertTrue(all(mapping.request_model == "" for mapping in roles))
        self.assertTrue(all(mapping.supports_1m is False for mapping in roles))

    def test_profile_summary_persists_api_key_and_defaults_inactive(self):
        profile = ModelProfile(
            name="DeepSeek",
            api_key="sk-secret-token",
            base_url="https://api.deepseek.com/anthropic",
            default_model="deepseek-v4-pro[1m]",
            mappings=[ModelMapping("Sonnet", "deepseek-v4-pro", "deepseek-v4-pro")],
        )

        summary = profile_to_summary(profile)

        self.assertEqual(summary["name"], "DeepSeek")
        self.assertFalse(summary["is_active"])
        self.assertEqual(summary["api_key"], "sk-secret-token")

    def test_profile_summary_can_restore_editable_profile_with_api_key(self):
        profile = ModelProfile(
            name="DeepSeek",
            api_key="sk-secret-token",
            base_url="https://api.deepseek.com/anthropic",
            default_model="deepseek-v4-pro[1m]",
            user_agent="Mozilla/5.0",
            is_active=True,
            mappings=[
                ModelMapping("Sonnet", "deepseek-v4-pro", "deepseek-v4-pro", False),
                ModelMapping("Opus", "deepseek-v4-pro[1m]", "deepseek-v4-pro", True),
            ],
        )

        restored = profile_from_summary(profile_to_summary(profile))

        self.assertEqual(restored.name, "DeepSeek")
        self.assertEqual(restored.api_key, "sk-secret-token")
        self.assertEqual(restored.base_url, "https://api.deepseek.com/anthropic")
        self.assertEqual(restored.default_model, "deepseek-v4-pro[1m]")
        self.assertEqual(restored.user_agent, "Mozilla/5.0")
        self.assertTrue(restored.is_active)
        self.assertEqual([mapping.role for mapping in restored.mappings], ["Sonnet", "Opus"])
        self.assertTrue(restored.mappings[1].supports_1m)

    def test_set_active_profile_marks_only_selected_profile_active(self):
        profiles = [
            {"name": "DeepSeek", "is_active": True},
            {"name": "LongCat", "is_active": False},
            {"name": "Moonshot", "is_active": False},
        ]

        updated = set_active_profile(profiles, 1)

        self.assertIs(updated, profiles)
        self.assertEqual(
            [profile["is_active"] for profile in updated],
            [False, True, False],
        )

    def test_toggle_active_profile_stops_selected_active_profile(self):
        profiles = [
            {"name": "DeepSeek", "is_active": True},
            {"name": "LongCat", "is_active": False},
        ]

        updated = toggle_active_profile(profiles, 0)

        self.assertIs(updated, profiles)
        self.assertEqual([profile["is_active"] for profile in updated], [False, False])

    def test_toggle_active_profile_starts_selected_inactive_profile(self):
        profiles = [
            {"name": "DeepSeek", "is_active": True},
            {"name": "LongCat", "is_active": False},
        ]

        updated = toggle_active_profile(profiles, 1)

        self.assertEqual([profile["is_active"] for profile in updated], [False, True])

    def test_validate_profile_rejects_missing_required_fields_and_partial_mapping(self):
        profile = ModelProfile(
            name="",
            api_key="",
            base_url="",
            default_model="",
            mappings=[ModelMapping("Sonnet", "deepseek-v4-pro", "")],
        )

        errors = validate_profile(profile)

        self.assertIn("请输入配置名称", errors)
        self.assertIn("请输入 API Key", errors)
        self.assertIn("请输入请求地址", errors)
        self.assertIn("请输入默认兜底模型", errors)
        self.assertIn("Sonnet 的显示名称和实际请求模型必须同时填写", errors)

    def test_validate_profile_requires_at_least_one_complete_mapping(self):
        profile = ModelProfile(
            name="DeepSeek",
            api_key="sk-secret-token",
            base_url="https://api.deepseek.com/anthropic",
            default_model="deepseek-v4-pro[1m]",
            mappings=[ModelMapping("Sonnet", "", "")],
        )

        self.assertIn("至少填写一个模型映射", validate_profile(profile))

    def test_mask_secret_handles_short_values(self):
        self.assertEqual(mask_secret("abc"), "***")
        self.assertEqual(mask_secret(""), "")


if __name__ == "__main__":
    unittest.main()
