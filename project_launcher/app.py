"""Application orchestrator — wires config, scanner, launcher, and UI."""

import ctypes
import sys
import os
from typing import Dict, Any

from config import load_config, save_config
from ui.main_window import MainWindow


class App:
    """Project Launcher application."""

    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.window: MainWindow | None = None

    def run(self):
        """Initialize and run the application."""
        # 1. Single-instance check
        if not self._acquire_single_instance():
            return  # another instance activated; exit silently

        # 2. Load config
        self.config = load_config()

        # 3. Build and show main window
        self.window = MainWindow(self.config, on_config_changed=self._on_config_changed)

        # 4. Run
        self.window.run()

    def _on_config_changed(self, config: Dict[str, Any]):
        """Handle config changes from settings dialog."""
        self.config = config

    # ── Single-instance lock ────────────────────────────────────────────────

    _mutex = None  # must hold a reference to prevent GC from releasing it

    def _acquire_single_instance(self) -> bool:
        """Acquire a named mutex to ensure only one instance runs.

        Returns True if this is the first instance; False if another
        instance already exists (which is then brought to foreground).
        """
        if sys.platform != 'win32':
            return True

        mutex_name = r"Global\ProjectLauncher_SingleInstance"
        self._mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)

        if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            # Find and activate the existing window
            hwnd = ctypes.windll.user32.FindWindowW(None, "Project Launcher")
            if hwnd:
                # SW_RESTORE = 9: restore if minimized
                ctypes.windll.user32.ShowWindow(hwnd, 9)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
            return False

        return True
