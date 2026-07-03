import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "project_launcher"))

from ui.drop_handler import _copy_path_preserving_existing  # noqa: E402


class DropHandlerSafetyTests(unittest.TestCase):
    def test_failed_directory_overwrite_restores_existing_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing_source = root / "missing-source"
            target = root / "target"
            target.mkdir()
            marker = target / "keep.txt"
            marker.write_text("original", encoding="utf-8")

            with self.assertRaises(OSError):
                _copy_path_preserving_existing(str(missing_source), str(target), overwrite=True)

            self.assertTrue(target.is_dir())
            self.assertEqual(marker.read_text(encoding="utf-8"), "original")
            self.assertEqual(
                list(root.glob("target.project_launcher_backup_*")),
                [],
            )


if __name__ == "__main__":
    unittest.main()
