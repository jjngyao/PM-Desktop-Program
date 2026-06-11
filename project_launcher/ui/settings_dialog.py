"""Settings dialog for Project Launcher."""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Callable, Dict, Any, List

from launcher import detect_ides, IDEInfo


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
        self.dialog.title('设置')
        self.dialog.geometry('550x480')
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()

        # Center on parent
        self.dialog.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        dw = 550
        dh = 480
        x = px + (pw - dw) // 2
        y = py + (ph - dh) // 2
        self.dialog.geometry(f'{dw}x{dh}+{x}+{y}')

        self._build()

        # Pre-populate
        self._load_values()

    def _build(self):
        """Build the dialog layout."""
        main = ttk.Frame(self.dialog, padding=20)
        main.pack(fill=tk.BOTH, expand=True)

        # ── Base Directory ──────────────────────────────────────────────

        ttk.Label(main, text='基础目录', font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)

        dir_frame = ttk.Frame(main)
        dir_frame.pack(fill=tk.X, pady=(4, 16))

        self.dir_var = tk.StringVar()
        self.dir_entry = ttk.Entry(dir_frame, textvariable=self.dir_var, font=('Segoe UI', 9))
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        browse_dir_btn = ttk.Button(dir_frame, text='浏览...', command=self._browse_dir)
        browse_dir_btn.pack(side=tk.LEFT, padx=(6, 0))

        # ── IDE Selection ───────────────────────────────────────────────

        ttk.Label(main, text='IDE', font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)

        ide_frame = ttk.Frame(main)
        ide_frame.pack(fill=tk.X, pady=(4, 6))

        self.ide_var = tk.StringVar()
        self.ide_combo = ttk.Combobox(ide_frame, textvariable=self.ide_var, state='readonly')
        self.ide_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.ide_combo.bind('<<ComboboxSelected>>', self._on_ide_selected)

        custom_btn = ttk.Button(ide_frame, text='浏览...', command=self._browse_ide)
        custom_btn.pack(side=tk.LEFT, padx=(6, 0))

        self.custom_path_var = tk.StringVar()
        self.custom_path_label = ttk.Label(main, textvariable=self.custom_path_var,
                                           font=('Segoe UI', 8), foreground='#888')
        self.custom_path_label.pack(anchor=tk.W, pady=(0, 16))

        # ── Excluded Directories ────────────────────────────────────────

        ttk.Label(main, text='排除目录', font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W)

        excl_frame = ttk.Frame(main)
        excl_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 4))

        # Listbox + scrollbar
        list_frame = ttk.Frame(excl_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.excl_listbox = tk.Listbox(list_frame, height=6, font=('Segoe UI', 9),
                                        selectmode=tk.EXTENDED)
        self.excl_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL,
                                   command=self.excl_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.excl_listbox.configure(yscrollcommand=scrollbar.set)

        # Add/remove buttons
        btn_frame = ttk.Frame(excl_frame)
        btn_frame.pack(fill=tk.X, pady=(4, 0))

        self.new_excl_var = tk.StringVar()
        self.new_excl_entry = ttk.Entry(btn_frame, textvariable=self.new_excl_var,
                                         font=('Segoe UI', 9), width=18)
        self.new_excl_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.new_excl_entry.bind('<Return>', lambda e: self._add_exclusion())

        add_btn = ttk.Button(btn_frame, text='添加', command=self._add_exclusion)
        add_btn.pack(side=tk.LEFT, padx=(4, 0))

        remove_btn = ttk.Button(btn_frame, text='删除', command=self._remove_exclusion)
        remove_btn.pack(side=tk.LEFT, padx=(4, 0))

        # ── Sort option ─────────────────────────────────────────────────

        ttk.Separator(main, orient='horizontal').pack(fill=tk.X, pady=(16, 8))

        self.sort_var = tk.BooleanVar()
        sort_cb = ttk.Checkbutton(main, text='优先显示最近修改的项目',
                                   variable=self.sort_var)
        sort_cb.pack(anchor=tk.W)

        # ── Buttons ─────────────────────────────────────────────────────

        ttk.Separator(main, orient='horizontal').pack(fill=tk.X, pady=(12, 8))

        bottom = ttk.Frame(main)
        bottom.pack(fill=tk.X)

        cancel_btn = ttk.Button(bottom, text='取消', command=self.dialog.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=(6, 0))

        save_btn = ttk.Button(bottom, text='保存', command=self._save, style='Accent.TButton')
        save_btn.pack(side=tk.RIGHT)

        # Try to make save button accent-colored
        try:
            save_btn.configure(default='active')
        except tk.TclError:
            pass

    def _load_values(self):
        """Populate fields from current config."""
        # Base directory
        base_dir = self.config.get('base_directory', '')
        self.dir_var.set(base_dir)

        # IDE detection
        self.ides = detect_ides()
        # Add custom option
        custom_ide = IDEInfo('custom', '自定义可执行文件...', '')
        self.ides.insert(len(self.ides) - 1, custom_ide)  # before explorer

        ide_display_names = [ide.display_name for ide in self.ides]
        self.ide_combo['values'] = ide_display_names

        selected_key = self.config.get('selected_ide', 'auto')
        selected_index = 0

        if selected_key == 'auto':
            # select the first non-explorer IDE, or explorer
            for i, ide in enumerate(self.ides):
                if ide.key != 'explorer':
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

        self.custom_path_var.set(self.config.get('ide_custom_path', ''))

        # Exclusions
        for d in self.config.get('excluded_dirs', []):
            self.excl_listbox.insert(tk.END, d)

        # Sort
        self.sort_var.set(self.config.get('sort_recent_first', True))

    def _browse_dir(self):
        path = filedialog.askdirectory(title='选择项目目录', parent=self.dialog)
        if path:
            self.dir_var.set(path)

    def _browse_ide(self):
        path = filedialog.askopenfilename(
            title='选择 IDE 可执行文件',
            parent=self.dialog,
            filetypes=[('可执行文件', '*.exe'), ('所有文件', '*.*')],
        )
        if path:
            self.custom_path_var.set(path)
            # Switch to custom mode
            for i, ide in enumerate(self.ides):
                if ide.key == 'custom':
                    self.ide_combo.current(i)
                    break
            self._on_ide_selected()

    def _on_ide_selected(self, event=None):
        """Show custom path when 'Custom...' is selected."""
        idx = self.ide_combo.current()
        if idx >= 0 and idx < len(self.ides):
            ide = self.ides[idx]
            if ide.key == 'custom':
                if not self.custom_path_var.get():
                    self.custom_path_var.set('（点击浏览选择 .exe 文件）')
            else:
                self.custom_path_var.set(ide.executable)

    def _add_exclusion(self):
        name = self.new_excl_var.get().strip()
        if not name:
            return
        # Check duplicate
        existing = list(self.excl_listbox.get(0, tk.END))
        if name not in existing:
            self.excl_listbox.insert(tk.END, name)
        self.new_excl_var.set('')

    def _remove_exclusion(self):
        selected = self.excl_listbox.curselection()
        # Delete in reverse to keep indices valid
        for idx in reversed(selected):
            self.excl_listbox.delete(idx)

    def _save(self):
        """Validate and save settings."""
        base_dir = self.dir_var.get().strip()
        if base_dir and not os.path.isdir(base_dir):
            messagebox.showwarning(
                '无效目录',
                f'目录不存在:\n{base_dir}\n\n'
                '请输入有效路径或留空。',
                parent=self.dialog,
            )
            return

        # Build config
        config = dict(self.config)  # copy

        config['base_directory'] = base_dir

        idx = self.ide_combo.current()
        if idx >= 0 and idx < len(self.ides):
            ide = self.ides[idx]
            config['selected_ide'] = ide.key
            if ide.key == 'custom':
                config['ide_custom_path'] = self.custom_path_var.get()
            else:
                config['ide_custom_path'] = ''
        else:
            config['selected_ide'] = 'auto'

        config['excluded_dirs'] = list(self.excl_listbox.get(0, tk.END))
        config['sort_recent_first'] = self.sort_var.get()

        self.result_config = config
        self.dialog.destroy()

    def get_result(self) -> Dict[str, Any] | None:
        """Wait for the dialog and return the saved config or None if cancelled."""
        self.dialog.wait_window()
        return self.result_config
