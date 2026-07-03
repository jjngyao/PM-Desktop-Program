import json
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "project_launcher"))

import config  # noqa: E402


class ConfigSafetyTests(unittest.TestCase):
    def test_save_config_creates_backup_before_replacing_existing_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "config.json"
            original = {"base_directory": "D:/old", "last_opened": {"old": "value"}}
            config_path.write_text(json.dumps(original), encoding="utf-8")

            old_get_config_path = config.get_config_path
            config.get_config_path = lambda: str(config_path)
            try:
                config.save_config({"base_directory": "D:/new"})
            finally:
                config.get_config_path = old_get_config_path

            backup = config_path.with_suffix(config_path.suffix + ".bak")
            self.assertTrue(backup.exists())
            self.assertEqual(json.loads(backup.read_text(encoding="utf-8")), original)
            self.assertEqual(
                json.loads(config_path.read_text(encoding="utf-8")),
                {"base_directory": "D:/new"},
            )


if __name__ == "__main__":
    unittest.main()
