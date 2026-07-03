import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "project_launcher"))

from ui.safety_messages import build_delete_confirmation_message  # noqa: E402


class SafetyMessageTests(unittest.TestCase):
    def test_delete_confirmation_states_direct_disk_delete(self):
        message = build_delete_confirmation_message("项目", "demo", "D:/projects/demo")

        self.assertIn("demo", message)
        self.assertIn("D:/projects/demo", message)
        self.assertIn("不会进入回收站", message)
        self.assertIn("请确认路径无误", message)


if __name__ == "__main__":
    unittest.main()
