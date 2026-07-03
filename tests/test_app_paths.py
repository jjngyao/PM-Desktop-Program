import os
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "project_launcher"))

from app_paths import get_log_path  # noqa: E402


class AppPathTests(unittest.TestCase):
    def test_log_path_uses_project_launcher_temp_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_temp = os.environ.get("TEMP")
            os.environ["TEMP"] = tmp
            try:
                log_path = Path(get_log_path("error.log"))
            finally:
                if old_temp is None:
                    os.environ.pop("TEMP", None)
                else:
                    os.environ["TEMP"] = old_temp

            self.assertEqual(log_path.parent, Path(tmp) / "ProjectLauncher")
            self.assertTrue(log_path.parent.exists())
            self.assertEqual(log_path.name, "error.log")


if __name__ == "__main__":
    unittest.main()
