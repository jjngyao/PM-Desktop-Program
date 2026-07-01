"""New folder creation dialog for Project Launcher."""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from constants import FONT_FAMILY, FONT_SIZE_NORMAL
from ui.widgets import show_error


class NewFolderDialog:
    """Modal dialog for creating a new folder at an arbitrary path.

    Usage:
        NewFolderDialog(parent, on_created=callback)
    """

    def __init__(self, parent: tk.Tk, on_created=None, default_path: str = ""):
        self._parent = parent
        self._on_created = on_created
        self._default_path = default_path

        self._dialog = tk.Toplevel(parent)
        self._dialog.title("新建文件夹")
        self._dialog.resizable(False, False)
        self._dialog.transient(parent)
        self._dialog.grab_set()

        self._center_on_parent()
        self._build()
        self._dialog.wait_window()

    # ── Layout ─────────────────────────────────────────────────────────────

    def _center_on_parent(self):
        """Position the dialog centered on its parent window."""
        self._dialog.update_idletasks()
        pw = self._parent.winfo_width()
        ph = self._parent.winfo_height()
        px = self._parent.winfo_x()
        py = self._parent.winfo_y()
        dw, dh = 520, 120
        x = px + (pw - dw) // 2
        y = py + (ph - dh) // 2
        self._dialog.geometry(f"{dw}x{dh}+{x}+{y}")

    def _build(self):
        """Build the dialog layout."""
        frame = ttk.Frame(self._dialog, padding=(16, 16, 16, 8))
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frame, text="请输入要创建的文件夹完整路径:",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
        ).pack(anchor="w")

        entry_frame = ttk.Frame(frame)
        entry_frame.pack(fill=tk.X, pady=(8, 12))

        self._path_var = tk.StringVar(value=self._default_path)
        path_entry = ttk.Entry(
            entry_frame, textvariable=self._path_var,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
        )
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        browse_btn = ttk.Button(
            entry_frame, text="浏览...", command=self._browse
        )
        browse_btn.pack(side=tk.LEFT, padx=(8, 0))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="确定", command=self._on_ok).pack(
            side=tk.RIGHT, padx=(8, 0),
        )
        ttk.Button(btn_frame, text="取消", command=self._dialog.destroy).pack(
            side=tk.RIGHT,
        )

        path_entry.focus_set()

    # ── Actions ────────────────────────────────────────────────────────────

    def _browse(self):
        """Open a folder browser to select the parent directory."""
        result = filedialog.askdirectory(
            parent=self._dialog, title="选择父文件夹",
        )
        if result:
            self._path_var.set(result + "/")
        # Re-focus the path entry (find it and focus)
        for child in self._dialog.winfo_children():
            if isinstance(child, ttk.Frame):
                for c in child.winfo_children():
                    if isinstance(c, ttk.Frame):
                        for w in c.winfo_children():
                            if isinstance(w, ttk.Entry):
                                w.focus_set()

    def _on_ok(self):
        """Validate and create the folder."""
        path = self._path_var.get().strip()
        if not path:
            return

        try:
            os.makedirs(path, exist_ok=True)
        except OSError as e:
            show_error(self._dialog, "创建失败", f"无法创建文件夹:\n{e}")
            return

        self._dialog.destroy()
        messagebox.showinfo(
            "成功", f"文件夹已创建:\n{path}", parent=self._parent,
        )

        if self._on_created:
            self._on_created(path)
