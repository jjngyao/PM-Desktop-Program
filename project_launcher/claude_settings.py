"""Safe Claude Code settings.json read/write helpers."""

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, Union

from model_profiles import (
    DEFAULT_AUTH_FIELD,
    ROLE_ENV_KEYS,
    ModelProfile,
    build_claude_settings,
)


CLAUDE_MANAGED_ENV_KEYS = {
    "ANTHROPIC_AUTH_TOKEN",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_BASE_URL",
    "ANTHROPIC_MODEL",
    *ROLE_ENV_KEYS.values(),
}


def get_default_claude_settings_path() -> Path:
    """Return the default Claude Code user settings path."""
    return Path.home() / ".claude" / "settings.json"


def _read_settings(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as settings_file:
        data = json.load(settings_file)
    if not isinstance(data, dict):
        raise ValueError("Claude Code settings.json must contain a JSON object.")
    return data


def _backup_existing(path: Path) -> None:
    if path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))


def _atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            json.dump(data, tmp_file, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
    except Exception:
        try:
            tmp_path.unlink(missing_ok=True)
        finally:
            raise


def apply_profile_to_settings_file(
    path: Union[str, Path],
    profile: ModelProfile,
) -> Dict[str, Any]:
    """Apply a model profile to Claude Code settings.json."""
    settings_path = Path(path)
    existing = _read_settings(settings_path)
    updated = build_claude_settings(existing, profile)
    _backup_existing(settings_path)
    _atomic_write_json(settings_path, updated)
    return updated


def stop_profile_in_settings_file(path: Union[str, Path]) -> Dict[str, Any]:
    """Remove Project Launcher managed Claude Code env values."""
    settings_path = Path(path)
    updated = _read_settings(settings_path)
    env = dict(updated.get("env", {}))

    for key in CLAUDE_MANAGED_ENV_KEYS:
        env.pop(key, None)

    updated["env"] = env
    _backup_existing(settings_path)
    _atomic_write_json(settings_path, updated)
    return updated
