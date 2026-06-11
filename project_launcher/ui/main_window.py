"""Main window for Project Launcher.

Provides the search bar, scrollable project list, status bar, and settings access.
"""

import ctypes
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Any, Optional, Set

from scanner import ProjectInfo, scan_async
from launcher import detect_ides, find_ide_by_key, launch, IDEInfo
from config import save_config, get_config_path
from ui.widgets import SearchEntry, ProjectItemFrame, show_error
from ui.settings_dialog import SettingsDialog


class MainWindow:
    """Primary application window."""

    def __init__(self, config: Dict[str, Any], on_config_changed=None):
        self.config = config
        self.on_config_changed = on_config_changed
        self.projects: List[ProjectInfo] = []
        self.current_ide: Optional[IDEInfo] = None
        self.project_frames: List[ProjectItemFrame] = []
        self._scan_thread = None

        # ── Root window ─────────────────────────────────────────────────

        self.root = tk.Tk()
        self.root.title('项目启动器')
        self.root.minsize(400, 300)

        # Restore geometry
        geo = config.get('window_geometry', '900x600')
        if '+' not in geo:
            # Center on screen
            self.root.update_idletasks()
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            w, h = 900, 600
            x = (sw - w) // 2
            y = (sh - h) // 2
            geo = f'{w}x{h}+{x}+{y}'
        self.root.geometry(geo)

        # App icon
        self._set_icon()

        # DPI awareness (set before any widget creation)
        self._set_dpi_aware()

        # Styles
        self._setup_styles()

        # ── Build layout ────────────────────────────────────────────────

        self._build_toolbar()
        self._build_project_list()
        self._build_status_bar()

        # ── Detect IDE ──────────────────────────────────────────────────

        self._detect_ide()

        # ── Bind events ─────────────────────────────────────────────────

        self.root.protocol('WM_DELETE_WINDOW', self._on_close)
        self.root.bind('<F5>', lambda e: self.refresh())
        self.root.bind('<Control-r>', lambda e: self.refresh())

        # ── Initial scan ────────────────────────────────────────────────

        self.root.after(100, self.refresh)

    # ── DPI & Styling ───────────────────────────────────────────────────────

    def _set_dpi_aware(self):
        """Enable DPI awareness to prevent blurry text on high-DPI displays."""
        if sys.platform != 'win32':
            return
        try:
            # Windows 10 1703+
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_AWARE_V2
        except AttributeError:
            try:
                # Windows 8.1+
                ctypes.windll.shcore.SetProcessDpiAwareness(1)  # SYSTEM_AWARE
            except AttributeError:
                try:
                    # Windows Vista+
                    ctypes.windll.user32.SetProcessDPIAware()
                except AttributeError:
                    pass

    def _set_icon(self):
        """Set the window icon."""
        try:
            if getattr(sys, 'frozen', False):
                base = sys._MEIPASS
            else:
                base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            icon_path = os.path.join(base, 'icon.png')
            if os.path.exists(icon_path):
                img = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, img)
        except Exception:
            pass  # icon is optional

    def _setup_styles(self):
        """Configure ttk styles."""
        style = ttk.Style()

        # Try to use a modern theme
        try:
            style.theme_use('vista')
        except tk.TclError:
            try:
                style.theme_use('clam')
            except tk.TclError:
                pass

        # Fonts
        self.FONT_TOOLBAR = ('Segoe UI', 10)
        self.FONT_STATUS = ('Segoe UI', 9)

        # Custom styles
        style.configure('Project.TFrame', background='#ffffff')
        style.configure('ProjectHover.TFrame', background='#e8e8e8')

        # Accent button style
        style.configure('Accent.TButton', font=('Segoe UI', 9))

        # Gear button style
        style.configure('Gear.TButton', font=('Segoe UI', 14), padding=(4, 2))

    # ── Layout builders ─────────────────────────────────────────────────────

    def _build_toolbar(self):
        """Build the search bar + settings gear."""
        toolbar = ttk.Frame(self.root, padding=(10, 10, 10, 6))
        toolbar.pack(fill=tk.X)

        # Settings gear (left side)
        gear_btn = tk.Button(
            toolbar,
            text='⚙',
            font=('Segoe UI', 14),
            bg='#f0f0f0',
            bd=0,
            cursor='hand2',
            activebackground='#e0e0e0',
            command=self._open_settings,
        )
        gear_btn.pack(side=tk.LEFT, padx=(0, 8))

        # Search entry
        self.search_entry = SearchEntry(
            toolbar,
            placeholder='搜索项目...',
            font=self.FONT_TOOLBAR,
        )
        self.search_entry.set_callback(self._on_search)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        # Refresh button
        refresh_btn = tk.Button(
            toolbar,
            text='↻',
            font=('Segoe UI', 14),
            bg='#f0f0f0',
            bd=0,
            cursor='hand2',
            activebackground='#e0e0e0',
            command=self.refresh,
        )
        refresh_btn.pack(side=tk.LEFT, padx=(8, 0))

    def _build_project_list(self):
        """Build the scrollable project list area."""
        # Outer frame
        list_container = ttk.Frame(self.root)
        list_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))

        # Canvas for scrolling
        self.list_canvas = tk.Canvas(list_container, bg='#ffffff', highlightthickness=0)
        self.list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL,
                                   command=self.list_canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.list_canvas.configure(yscrollcommand=scrollbar.set)

        # Inner frame that holds the project items
        self.list_frame = ttk.Frame(self.list_canvas, style='Project.TFrame')
        self.list_frame_id = self.list_canvas.create_window(
            (0, 0), window=self.list_frame, anchor='nw', tags='list_frame'
        )

        # Bind canvas resize to adjust inner frame width
        self.list_canvas.bind('<Configure>', self._on_canvas_configure)
        self.list_frame.bind('<Configure>', self._on_frame_configure)

        # Mousewheel scrolling
        self.list_canvas.bind('<MouseWheel>', self._on_mousewheel)
        self.list_canvas.bind('<Enter>', self._on_canvas_enter)
        self.list_canvas.bind('<Leave>', self._on_canvas_leave)

    def _build_status_bar(self):
        """Build the status bar at the bottom."""
        status_frame = ttk.Frame(self.root, padding=(12, 4))
        status_frame.pack(fill=tk.X)

        ttk.Separator(status_frame, orient='horizontal').pack(fill=tk.X)

        label_frame = ttk.Frame(status_frame, padding=(0, 4, 0, 0))
        label_frame.pack(fill=tk.X)

        self.status_label = tk.Label(
            label_frame,
            text='就绪',
            font=self.FONT_STATUS,
            fg='#666666',
            bg=self.root.cget('bg'),
            anchor='w',
        )
        self.status_label.pack(side=tk.LEFT)

        self.ide_label = tk.Label(
            label_frame,
            text='',
            font=self.FONT_STATUS,
            fg='#888888',
            bg=self.root.cget('bg'),
            anchor='e',
        )
        self.ide_label.pack(side=tk.RIGHT)

    # ── Canvas/scroll handling ──────────────────────────────────────────────

    def _on_canvas_configure(self, event):
        """Resize the inner frame to match canvas width."""
        self.list_canvas.itemconfig(self.list_frame_id, width=event.width)

    def _on_frame_configure(self, event):
        """Update scroll region when inner frame size changes."""
        self.list_canvas.configure(scrollregion=self.list_canvas.bbox('all'))

    def _on_mousewheel(self, event):
        """Handle mousewheel scrolling."""
        self.list_canvas.yview_scroll(-1 * (event.delta // 120), 'units')

    def _on_canvas_enter(self, event):
        """Bind mousewheel at root level when cursor enters canvas area."""
        self.root.bind('<MouseWheel>', self._on_mousewheel_redirect, add='+')

    def _on_canvas_leave(self, event):
        """Unbind root-level mousewheel when cursor leaves canvas area."""
        self.root.unbind('<MouseWheel>')

    def _on_mousewheel_redirect(self, event):
        """Redirect root-level mousewheel to the list canvas for scrolling."""
        self.list_canvas.yview_scroll(-1 * (event.delta // 120), 'units')

    # ── IDE detection ───────────────────────────────────────────────────────

    def _detect_ide(self):
        """Detect the current IDE based on config."""
        ide_key = self.config.get('selected_ide', 'auto')
        custom_path = self.config.get('ide_custom_path', '')

        if ide_key == 'auto':
            # Pick the first non-explorer IDE
            ides = detect_ides()
            for ide in ides:
                if ide.key != 'explorer':
                    self.current_ide = ide
                    break
            else:
                self.current_ide = IDEInfo('explorer', '文件资源管理器', '')
        else:
            self.current_ide = find_ide_by_key(ide_key, custom_path)
            if self.current_ide is None:
                self.current_ide = IDEInfo('explorer', '文件资源管理器', '')
                self.ide_label.config(text='未找到 IDE — 使用文件资源管理器')
                return

        if self.current_ide:
            self.ide_label.config(text=self.current_ide.display_name)

    # ── Project scanning ────────────────────────────────────────────────────

    def refresh(self):
        """Re-scan the base directory and rebuild the project list."""
        base_dir = self.config.get('base_directory', '')
        if not base_dir:
            self._show_empty('未设置基础目录。\n点击 ⚙ 齿轮图标进行配置。')
            self.status_label.config(text='未配置基础目录')
            return

        excluded = set(self.config.get('excluded_dirs', []))
        sort_recent = self.config.get('sort_recent_first', True)

        self._set_scanning(True)

        def on_callback(phase, data):
            self.root.after(0, lambda: self._handle_scan_callback(phase, data))

        self._scan_thread = scan_async(base_dir, excluded, on_callback, sort_recent)

    def _set_scanning(self, scanning: bool):
        """Update UI state during scanning."""
        if scanning:
            self.status_label.config(text='正在扫描...')

    def _handle_scan_callback(self, phase: str, data: dict):
        """Handle scanner callbacks on the main thread."""
        if phase == 'progress':
            current = data.get('current', 0)
            total = data.get('total', 0)
            self.status_label.config(text=f'正在扫描... {current}/{total}')

        elif phase == 'error':
            msg = data.get('message', '未知错误')
            show_error(self.root, '扫描错误', msg)
            self.status_label.config(text='扫描失败')
            self._show_empty(f'无法访问:\n{self.config.get("base_directory", "")}')

        elif phase == 'complete':
            self.projects = data.get('projects', [])
            errors = data.get('errors', [])
            skipped = data.get('skipped', 0)
            self._rebuild_list()

            # Update status
            parts = [f'{len(self.projects)} 个项目']
            if skipped:
                parts.append(f'{skipped} 个已跳过')
            base = self.config.get('base_directory', '')
            parts.append(f'| {base}')
            self.status_label.config(text='  '.join(parts))

            if errors:
                self.ide_label.config(text=f'⚠ {errors[0][:40]}...' if len(errors[0]) > 40 else f'⚠ {errors[0]}')

    # ── Project list display ────────────────────────────────────────────────

    def _rebuild_list(self, filter_query: str = ''):
        """Rebuild the visible project list, optionally filtered."""
        # Clear existing frames
        for frame in self.project_frames:
            frame.destroy()
        self.project_frames.clear()

        # Filter
        query = filter_query.lower().strip()
        if query:
            visible = [p for p in self.projects if query in p.name.lower()]
        else:
            visible = self.projects

        if not visible:
            self._show_empty(
                f'未找到匹配 "{filter_query}" 的项目'
                if filter_query else
                '未找到项目。\n点击 ⚙ 齿轮图标更改目录。'
            )
            return

        # Clear empty-state
        self._clear_empty()

        # Build frames
        for project in visible:
            frame = ProjectItemFrame(
                self.list_frame,
                project,
                on_launch=self._on_launch_project,
            )
            frame.pack(fill=tk.X)
            self.project_frames.append(frame)

        # Reset scroll to top
        self.list_canvas.yview_moveto(0)

        # Update status count if filtered
        if query:
            self.status_label.config(
                text=f'{len(visible)} / {len(self.projects)} 个项目 | {self.config.get("base_directory", "")}'
            )

    def _show_empty(self, message: str):
        """Show the empty-state message."""
        self._clear_empty()
        self._empty_label = tk.Label(
            self.list_frame,
            text=message,
            font=('Segoe UI', 12),
            fg='#aaaaaa',
            bg='#ffffff',
            justify=tk.CENTER,
        )
        self._empty_label.pack(expand=True, fill=tk.BOTH, pady=80)

    def _clear_empty(self):
        """Remove the empty-state label if present."""
        if hasattr(self, '_empty_label') and self._empty_label:
            self._empty_label.destroy()
            self._empty_label = None

    # ── Actions ─────────────────────────────────────────────────────────────

    def _on_search(self, query: str):
        """Handle search query changes."""
        self._rebuild_list(filter_query=query)

    def _on_launch_project(self, project: ProjectInfo):
        """Handle double-click to launch a project."""
        if not self.current_ide:
            self.current_ide = IDEInfo('explorer', '文件资源管理器', '')

        success = launch(project.path, self.current_ide)

        if not success:
            # Project no longer exists?
            if not os.path.isdir(project.path):
                show_error(
                    self.root,
                    '项目不存在',
                    f'项目目录已不存在:\n{project.path}\n\n正在刷新列表...',
                )
                self.refresh()
                return

        # Update last_opened timestamp
        last_opened = self.config.setdefault('last_opened', {})
        from datetime import datetime
        last_opened[project.path] = datetime.now().isoformat()
        save_config(self.config)

    def _open_settings(self):
        """Open the settings dialog."""
        dialog = SettingsDialog(self.root, self.config, on_save=self._on_settings_saved)
        result = dialog.get_result()

        if result is not None:
            self.config = result
            save_config(self.config)
            self._detect_ide()
            self.refresh()
            if self.on_config_changed:
                self.on_config_changed(self.config)

    def _on_settings_saved(self, config: Dict[str, Any]):
        """Called after settings are saved (can be used for additional actions)."""
        pass

    # ── Lifecycle ───────────────────────────────────────────────────────────

    def _on_close(self):
        """Handle window close — save config and exit."""
        geo = self.root.geometry()
        self.config['window_geometry'] = geo
        save_config(self.config)
        self.root.destroy()

    def run(self):
        """Start the Tkinter main loop."""
        self.root.mainloop()
