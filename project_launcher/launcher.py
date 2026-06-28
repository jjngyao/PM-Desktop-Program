"""IDE auto-detection and project launching.

Detects installed IDEs (VS Code, Cursor, Windsurf) and launches
a project folder in the selected IDE.
"""

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class IDEInfo:
    """Represents a detected IDE."""
    key: str             # internal identifier: "vscode", "cursor", "custom", "explorer"
    display_name: str    # human-readable label
    executable: str      # full path to .exe, empty for explorer


# ── Generic IDE finder ──────────────────────────────────────────────────────

def _find_ide_by_paths(
    ide_key: str,
    display_name: str,
    local_subpath: str,
    exe_name: str,
    path_command: str,
    *,
    check_program_files: bool = False,
    program_files_subpath: str = "",
) -> List[IDEInfo]:
    """Generic IDE detection helper.

    Scans known installation locations and PATH for an IDE executable.
    Deduplicates results by executable path.

    Args:
        ide_key: Internal key (e.g. "vscode", "cursor", "windsurf").
        display_name: Human-readable label.
        local_subpath: Sub-path under %LOCALAPPDATA%\\Programs.
        exe_name: Executable filename (e.g. "Code.exe").
        path_command: Command name for shutil.which lookup.
        check_program_files: Also check %ProgramFiles%.
        program_files_subpath: Sub-path under %ProgramFiles% (used when
            *check_program_files* is True).
    """
    candidates: List[IDEInfo] = []
    seen: set = set()

    def _add(path: str, label: str) -> None:
        norm = os.path.normcase(path)
        if norm not in seen:
            seen.add(norm)
            candidates.append(IDEInfo(ide_key, label, path))

    # %LOCALAPPDATA%\\Programs\\...
    user_path = os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "Programs", local_subpath, exe_name,
    )
    if os.path.isfile(user_path):
        _add(user_path, display_name)

    # %ProgramFiles%\\... (optional — VS Code has a system-wide installer)
    if check_program_files:
        prog_path = os.path.join(
            os.environ.get("ProgramFiles", "C:\\Program Files"),
            program_files_subpath or local_subpath, exe_name,
        )
        if os.path.isfile(prog_path):
            _add(prog_path, display_name)

    # PATH lookup
    from_path = shutil.which(path_command)
    if from_path:
        _add(from_path, f"{display_name} (PATH)")

    return candidates


# ── Individual IDE detection ────────────────────────────────────────────────

def _find_vscode() -> List[IDEInfo]:
    return _find_ide_by_paths(
        "vscode", "Visual Studio Code",
        local_subpath="Microsoft VS Code",
        exe_name="Code.exe",
        path_command="code",
        check_program_files=True,
        program_files_subpath="Microsoft VS Code",
    )


def _find_cursor() -> List[IDEInfo]:
    return _find_ide_by_paths(
        "cursor", "Cursor",
        local_subpath="Cursor",
        exe_name="Cursor.exe",
        path_command="cursor",
    )


def _find_windsurf() -> List[IDEInfo]:
    return _find_ide_by_paths(
        "windsurf", "Windsurf",
        local_subpath="Windsurf",
        exe_name="Windsurf.exe",
        path_command="windsurf",
    )


# ── Public detection API ────────────────────────────────────────────────────

def detect_ides() -> List[IDEInfo]:
    """Return a list of all detected IDEs.

    Always includes 文件资源管理器 as the last-resort fallback.
    """
    ides: List[IDEInfo] = []
    ides.extend(_find_vscode())
    ides.extend(_find_cursor())
    ides.extend(_find_windsurf())

    # 文件资源管理器 fallback (always available via os.startfile)
    ides.append(IDEInfo("explorer", "文件资源管理器", ""))

    return ides


def find_ide_by_key(key: str, custom_path: str = "") -> Optional[IDEInfo]:
    """Find a specific IDE by key, with optional custom path.

    Re-runs detection and returns the first match for *key*.
    If *key* is 'custom' and *custom_path* is a valid file, returns that IDE.
    Returns None if the IDE is no longer available.
    """
    if key == "custom":
        if custom_path and os.path.isfile(custom_path):
            return IDEInfo("custom", f"Custom ({os.path.basename(custom_path)})", custom_path)
        return None

    ides = detect_ides()
    for ide in ides:
        if ide.key == key:
            return ide
    return None


# ── Launching ───────────────────────────────────────────────────────────────

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
    if ide.key == "explorer" or not ide.executable:
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
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        return True
    except (OSError, FileNotFoundError):
        # IDE executable removed or broken — fall back to Explorer
        try:
            os.startfile(project_path)
        except OSError:
            return False
        return False  # return False so caller knows fallback occurred
