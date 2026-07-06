import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "project_launcher"))

from claude_settings import apply_profile_to_settings_file, stop_profile_in_settings_file  # noqa: E402
from model_profiles import ModelMapping, ModelProfile  # noqa: E402


class ClaudeSettingsTests(unittest.TestCase):
    def test_apply_profile_preserves_unknown_fields_and_creates_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            original = {
                "autoUpdatesChannel": "stable",
                "env": {"KEEP_ME": "yes"},
                "permissions": {"allow": ["Bash"]},
            }
            settings_path.write_text(json.dumps(original), encoding="utf-8")
            profile = ModelProfile(
                name="DeepSeek",
                api_key="sk-secret-token",
                base_url="https://api.deepseek.com/anthropic",
                default_model="deepseek-v4-pro[1m]",
                mappings=[
                    ModelMapping("Sonnet", "deepseek-v4-pro", "deepseek-v4-pro"),
                    ModelMapping("Haiku", "deepseek-v4-flash", "deepseek-v4-flash"),
                ],
            )

            updated = apply_profile_to_settings_file(settings_path, profile)

            self.assertEqual(updated["autoUpdatesChannel"], "stable")
            self.assertEqual(updated["permissions"], {"allow": ["Bash"]})
            self.assertEqual(updated["env"]["KEEP_ME"], "yes")
            self.assertEqual(updated["env"]["ANTHROPIC_AUTH_TOKEN"], "sk-secret-token")
            self.assertEqual(updated["env"]["ANTHROPIC_BASE_URL"], "https://api.deepseek.com/anthropic")
            self.assertEqual(updated["env"]["ANTHROPIC_MODEL"], "deepseek-v4-pro[1m]")
            self.assertEqual(updated["env"]["ANTHROPIC_DEFAULT_SONNET_MODEL"], "deepseek-v4-pro")
            self.assertEqual(updated["env"]["ANTHROPIC_DEFAULT_HAIKU_MODEL"], "deepseek-v4-flash")
            self.assertEqual(json.loads(settings_path.read_text(encoding="utf-8")), updated)
            self.assertEqual(
                json.loads(settings_path.with_suffix(".json.bak").read_text(encoding="utf-8")),
                original,
            )

    def test_stop_profile_removes_managed_env_values_and_preserves_unknown_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            original = {
                "env": {
                    "KEEP_ME": "yes",
                    "ANTHROPIC_AUTH_TOKEN": "sk-secret-token",
                    "ANTHROPIC_BASE_URL": "https://api.deepseek.com/anthropic",
                    "ANTHROPIC_MODEL": "deepseek-v4-pro[1m]",
                    "ANTHROPIC_DEFAULT_SONNET_MODEL": "deepseek-v4-pro",
                    "ANTHROPIC_DEFAULT_OPUS_MODEL": "deepseek-v4-pro[1m]",
                }
            }
            settings_path.write_text(json.dumps(original), encoding="utf-8")

            updated = stop_profile_in_settings_file(settings_path)

            self.assertEqual(updated, {"env": {"KEEP_ME": "yes"}})
            self.assertEqual(json.loads(settings_path.read_text(encoding="utf-8")), updated)
            self.assertEqual(
                json.loads(settings_path.with_suffix(".json.bak").read_text(encoding="utf-8")),
                original,
            )


if __name__ == "__main__":
    unittest.main()
