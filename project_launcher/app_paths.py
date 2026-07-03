"""Shared filesystem paths used by Project Launcher."""

import os


APP_TEMP_DIR_NAME = "ProjectLauncher"


def get_temp_dir() -> str:
    """Return the app-specific temp directory, creating it if needed."""
    root = os.environ.get("TEMP", os.path.expanduser("~"))
    path = os.path.join(root, APP_TEMP_DIR_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def get_log_path(filename: str) -> str:
    """Return a log file path under the app-specific temp directory."""
    return os.path.join(get_temp_dir(), filename)
