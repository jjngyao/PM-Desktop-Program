"""Directory browsing controller for Project Launcher.

Manages the directory-browsing view mode: entering subdirectories,
navigating back, and rendering directory entries.
"""

import os
import shutil
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Optional, TYPE_CHECKING

from constants import (
    COLOR_BG_WHITE, COLOR_BG_NAV, COLOR_BG_TOOLBAR,
    COLOR_BG_TOOLBAR_ACTIVE, COLOR_BG_HOVER,
    COLOR_TEXT_SECONDARY, COLOR_TEXT_PLACEHOLDER,
    FONT_FAMILY, FONT_SIZE_NORMAL, FONT_SIZE_EMPTY,
    FONT_SIZE_LARGE, FONT_SIZE_STATUS, MAX_DIR_ENTRIES,
)
from ui.widgets import DirectoryEntryFrame, show_error

if TYPE_CHECKING:
    from ui.main_window import MainWindow


class BrowseController:
    """Handles directory browsing within the project list area.

    Owns all browse-related state (navigation history, directory entry
    frames) and delegates shared UI operations to the parent MainWindow.
    """

    def __init__(self, main: "MainWindow"):
        self._main = main
        self._browsing_path: Optional[str] = None
        self._browse_history: List[tuple] = []   # stack of (path, view_mode)
        self._dir_frames: List[DirectoryEntryFrame] = []
        self._nav_frame: Optional[tk.Frame] = None

    # ── Public API ────────────────────────────────────────────────────────

    @property
    def is_active(self) -> bool:
        """True when the controller is showing a directory view."""
        return self._browsing_path is not None

    @property
    def current_path(self) -> Optional[str]:
        """The directory currently being browsed, or None."""
        return self._browsing_path

    def enter(self, path: str):
        """Enter directory-browse mode starting at *path*."""
        self._browse_history.append((None, "projects"))
        self._show_directory(path)

    def go_back(self):
        """Navigate back from directory view to the previous view."""
        if not self._browse_history:
            return

        prev_path, prev_mode = self._browse_history.pop()
        self._hide_browse_nav()
        self._main._clear_all_frames()
        self._main._clear_empty()

        if prev_mode == "projects":
            self._browsing_path = None
            query = self._main.search_entry.get_query()
            self._main._rebuild_list(filter_query=query)
        else:
            self._show_directory(prev_path)

    def reset(self):
        """Reset to project-list view, discarding all browse state."""
        self._hide_browse_nav()
        self._main._clear_all_frames()
        self._browsing_path = None
        self._browse_history.clear()

    def refresh_current(self):
        """Re-scan the current directory and rebuild the listing."""
        if self._browsing_path:
            self._show_directory(self._browsing_path)

    # ── Directory display ─────────────────────────────────────────────────

    def _show_directory(self, path: str):
        """Display the contents of *path* in the list area."""
        self._browsing_path = path

        self._main._clear_all_frames()
        self._show_browse_nav()

        # List entries — directories first, then files
        try:
            entries = sorted(
                os.scandir(path),
                key=lambda e: (not e.is_dir(), e.name.lower()),
            )
        except (PermissionError, OSError):
            self._main._show_empty("没有权限访问此目录")
            return

        entry_list = list(entries)
        if len(entry_list) > MAX_DIR_ENTRIES:
            entry_list = entry_list[:MAX_DIR_ENTRIES]

        if not entry_list:
            self._main._show_empty("此目录为空")
            return

        self._main._clear_empty()

        for entry in entry_list:
            try:
                is_dir = entry.is_dir()
            except OSError:
                is_dir = False

            frame = DirectoryEntryFrame(
                self._main.list_frame,
                entry.name,
                entry.path,
                is_dir=is_dir,
                on_click=self._on_entry_click,
                on_open=self._on_open_entry,
                on_open_folder=self._on_open_containing_folder,
                on_delete=self._on_delete_entry,
                on_launch_ide=self._on_launch_ide,
            )
            frame.pack(fill=tk.X)
            self._dir_frames.append(frame)

        self._main.list_canvas.yview_moveto(0)

    def _on_entry_click(self, path: str):
        """Handle clicking a directory entry — navigate into it."""
        self._browse_history.append((self._browsing_path, "directory"))
        self._show_directory(path)

    def _on_launch_ide(self, path: str):
        """Launch the bound IDE for the given directory path."""
        self._main.launch_ide_for_path(path)

    # ── Right-click actions ────────────────────────────────────────────────

    def _on_open_entry(self, path: str):
        """Open an entry: folders in Explorer, files with default program."""
        try:
            os.startfile(path)
        except OSError:
            pass

    def _on_open_containing_folder(self, path: str):
        """Open the parent folder in Explorer, selecting the file."""
        try:
            os.startfile(os.path.dirname(path))
        except OSError:
            pass

    def _on_delete_entry(self, path: str):
        """Delete a file or folder after confirmation, then refresh."""
        if not os.path.exists(path):
            show_error(
                self._main.root, "不存在",
                f"此项已不存在:\n{path}\n\n正在刷新...",
            )
            self.refresh_current()
            return

        name = os.path.basename(path)
        item_type = "文件夹" if os.path.isdir(path) else "文件"
        confirmed = messagebox.askyesno(
            "确认删除",
            f"确定要删除以下{item_type}吗？\n\n"
            f"📁 {name}\n"
            f"📂 {path}\n\n"
            f"此操作不可撤销！",
            parent=self._main.root,
        )
        if not confirmed:
            return

        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        except OSError as e:
            show_error(
                self._main.root, "删除失败",
                f"无法删除{item_type}:\n{path}\n\n{e}",
            )
            return

        self._main.status_label.config(text=f"已删除: {name}")
        self.refresh_current()

    # ── Navigation bar ────────────────────────────────────────────────────

    def _show_browse_nav(self):
        """Show the directory browse navigation bar."""
        if self._nav_frame is not None:
            self._nav_frame.destroy()

        self._nav_frame = tk.Frame(self._main.list_frame, bg=COLOR_BG_NAV, height=36)
        self._nav_frame.pack(fill=tk.X)

        back_btn = tk.Button(
            self._nav_frame,
            text="← 返回",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            bg=COLOR_BG_NAV,
            bd=0,
            cursor="hand2",
            activebackground=COLOR_BG_TOOLBAR_ACTIVE,
            command=self.go_back,
        )
        back_btn.pack(side=tk.LEFT, padx=(8, 12), pady=4)

        path_label = tk.Label(
            self._nav_frame,
            text=self._browsing_path,
            font=(FONT_FAMILY, FONT_SIZE_STATUS),
            fg=COLOR_TEXT_SECONDARY,
            bg=COLOR_BG_NAV,
            anchor="w",
        )
        path_label.pack(side=tk.LEFT, fill=tk.X, pady=4)

    def _hide_browse_nav(self):
        """Hide the directory browse navigation bar."""
        if self._nav_frame is not None:
            self._nav_frame.destroy()
            self._nav_frame = None
