"""Background project directory scanner.

Scans a base directory for immediate subdirectories (each = one project),
filtering out hidden dirs and user-configured exclusions.
"""

import os
import threading
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Set


@dataclass
class ProjectInfo:
    """Information about a single project directory."""
    name: str
    path: str
    last_modified: float = 0.0
    has_git: bool = False
    has_readme: bool = False
    hidden: bool = False


@dataclass
class ScanResult:
    """Result of a scan operation."""
    projects: List[ProjectInfo] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    skipped_count: int = 0


def scan_projects(
    base_dir: str,
    excluded_dirs: Optional[Set[str]] = None,
    callback: Optional[Callable] = None,
    sort_recent_first: bool = True,
) -> ScanResult:
    """Scan *base_dir* for project subdirectories.

    This function is designed to run in a background thread.
    Use *callback(phase, data)* to report progress to the UI thread.

    Args:
        base_dir: Absolute path to the projects root directory.
        excluded_dirs: Set of directory names to skip.
        callback: Called as callback('progress', {current, total}) and
                  callback('complete', {projects, errors, skipped}).
        sort_recent_first: Sort projects by mtime descending.

    Returns:
        ScanResult with projects, errors, and skipped count.
    """
    if excluded_dirs is None:
        excluded_dirs = set()

    result = ScanResult()

    # Validate base directory
    if not base_dir or not os.path.isdir(base_dir):
        err_msg = f"Directory does not exist or is not accessible: {base_dir}"
        result.errors.append(err_msg)
        if callback:
            callback('error', {'message': err_msg})
        return result

    # Collect entries
    try:
        entries = list(os.scandir(base_dir))
    except PermissionError:
        err_msg = f"Permission denied accessing: {base_dir}"
        result.errors.append(err_msg)
        if callback:
            callback('error', {'message': err_msg})
        return result
    except OSError as e:
        err_msg = f"Cannot read directory {base_dir}: {e}"
        result.errors.append(err_msg)
        if callback:
            callback('error', {'message': err_msg})
        return result

    total = len(entries)
    processed = 0

    for entry in entries:
        processed += 1

        # Skip files — only directories are projects
        try:
            if not entry.is_dir():
                continue
        except PermissionError:
            result.skipped_count += 1
            continue
        except OSError:
            continue

        name = entry.name

        # Skip hidden dirs (names starting with .)
        if name.startswith('.'):
            continue

        # Skip user-configured exclusions
        if name in excluded_dirs:
            continue

        # Gather metadata
        try:
            stat = entry.stat()
            last_modified = stat.st_mtime
        except OSError:
            last_modified = 0.0

        has_git = os.path.isdir(os.path.join(entry.path, '.git'))
        has_readme = any(
            os.path.isfile(os.path.join(entry.path, f'README{ext}'))
            for ext in ('', '.md', '.txt', '.rst')
        )

        project = ProjectInfo(
            name=name,
            path=entry.path,
            last_modified=last_modified,
            has_git=has_git,
            has_readme=has_readme,
            hidden=False,
        )
        result.projects.append(project)

        # Report progress
        if callback:
            callback('progress', {'current': processed, 'total': total})

    # Sort
    if sort_recent_first:
        result.projects.sort(key=lambda p: p.last_modified, reverse=True)
    else:
        result.projects.sort(key=lambda p: p.name.lower())

    if callback:
        callback('complete', {
            'projects': result.projects,
            'errors': result.errors,
            'skipped': result.skipped_count,
        })

    return result


def scan_async(
    base_dir: str,
    excluded_dirs: Optional[Set[str]],
    callback: Callable,
    sort_recent_first: bool = True,
) -> threading.Thread:
    """Launch a background scan and return the thread.

    The *callback* is called on the background thread — the caller
    must marshal UI updates to the main thread (e.g. via root.after).
    """
    thread = threading.Thread(
        target=scan_projects,
        args=(base_dir, excluded_dirs, callback, sort_recent_first),
        daemon=True,
    )
    thread.start()
    return thread
