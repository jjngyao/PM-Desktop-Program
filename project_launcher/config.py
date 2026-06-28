"""Configuration persistence for Project Launcher.

Stores settings as JSON. Prefers portable mode (config.json next to EXE),
falls back to %APPDATA%/ProjectLauncher/config.json.
"""

import copy
import json
import os
import shutil
import sys
import tempfile
from typing import Any, Dict

from constants import DEFAULT_EXCLUDED_DIRS

# ── defaults ────────────────────────────────────────────────────────────────

DEFAULT_CONFIG: Dict[str, Any] = {
    "base_directory": "",
    "selected_ide": "auto",
    "ide_custom_path": "",
    "excluded_dirs": list(DEFAULT_EXCLUDED_DIRS),
    "window_geometry": "900x600",
    "sort_recent_first": True,
    "last_opened": {},
}

# ── path helpers ────────────────────────────────────────────────────────────

def _get_portable_path() -> str:
    """Config path next to the EXE (or script)."""
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, 'config.json')


def _get_appdata_path() -> str:
    """Config path in user AppData."""
    appdata = os.environ.get('APPDATA', os.path.expanduser('~'))
    return os.path.join(appdata, 'ProjectLauncher', 'config.json')


def get_config_path() -> str:
    """Return the active config file path.

    If a portable config exists, use it; otherwise use AppData.
    """
    portable = _get_portable_path()
    if os.path.exists(portable):
        return portable
    return _get_appdata_path()


# ── load / save ─────────────────────────────────────────────────────────────

def _backfill(config: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure all default keys exist in the loaded config."""
    for key, default in DEFAULT_CONFIG.items():
        if key not in config:
            config[key] = copy.deepcopy(default)
        elif isinstance(default, dict) and isinstance(config[key], dict):
            for dk, dv in default.items():
                if dk not in config[key]:
                    config[key][dk] = dv
    return config


def load_config() -> Dict[str, Any]:
    """Load config from disk. Returns defaults on any failure."""
    path = get_config_path()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except (json.JSONDecodeError, OSError):
        # Back up the corrupted file so the user can inspect it
        if os.path.exists(path):
            bak = path + '.bak'
            try:
                shutil.copy2(path, bak)
            except OSError:
                pass
        # Return a deep copy of defaults to avoid shared mutation
        return copy.deepcopy(DEFAULT_CONFIG)
    return _backfill(config)


def save_config(config: Dict[str, Any]) -> None:
    """Atomically save config to disk."""
    path = get_config_path()
    config_dir = os.path.dirname(path)
    os.makedirs(config_dir, exist_ok=True)

    try:
        tmp_fd, tmp_path = tempfile.mkstemp(dir=config_dir, suffix='.tmp')
        with os.fdopen(tmp_fd, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)  # atomic on same filesystem
    except OSError:
        # If atomic replace fails (e.g. cross-volume), fall back to direct write
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except OSError:
            pass  # silently fail — not worth crashing over
