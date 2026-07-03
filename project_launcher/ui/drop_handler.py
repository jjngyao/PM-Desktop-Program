"""Windows drag-and-drop file-copy handler for Project Launcher.

Installs a WM_DROPFILES subclass on the main window and copies
dropped files/folders into the current target directory.
"""

import ctypes
import os
import shutil
import sys
import tkinter as tk
import uuid
from tkinter import messagebox
from typing import List, Optional, TYPE_CHECKING

from constants import (
    WM_DROPFILES, DROP_POLL_INTERVAL_MS, DROP_MAX_FILES,
    DROP_PATH_BUFFER_SIZE, SUBCLASS_ID,
)
from app_paths import get_log_path

if TYPE_CHECKING:
    from ui.main_window import MainWindow


# ── Shared helper (used by both subclass-proc and fallback WNDPROC) ───────

def _extract_dropped_files(hdrop: int) -> List[str]:
    """Extract file paths from a WM_DROPFILES HDROP handle.

    Returns an empty list on any failure; never raises.
    """
    try:
        sh = ctypes.windll.shell32
        count = sh.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
        if count == 0 or count > DROP_MAX_FILES:
            return []

        files: List[str] = []
        for i in range(count):
            buf = ctypes.create_unicode_buffer(DROP_PATH_BUFFER_SIZE)
            sh.DragQueryFileW(hdrop, i, buf, DROP_PATH_BUFFER_SIZE)
            files.append(buf.value)
        return files
    except Exception:
        return []


def _remove_path(path: str) -> None:
    """Remove a file or directory if it exists."""
    if os.path.isdir(path):
        shutil.rmtree(path)
    elif os.path.exists(path):
        os.remove(path)


def _copy_path(src: str, dst: str) -> None:
    """Copy a file or directory to a destination path."""
    if os.path.isdir(src):
        shutil.copytree(src, dst)
    else:
        shutil.copy2(src, dst)


def _copy_path_preserving_existing(src: str, dst: str, overwrite: bool) -> None:
    """Copy *src* to *dst* without losing the existing destination on failure."""
    if not os.path.exists(dst):
        _copy_path(src, dst)
        return

    if not overwrite:
        raise FileExistsError(dst)

    backup = f"{dst}.project_launcher_backup_{uuid.uuid4().hex}"
    shutil.move(dst, backup)
    try:
        _copy_path(src, dst)
    except OSError:
        if os.path.exists(dst):
            _remove_path(dst)
        shutil.move(backup, dst)
        raise
    else:
        _remove_path(backup)


# ── DropHandler ─────────────────────────────────────────────────────────────

class DropHandler:
    """Manages drag-and-drop file copy via Windows WM_DROPFILES.

    Uses SetWindowSubclass (comctl32.dll) — the recommended API — with
    a fallback to direct WNDPROC replacement on ancient systems.

    IMPORTANT: the subclass procedure NEVER calls Tkinter directly.
    Instead it pushes file paths onto a thread-safe queue; a periodic
    Tkinter timer drains the queue on the main thread.
    """

    def __init__(self, main: "MainWindow"):
        self._main = main
        self._pending_drops: List[List[str]] = []
        self._drop_poll_id: Optional[str] = None
        self._subclass_proc_ref = None
        self._fallback_wndproc_ref = None
        self._fallback_original = None

    # ── Public API ────────────────────────────────────────────────────────

    def setup(self):
        """Install the drop-target subclass on the main window.

        Must be called AFTER the Tk window is fully materialized
        (after root.update_idletasks()).
        """
        if sys.platform != "win32":
            return

        try:
            hwnd = self._main.root.winfo_id()
        except tk.TclError:
            return  # window not yet realized

        # ── Set argtypes for ALL shell32 drag-drop functions ───────────
        self._configure_shell32_argtypes()

        # ── Build the subclass procedure closure ───────────────────────
        SUBCLASSPROC = ctypes.WINFUNCTYPE(
            ctypes.c_longlong,   # LRESULT
            ctypes.c_longlong,   # HWND
            ctypes.c_uint,       # UINT  msg
            ctypes.c_longlong,   # WPARAM
            ctypes.c_longlong,   # LPARAM
            ctypes.c_longlong,   # UINT_PTR  uIdSubclass
            ctypes.c_longlong,   # DWORD_PTR dwRefData
        )

        @SUBCLASSPROC
        def subclass_proc(hwnd, msg, wparam, lparam, _uid, _ref):
            try:
                if msg == WM_DROPFILES:
                    hdrop = wparam
                    if not hdrop:
                        return 0

                    files = _extract_dropped_files(hdrop)
                    ctypes.windll.shell32.DragFinish(hdrop)

                    if files:
                        self._pending_drops.append(files)
                    return 0

                return ctypes.windll.comctl32.DefSubclassProc(
                    hwnd, msg, wparam, lparam
                )
            except Exception:
                self._log_crash()
                return 0

        self._subclass_proc_ref = subclass_proc

        # ── Install the subclass ───────────────────────────────────────
        ok = self._install_subclass(hwnd, subclass_proc)
        if not ok:
            self._setup_fallback(hwnd)

        # Register to accept dropped files
        ctypes.windll.shell32.DragAcceptFiles(hwnd, True)

        # Start the polling timer
        self._poll_drop_queue()

    # ── Subclass installation ──────────────────────────────────────────────

    def _configure_shell32_argtypes(self):
        """Set argtypes for shell32 drag-drop functions.

        Without explicit argtypes, ctypes defaults pointer-sized parameters
        (HWND, HDROP) to c_int (32-bit), causing OverflowError on 64-bit
        Windows.
        """
        sh = ctypes.windll.shell32
        sh.DragAcceptFiles.argtypes = [ctypes.c_longlong, ctypes.c_int]
        sh.DragQueryFileW.argtypes = [
            ctypes.c_longlong, ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_uint,
        ]
        sh.DragQueryFileW.restype = ctypes.c_uint
        sh.DragFinish.argtypes = [ctypes.c_longlong]

    def _install_subclass(self, hwnd, subclass_proc) -> bool:
        """Try installing via SetWindowSubclass. Returns True on success."""
        comctl32 = ctypes.windll.comctl32
        comctl32.SetWindowSubclass.argtypes = [
            ctypes.c_longlong, ctypes.WINFUNCTYPE(
                ctypes.c_longlong, ctypes.c_longlong, ctypes.c_uint,
                ctypes.c_longlong, ctypes.c_longlong, ctypes.c_longlong,
                ctypes.c_longlong,
            ), ctypes.c_longlong, ctypes.c_longlong,
        ]
        comctl32.SetWindowSubclass.restype = ctypes.c_int
        comctl32.DefSubclassProc.argtypes = [
            ctypes.c_longlong, ctypes.c_uint, ctypes.c_longlong, ctypes.c_longlong,
        ]
        comctl32.DefSubclassProc.restype = ctypes.c_longlong

        return bool(comctl32.SetWindowSubclass(hwnd, subclass_proc, SUBCLASS_ID, 0))

    def _setup_fallback(self, hwnd):
        """Fallback: direct WNDPROC replacement (pre-XP or damaged comctl32)."""
        GWL_WNDPROC = -4

        WNDPROC_TYPE = ctypes.WINFUNCTYPE(
            ctypes.c_longlong, ctypes.c_longlong,
            ctypes.c_uint, ctypes.c_longlong, ctypes.c_longlong,
        )

        user32 = ctypes.windll.user32
        user32.SetWindowLongPtrW.argtypes = [
            ctypes.c_longlong, ctypes.c_int, ctypes.c_longlong,
        ]
        user32.SetWindowLongPtrW.restype = ctypes.c_longlong
        user32.CallWindowProcW.argtypes = [
            ctypes.c_longlong, ctypes.c_longlong,
            ctypes.c_uint, ctypes.c_longlong, ctypes.c_longlong,
        ]
        user32.CallWindowProcW.restype = ctypes.c_longlong

        @WNDPROC_TYPE
        def fallback_proc(hwnd, msg, wparam, lparam):
            try:
                if msg == WM_DROPFILES:
                    hdrop = wparam
                    if not hdrop:
                        return 0
                    files = _extract_dropped_files(hdrop)
                    ctypes.windll.shell32.DragFinish(hdrop)
                    if files:
                        self._pending_drops.append(files)
                    return 0
                return user32.CallWindowProcW(
                    self._fallback_original, hwnd, msg, wparam, lparam
                )
            except Exception:
                self._log_crash()
                return 0

        self._fallback_wndproc_ref = fallback_proc
        self._fallback_original = user32.GetWindowLongPtrW(hwnd, GWL_WNDPROC)

        new_addr = ctypes.cast(fallback_proc, ctypes.c_void_p).value
        user32.SetWindowLongPtrW(hwnd, GWL_WNDPROC, new_addr)

        ctypes.windll.shell32.DragAcceptFiles(hwnd, True)

    # ── Polling queue (drains on Tkinter main thread) ──────────────────────

    def _poll_drop_queue(self):
        """Periodic timer — drain _pending_drops on the main thread."""
        try:
            if self._pending_drops:
                batch = self._pending_drops.pop(0)
                self._handle_dropped_files(batch)
        except Exception:
            pass
        self._drop_poll_id = self._main.root.after(
            DROP_POLL_INTERVAL_MS, self._poll_drop_queue
        )

    # ── Drop handling ──────────────────────────────────────────────────────

    def _handle_dropped_files(self, files: List[str]):
        """Entry point for dropped files (called on main thread)."""
        try:
            self._handle_dropped_files_impl(files)
        except Exception:
            self._log_crash()
            messagebox.showerror(
                "拖放错误",
                f"处理拖放文件时出错，详情请查看:\n"
                f"{get_log_path('dnd_crash.log')}",
                parent=self._main.root,
            )

    def _handle_dropped_files_impl(self, files: List[str]):
        """Core copy logic, split into clear phases."""
        # ── Phase 1: Resolve target directory ──────────────────────────
        target_dir = self._resolve_target_dir()
        if target_dir is None:
            return

        # ── Phase 2: Check for filename conflicts ──────────────────────
        proceed, overwrite, skip_existing = self._check_conflicts(files, target_dir)
        if not proceed:
            return

        # ── Phase 3: Copy files ────────────────────────────────────────
        copied, skipped, failed = self._copy_files(files, target_dir, overwrite, skip_existing)

        # ── Phase 4: Summary & refresh ─────────────────────────────────
        self._show_summary_and_refresh(copied, skipped, failed, target_dir)

    def _resolve_target_dir(self) -> Optional[str]:
        """Determine the target directory for the drop.

        Returns the target path, or None after showing a warning.
        """
        browse = self._main.browse
        if browse.is_active:
            target_dir = browse.current_path
        else:
            target_dir = self._main.config.get("base_directory", "")

        if not target_dir:
            messagebox.showwarning(
                "无法复制",
                "请先在设置中配置基础目录，或双击项目进入目录浏览模式。",
                parent=self._main.root,
            )
            return None

        if not os.path.isdir(target_dir):
            messagebox.showwarning(
                "目录不存在",
                f"目标目录不存在:\n{target_dir}",
                parent=self._main.root,
            )
            return None

        return target_dir

    def _check_conflicts(
        self, files: List[str], target_dir: str
    ) -> tuple:
        """Check for existing files and ask the user how to handle them.

        Returns (proceed, overwrite, skip_existing).
        """
        existing_names: List[str] = []
        for f in files:
            name = os.path.basename(f)
            if os.path.exists(os.path.join(target_dir, name)):
                existing_names.append(name)

        if not existing_names:
            return True, False, False

        if len(existing_names) <= 5:
            names_str = "\n".join(f"  • {n}" for n in existing_names)
            msg = f"以下项目已存在:\n{names_str}\n\n是否覆盖？"
        else:
            msg = f"{len(existing_names)} 个项目已存在，是否覆盖？"

        answer = messagebox.askyesnocancel(
            "冲突",
            msg + '\n\n"是" = 覆盖全部  |  "否" = 跳过全部  |  "取消" = 放弃复制',
            parent=self._main.root,
        )

        if answer is None:
            return False, False, False
        elif answer:
            return True, True, False
        else:
            return True, False, True

    def _copy_files(
        self, files: List[str], target_dir: str,
        overwrite: bool, skip_existing: bool,
    ) -> tuple:
        """Copy all files/folders to target_dir.

        Returns (copied, skipped, failed) counts.
        """
        copied = 0
        skipped = 0
        failed = 0
        total = len(files)

        for i, src in enumerate(files, 1):
            name = os.path.basename(src)
            dst = os.path.join(target_dir, name)

            if skip_existing and os.path.exists(dst):
                skipped += 1
                continue

            # Update status bar
            self._main.status_label.config(text=f"正在复制... {i}/{total}")
            self._main.root.update_idletasks()

            try:
                _copy_path_preserving_existing(src, dst, overwrite)
                copied += 1
            except (OSError, shutil.SameFileError, PermissionError):
                failed += 1

        return copied, skipped, failed

    def _show_summary_and_refresh(
        self, copied: int, skipped: int, failed: int, target_dir: str,
    ):
        """Show the completion summary and refresh the view."""
        parts = [f"成功 {copied} 个"]
        if skipped:
            parts.append(f"跳过 {skipped} 个")
        if failed:
            parts.append(f"失败 {failed} 个")
        summary = "，".join(parts)

        messagebox.showinfo(
            "复制完成",
            f"{summary}\n\n目标: {target_dir}",
            parent=self._main.root,
        )

        # Restore status bar
        base = self._main.config.get("base_directory", "")
        browse = self._main.browse
        if browse.is_active:
            self._main.status_label.config(text=f"浏览: {browse.current_path}")
        elif base:
            self._main.status_label.config(
                text=f"{len(self._main.projects)} 个项目 | {base}"
            )
        else:
            self._main.status_label.config(text="就绪")

        # Refresh directory listing if browsing
        browse.refresh_current()

    # ── Helpers ────────────────────────────────────────────────────────────

    def _log_crash(self):
        """Log an exception from inside a C callback to a temp file."""
        import traceback
        try:
            with open(get_log_path("dnd_crash.log"), "a", encoding="utf-8") as f:
                f.write(traceback.format_exc() + "\n")
        except Exception:
            pass
