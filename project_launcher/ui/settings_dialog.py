"""Settings dialog for Project Launcher."""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Callable, Dict, Any, List

from launcher import detect_ides, IDEInfo
from constants import FONT_FAMILY, FONT_SIZE_LARGE, FONT_SIZE_NORMAL, FONT_SIZE_STATUS


class SettingsDialog:
    """Modal settings dialog for configuring base directory, IDE, and exclusions."""

    def __init__(self, parent, config: Dict[str, Any], on_save: Callable):
        self.parent = parent
        self.config = config
        self.on_save = on_save
        self.ides: List[IDEInfo] = []
        self.result_config: Dict[str, Any] | None = None

        # Build dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("设置")
        self.dialog.geometry("550x480")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center on parent
        self.dialog.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        dw, dh = 550, 480
        x = px + (pw - dw) // 2
        y = py + (ph - dh) // 2
        self.dialog.geometry(f"{dw}x{dh}+{x}+{y}")

        self._build()
        self._load_values()

    # ── Layout builders ──────────────────────────────────────────────────

    def _build(self):
        """Build the full dialog layout, delegating to section builders."""
        main = ttk.Frame(self.dialog, padding=20)
        main.pack(fill=tk.BOTH, expand=True)

        self._build_dir_section(main)
        self._build_ide_section(main)
        self._build_exclusion_section(main)

        ttk.Separator(main, orient="horizontal").pack(fill=tk.X, pady=(16, 8))

        self.sort_var = tk.BooleanVar()
        ttk.Checkbutton(
            main, text="优先显示最近修改的项目", variable=self.sort_var,
        ).pack(anchor=tk.W)

        ttk.Separator(main, orient="horizontal").pack(fill=tk.X, pady=(12, 8))
        self._build_bottom_buttons(main)

    def _build_dir_section(self, main: ttk.Frame):
        """Build the base directory row."""
        ttk.Label(main, text="基础目录",
                  font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold")).pack(anchor=tk.W)

        dir_frame = ttk.Frame(main)
        dir_frame.pack(fill=tk.X, pady=(4, 16))

        self.dir_var = tk.StringVar()
        self.dir_entry = ttk.Entry(
            dir_frame, textvariable=self.dir_var,
            font=(FONT_FAMILY, FONT_SIZE_STATUS),
        )
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(dir_frame, text="浏览...", command=self._browse_dir).pack(
            side=tk.LEFT, padx=(6, 0),
        )

    def _build_ide_section(self, main: ttk.Frame):
        """Build the IDE selection row + custom path label."""
        ttk.Label(main, text="IDE",
                  font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold")).pack(anchor=tk.W)

        ide_frame = ttk.Frame(main)
        ide_frame.pack(fill=tk.X, pady=(4, 6))

        self.ide_var = tk.StringVar()
        self.ide_combo = ttk.Combobox(
            ide_frame, textvariable=self.ide_var, state="readonly",
        )
        self.ide_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.ide_combo.bind("<<ComboboxSelected>>", self._on_ide_selected)

        ttk.Button(ide_frame, text="浏览...", command=self._browse_ide).pack(
            side=tk.LEFT, padx=(6, 0),
        )

        self.custom_path_var = tk.StringVar()
        self.custom_path_label = ttk.Label(
            main, textvariable=self.custom_path_var,
            font=(FONT_FAMILY, FONT_SIZE_STATUS - 1), foreground="#888",
        )
        self.custom_path_label.pack(anchor=tk.W, pady=(0, 16))

    def _build_exclusion_section(self, main: ttk.Frame):
        """Build the excluded directories listbox + add/remove buttons."""
        ttk.Label(main, text="排除目录",
                  font=(FONT_FAMILY, FONT_SIZE_LARGE, "bold")).pack(anchor=tk.W)

        excl_frame = ttk.Frame(main)
        excl_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 4))

        list_frame = ttk.Frame(excl_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.excl_listbox = tk.Listbox(
            list_frame, height=6, font=(FONT_FAMILY, FONT_SIZE_STATUS),
            selectmode=tk.EXTENDED,
        )
        self.excl_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(
            list_frame, orient=tk.VERTICAL, command=self.excl_listbox.yview,
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.excl_listbox.configure(yscrollcommand=scrollbar.set)

        btn_frame = ttk.Frame(excl_frame)
        btn_frame.pack(fill=tk.X, pady=(4, 0))

        self.new_excl_var = tk.StringVar()
        self.new_excl_entry = ttk.Entry(
            btn_frame, textvariable=self.new_excl_var,
            font=(FONT_FAMILY, FONT_SIZE_STATUS), width=18,
        )
        self.new_excl_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.new_excl_entry.bind("<Return>", lambda e: self._add_exclusion())

        ttk.Button(btn_frame, text="添加", command=self._add_exclusion).pack(
            side=tk.LEFT, padx=(4, 0),
        )
        ttk.Button(btn_frame, text="删除", command=self._remove_exclusion).pack(
            side=tk.LEFT, padx=(4, 0),
        )

    def _build_bottom_buttons(self, main: ttk.Frame):
        """Build the Save / Cancel buttons at the bottom."""
        bottom = ttk.Frame(main)
        bottom.pack(fill=tk.X)

        ttk.Button(bottom, text="取消", command=self.dialog.destroy).pack(
            side=tk.RIGHT, padx=(6, 0),
        )

        save_btn = ttk.Button(
            bottom, text="保存", command=self._save, style="Accent.TButton",
        )
        save_btn.pack(side=tk.RIGHT)
        try:
            save_btn.configure(default="active")
        except tk.TclError:
            pass

    # ── Value loading ─────────────────────────────────────────────────────

    def _load_values(self):
        """Populate fields from current config."""
        base_dir = self.config.get("base_directory", "")
        self.dir_var.set(base_dir)

        # IDE detection
        self.ides = detect_ides()
        custom_ide = IDEInfo("custom", "自定义可执行文件...", "")
        self.ides.insert(len(self.ides) - 1, custom_ide)  # before explorer

        ide_display_names = [ide.display_name for ide in self.ides]
        self.ide_combo["values"] = ide_display_names

        selected_key = self.config.get("selected_ide", "auto")
        selected_index = 0

        if selected_key == "auto":
            for i, ide in enumerate(self.ides):
                if ide.key != "explorer":
                    selected_index = i
                    break
        else:
            for i, ide in enumerate(self.ides):
                if ide.key == selected_key:
                    selected_index = i
                    break

        if selected_index < len(ide_display_names):
            self.ide_combo.current(selected_index)
            self._on_ide_selected()

        self.custom_path_var.set(self.config.get("ide_custom_path", ""))

        for d in self.config.get("excluded_dirs", []):
            self.excl_listbox.insert(tk.END, d)

        self.sort_var.set(self.config.get("sort_recent_first", True))

    # ── Actions ────────────────────────────────────────────────────────────

    def _browse_dir(self):
        path = filedialog.askdirectory(title="选择项目目录", parent=self.dialog)
        if path:
            self.dir_var.set(path)

    def _browse_ide(self):
        path = filedialog.askopenfilename(
            title="选择 IDE 可执行文件",
            parent=self.dialog,
            filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")],
        )
        if path:
            self.custom_path_var.set(path)
            for i, ide in enumerate(self.ides):
                if ide.key == "custom":
                    self.ide_combo.current(i)
                    break
            self._on_ide_selected()

    def _on_ide_selected(self, event=None):
        """Show custom path when 'Custom...' is selected."""
        idx = self.ide_combo.current()
        if 0 <= idx < len(self.ides):
            ide = self.ides[idx]
            if ide.key == "custom":
                if not self.custom_path_var.get():
                    self.custom_path_var.set("（点击浏览选择 .exe 文件）")
            else:
                self.custom_path_var.set(ide.executable)

    def _add_exclusion(self):
        name = self.new_excl_var.get().strip()
        if not name:
            return
        existing = list(self.excl_listbox.get(0, tk.END))
        if name not in existing:
            self.excl_listbox.insert(tk.END, name)
        self.new_excl_var.set("")

    def _remove_exclusion(self):
        selected = self.excl_listbox.curselection()
        for idx in reversed(selected):
            self.excl_listbox.delete(idx)

    def _save(self):
        """Validate and save settings."""
        base_dir = self.dir_var.get().strip()
        if base_dir and not os.path.isdir(base_dir):
            messagebox.showwarning(
                "无效目录",
                f"目录不存在:\n{base_dir}\n\n请输入有效路径或留空。",
                parent=self.dialog,
            )
            return

        config = dict(self.config)

        config["base_directory"] = base_dir

        idx = self.ide_combo.current()
        if 0 <= idx < len(self.ides):
            ide = self.ides[idx]
            config["selected_ide"] = ide.key
            config["ide_custom_path"] = (
                self.custom_path_var.get() if ide.key == "custom" else ""
            )
        else:
            config["selected_ide"] = "auto"

        config["excluded_dirs"] = list(self.excl_listbox.get(0, tk.END))
        config["sort_recent_first"] = self.sort_var.get()

        self.result_config = config
        self.dialog.destroy()

    def get_result(self) -> Dict[str, Any] | None:
        """Wait for the dialog and return the saved config or None if cancelled."""
        self.dialog.wait_window()
        return self.result_config
