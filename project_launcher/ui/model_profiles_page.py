"""First-level model profile management page."""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, List, Dict, Any

from constants import FONT_FAMILY, FONT_SIZE_LARGE, FONT_SIZE_NORMAL, FONT_SIZE_STATUS


ProfileList = List[Dict[str, Any]]
ProfileCallback = Callable[[int, tk.Toplevel], ProfileList]
AddCallback = Callable[[tk.Toplevel], ProfileList]


class ModelProfilesPage:
    """Top-level page for listing, adding, editing, and deleting model profiles."""

    def __init__(
        self,
        parent: tk.Tk,
        profiles: ProfileList,
        *,
        on_add: AddCallback,
        on_edit: ProfileCallback,
        on_delete: ProfileCallback,
    ):
        self._parent = parent
        self._profiles = list(profiles)
        self._on_add = on_add
        self._on_edit = on_edit
        self._on_delete = on_delete

        self._dialog = tk.Toplevel(parent)
        self._dialog.title("模型配置")
        self._dialog.geometry("520x420")
        self._dialog.minsize(440, 320)
        self._dialog.transient(parent)
        self._dialog.grab_set()

        self._build()
        self._render_profiles()
        self._dialog.wait_window()

    def _build(self) -> None:
        outer = ttk.Frame(self._dialog, padding=18)
        outer.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(outer)
        header.pack(fill=tk.X, pady=(0, 14))

        ttk.Label(
            header,
            text="模型配置",
            font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold"),
        ).pack(side=tk.LEFT)

        add_button = tk.Button(
            header,
            text="+",
            width=3,
            height=1,
            relief=tk.FLAT,
            bg="#f2f5f8",
            activebackground="#e5edf5",
            fg="#111827",
            font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold"),
            command=self._add_profile,
        )
        add_button.pack(side=tk.RIGHT)

        self._list_frame = ttk.Frame(outer)
        self._list_frame.pack(fill=tk.BOTH, expand=True)

    def _render_profiles(self) -> None:
        for child in self._list_frame.winfo_children():
            child.destroy()

        if not self._profiles:
            ttk.Label(
                self._list_frame,
                text="暂无模型配置",
                font=(FONT_FAMILY, FONT_SIZE_NORMAL),
                foreground="#6b7280",
            ).pack(anchor=tk.W, pady=(8, 2))
            ttk.Label(
                self._list_frame,
                text="点击右上角 + 新建模型供应商配置",
                font=(FONT_FAMILY, FONT_SIZE_STATUS),
                foreground="#9ca3af",
            ).pack(anchor=tk.W)
            return

        for index, profile in enumerate(self._profiles):
            self._add_profile_row(index, profile)

    def _add_profile_row(self, index: int, profile: Dict[str, Any]) -> None:
        row = ttk.Frame(self._list_frame, padding=(0, 8))
        row.pack(fill=tk.X)

        ttk.Label(
            row,
            text=str(profile.get("name", "未命名配置")),
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(row, text="✎", width=3, command=lambda: self._edit_profile(index)).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(row, text="🗑", width=3, command=lambda: self._delete_profile(index)).pack(
            side=tk.LEFT, padx=(0, 10)
        )

        color = "#1a7f37" if profile.get("is_active") else "#d1242f"
        tk.Label(
            row,
            text="●",
            fg=color,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
        ).pack(side=tk.RIGHT)

        ttk.Separator(self._list_frame, orient="horizontal").pack(fill=tk.X)

    def _add_profile(self) -> None:
        self._profiles = list(self._on_add(self._dialog))
        self._render_profiles()

    def _edit_profile(self, index: int) -> None:
        self._profiles = list(self._on_edit(index, self._dialog))
        self._render_profiles()

    def _delete_profile(self, index: int) -> None:
        name = str(self._profiles[index].get("name", "该模型配置"))
        confirmed = messagebox.askyesno(
            "删除模型配置",
            f"确定要删除“{name}”吗？此操作不会删除 Claude Code settings.json。",
            parent=self._dialog,
        )
        if not confirmed:
            return
        self._profiles = list(self._on_delete(index, self._dialog))
        self._render_profiles()
