"""IDE auto-detection and project launching.

Detects installed IDEs (VS Code, Cursor, Windsurf) and launches
a project folder in the selected IDE.
"""

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class IDEInfo:
    """Represents a detected IDE."""
    key: str             # internal identifier: "vscode", "cursor", "custom", "explorer"
    display_name: str    # human-readable label
    executable: str      # full path to .exe, empty for explorer


# ── detection ───────────────────────────────────────────────────────────────

def _find_vscode() -> List[IDEInfo]:
    """Try to locate Visual Studio Code."""
    candidates = []

    user_vscode = os.path.join(
        os.environ.get('LOCALAPPDATA', ''),
        'Programs', 'Microsoft VS Code', 'Code.exe'
    )
    if os.path.isfile(user_vscode):
        candidates.append(IDEInfo('vscode', 'Visual Studio Code', user_vscode))

    prog_vscode = os.path.join(
        os.environ.get('ProgramFiles', 'C:\\Program Files'),
        'Microsoft VS Code', 'Code.exe'
    )
    if os.path.isfile(prog_vscode) and prog_vscode not in {c.executable for c in candidates}:
        candidates.append(IDEInfo('vscode', 'Visual Studio Code', prog_vscode))

    # PATH lookup
    code_from_path = shutil.which('code')
    if code_from_path and code_from_path not in {c.executable for c in candidates}:
        candidates.append(IDEInfo('vscode', 'Visual Studio Code (PATH)', code_from_path))

    return candidates


def _find_cursor() -> List[IDEInfo]:
    """Try to locate Cursor IDE."""
    candidates = []

    user_cursor = os.path.join(
        os.environ.get('LOCALAPPDATA', ''),
        'Programs', 'Cursor', 'Cursor.exe'
    )
    if os.path.isfile(user_cursor):
        candidates.append(IDEInfo('cursor', 'Cursor', user_cursor))

    cursor_from_path = shutil.which('cursor')
    if cursor_from_path and cursor_from_path not in {c.executable for c in candidates}:
        candidates.append(IDEInfo('cursor', 'Cursor (PATH)', cursor_from_path))

    return candidates


def _find_windsurf() -> List[IDEInfo]:
    """Try to locate Windsurf IDE."""
    candidates = []

    user_windsurf = os.path.join(
        os.environ.get('LOCALAPPDATA', ''),
        'Programs', 'Windsurf', 'Windsurf.exe'
    )
    if os.path.isfile(user_windsurf):
        candidates.append(IDEInfo('windsurf', 'Windsurf', user_windsurf))

    windsurf_from_path = shutil.which('windsurf')
    if windsurf_from_path and windsurf_from_path not in {c.executable for c in candidates}:
        candidates.append(IDEInfo('windsurf', 'Windsurf (PATH)', windsurf_from_path))

    return candidates


def detect_ides() -> List[IDEInfo]:
    """Return a list of all detected IDEs.

    Always includes 文件资源管理器 as the last-resort fallback.
    """
    ides: List[IDEInfo] = []
    ides.extend(_find_vscode())
    ides.extend(_find_cursor())
    ides.extend(_find_windsurf())

    # 文件资源管理器 fallback (always available via os.startfile)
    ides.append(IDEInfo('explorer', '文件资源管理器', ''))

    return ides


def find_ide_by_key(key: str, custom_path: str = '') -> Optional[IDEInfo]:
    """Find a specific IDE by key, with optional custom path.

    Re-runs detection and returns the first match for *key*.
    If *key* is 'custom' and *custom_path* is a valid file, returns that IDE.
    Returns None if the IDE is no longer available.
    """
    if key == 'custom':
        if custom_path and os.path.isfile(custom_path):
            return IDEInfo('custom', f'Custom ({os.path.basename(custom_path)})', custom_path)
        return None

    ides = detect_ides()
    for ide in ides:
        if ide.key == key:
            return ide
    return None


# ── launching ───────────────────────────────────────────────────────────────

def launch(project_path: str, ide: IDEInfo) -> bool:
    """Open *project_path* with the given *ide*.

    Args:
        project_path: Absolute path to the project directory.
        ide: The IDEInfo to use.

    Returns:
        True if the launch succeeded, False otherwise.
    """
    # Verify the project still exists
    if not os.path.isdir(project_path):
        return False

    # Explorer fallback — open in Windows Explorer
    if ide.key == 'explorer' or not ide.executable:
        try:
            os.startfile(project_path)
            return True
        except OSError:
            return False

    # IDE launch via subprocess
    try:
        subprocess.Popen(
            [ide.executable, project_path],
            shell=False,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
        )
        return True
    except (OSError, FileNotFoundError):
        # IDE executable removed or broken — fall back to Explorer
        try:
            os.startfile(project_path)
        except OSError:
            return False
        return False  # return False so caller knows fallback occurred
