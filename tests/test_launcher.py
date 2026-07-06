import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "project_launcher"))

import launcher  # noqa: E402
from launcher import IDEInfo  # noqa: E402


class LauncherTests(unittest.TestCase):
    def test_launch_uses_cmd_for_windows_command_wrappers(self):
        with tempfile.TemporaryDirectory() as tmp:
            ide = IDEInfo("vscode", "Visual Studio Code (PATH)", r"C:\Tools\code.cmd")

            with patch("launcher.subprocess.Popen") as popen:
                self.assertTrue(launcher.launch(tmp, ide))

            args, kwargs = popen.call_args
            self.assertEqual(args[0], ["cmd.exe", "/d", "/c", ide.executable, "--new-window", tmp])
            self.assertFalse(kwargs["shell"])

    def test_launch_reports_success_when_explorer_fallback_opens_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            ide = IDEInfo("vscode", "Visual Studio Code", r"C:\Missing\Code.exe")

            with patch("launcher.subprocess.Popen", side_effect=FileNotFoundError):
                with patch("launcher.os.startfile", create=True) as startfile:
                    self.assertTrue(launcher.launch(tmp, ide))

            startfile.assert_called_once_with(tmp)

    def test_launch_opens_vscode_family_ides_in_new_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            ide = IDEInfo("custom", "Custom", r"D:\Apps\Microsoft VS Code\Code.exe")

            with patch("launcher.subprocess.Popen") as popen:
                self.assertTrue(launcher.launch(tmp, ide))

            args, _ = popen.call_args
            self.assertEqual(args[0], [ide.executable, "--new-window", tmp])


if __name__ == "__main__":
    unittest.main()
