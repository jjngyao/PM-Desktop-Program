"""Main window for Project Launcher.

Provides the search bar, scrollable project list, status bar, and settings access.
"""

import ctypes
import os
import shutil
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Any, Optional, Set

from scanner import ProjectInfo, scan_async
from launcher import detect_ides, find_ide_by_key, launch, IDEInfo
from config import save_config, get_config_path
from ui.widgets import SearchEntry, ProjectItemFrame, DirectoryEntryFrame, show_error
from ui.settings_dialog import SettingsDialog


class MainWindow:
    """Primary application window."""

    def __init__(self, config: Dict[str, Any], on_config_changed=None):
        self.config = config
        self.on_config_changed = on_config_changed
        self.projects: List[ProjectInfo] = []
        self.current_ide: Optional[IDEInfo] = None
        self.project_frames: List[ProjectItemFrame] = []
        self._view_mode: str = 'projects'   # 'projects' or 'directory'
        self._browsing_path: Optional[str] = None
        self._browse_history: List[tuple] = []  # stack of (path, view_mode)
        self._dir_frames: List[DirectoryEntryFrame] = []
        self._nav_frame: Optional[tk.Frame] = None
        self._scan_thread = None
        self._pending_drops: List[List[str]] = []   # queue for drag-drop files
        self._drop_poll_id: Optional[str] = None

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

        # New folder button
        new_folder_btn = tk.Button(
            toolbar,
            text='📁 新建文件夹',
            font=('Segoe UI', 10),
            bg='#f0f0f0',
            bd=0,
            cursor='hand2',
            activebackground='#e0e0e0',
            command=self._on_new_folder,
        )
        new_folder_btn.pack(side=tk.LEFT, padx=(0, 8))

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
        # Reset to project list view if currently browsing
        self._hide_browse_nav()
        self._clear_all_frames()
        self._view_mode = 'projects'
        self._browsing_path = None
        self._browse_history.clear()

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
        # Ensure we are in project list view
        self._hide_browse_nav()
        self._view_mode = 'projects'
        self._browsing_path = None
        self._browse_history.clear()

        # Clear existing frames
        for frame in self.project_frames:
            frame.destroy()
        self.project_frames.clear()
        for frame in self._dir_frames:
            frame.destroy()
        self._dir_frames.clear()

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
                on_enter=self._on_enter_project,
                on_launch_ide=self._on_launch_ide,
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
        """Handle search query changes (project list view only)."""
        if self._view_mode != 'projects':
            return
        self._rebuild_list(filter_query=query)

    def _on_enter_project(self, project: ProjectInfo):
        """Handle double-click to browse project directory contents."""
        self._browse_history.append((None, 'projects'))
        self._show_directory(project.path)

    def _on_launch_ide(self, project: ProjectInfo):
        """Handle 'Open with IDE' action — launch project in the bound IDE."""
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

    # ── Directory browsing ─────────────────────────────────────────────────

    def _show_directory(self, path: str):
        """Display the contents of a directory in the list area."""
        self._view_mode = 'directory'
        self._browsing_path = path

        # Clear existing frames
        self._clear_all_frames()

        # Show navigation bar
        self._show_browse_nav()

        # List entries — directories first, then files
        try:
            entries = sorted(
                os.scandir(path),
                key=lambda e: (not e.is_dir(), e.name.lower()),
            )
        except (PermissionError, OSError):
            self._show_empty('没有权限访问此目录')
            return

        entry_list = list(entries)
        # Limit to avoid UI freeze with very large directories
        if len(entry_list) > 500:
            entry_list = entry_list[:500]

        if not entry_list:
            self._show_empty('此目录为空')
            return

        self._clear_empty()

        for entry in entry_list:
            try:
                is_dir = entry.is_dir()
            except OSError:
                is_dir = False

            frame = DirectoryEntryFrame(
                self.list_frame,
                entry.name,
                entry.path,
                is_dir=is_dir,
                on_click=self._on_directory_entry_click,
            )
            frame.pack(fill=tk.X)
            self._dir_frames.append(frame)

        # Reset scroll to top
        self.list_canvas.yview_moveto(0)

    def _on_directory_entry_click(self, path: str):
        """Handle clicking a directory entry — navigate into it."""
        self._browse_history.append((self._browsing_path, 'directory'))
        self._show_directory(path)

    def _show_browse_nav(self):
        """Show the directory browse navigation bar."""
        if self._nav_frame is not None:
            self._nav_frame.destroy()

        self._nav_frame = tk.Frame(self.list_frame, bg='#f5f5f5', height=36)
        self._nav_frame.pack(fill=tk.X)

        back_btn = tk.Button(
            self._nav_frame,
            text='← 返回',
            font=('Segoe UI', 10),
            bg='#f5f5f5',
            bd=0,
            cursor='hand2',
            activebackground='#e0e0e0',
            command=self._go_back,
        )
        back_btn.pack(side=tk.LEFT, padx=(8, 12), pady=4)

        path_label = tk.Label(
            self._nav_frame,
            text=self._browsing_path,
            font=('Segoe UI', 9),
            fg='#666666',
            bg='#f5f5f5',
            anchor='w',
        )
        path_label.pack(side=tk.LEFT, fill=tk.X, pady=4)

    def _hide_browse_nav(self):
        """Hide the directory browse navigation bar."""
        if self._nav_frame is not None:
            self._nav_frame.destroy()
            self._nav_frame = None

    def _go_back(self):
        """Navigate back from directory view to the previous view."""
        if not self._browse_history:
            return

        prev_path, prev_mode = self._browse_history.pop()
        self._hide_browse_nav()
        self._clear_all_frames()
        self._clear_empty()

        if prev_mode == 'projects':
            self._view_mode = 'projects'
            self._browsing_path = None
            # Rebuild project list with current search query
            query = self.search_entry.get_query()
            self._rebuild_list(filter_query=query)
        else:
            self._show_directory(prev_path)

    def _clear_all_frames(self):
        """Clear all item frames (both project and directory entries)."""
        for frame in self.project_frames:
            frame.destroy()
        self.project_frames.clear()
        for frame in self._dir_frames:
            frame.destroy()
        self._dir_frames.clear()

    # ── Drag-and-drop file copy ────────────────────────────────────────────

    def _setup_drop_target(self):
        """Register the root window as a Windows drop target via WM_DROPFILES.

        Uses SetWindowSubclass (comctl32.dll) to safely add a subclass
        procedure without replacing Tk's own WNDPROC.  This is the
        recommended Windows API for window subclassing and avoids having
        Tk accidentally reset our hook.
        """
        if sys.platform != 'win32':
            return

        try:
            hwnd = self.root.winfo_id()
        except tk.TclError:
            return  # window not yet realized

        # ── Set argtypes for ALL shell32 drag-drop functions ───────────
        # CRITICAL: without explicit argtypes, ctypes defaults pointer-sized
        # parameters (HWND, HDROP) to c_int (32-bit), causing OverflowError
        # on 64-bit Windows when the handle value exceeds 2³¹.
        sh = ctypes.windll.shell32
        sh.DragAcceptFiles.argtypes = [ctypes.c_longlong, ctypes.c_int]
        sh.DragQueryFileW.argtypes = [
            ctypes.c_longlong,   # HDROP
            ctypes.c_uint,       # UINT iFile
            ctypes.c_wchar_p,    # LPWSTR lpszFile (or NULL)
            ctypes.c_uint,       # UINT cch
        ]
        sh.DragQueryFileW.restype = ctypes.c_uint
        sh.DragFinish.argtypes = [ctypes.c_longlong]  # HDROP

        # ── SUBCLASSPROC signature ───────────────────────────────────────
        SUBCLASSPROC = ctypes.WINFUNCTYPE(
            ctypes.c_longlong,   # return: LRESULT
            ctypes.c_longlong,   # HWND
            ctypes.c_uint,       # UINT  msg
            ctypes.c_longlong,   # WPARAM
            ctypes.c_longlong,   # LPARAM
            ctypes.c_longlong,   # UINT_PTR  uIdSubclass
            ctypes.c_longlong,   # DWORD_PTR dwRefData
        )

        # ── Build the subclass procedure closure ─────────────────────────
        # WARNING: an unhandled Python exception inside a ctypes callback
        # can terminate the process instantly (C stack unwinding).  Wrap
        # EVERYTHING in a blanket try/except to prevent crashes.
        #
        # IMPORTANT: to avoid C-level crashes (which Python try/except
        # cannot catch), we never call any Tkinter API from inside this
        # callback.  Instead we push file paths onto a thread-safe list
        # and let a periodic Tkinter timer drain it.

        self._pending_drops: List[List[str]] = []

        @SUBCLASSPROC
        def subclass_proc(hwnd, msg, wparam, lparam, _uid, _ref):
            WM_DROPFILES = 0x0233
            try:
                if msg == WM_DROPFILES:
                    hdrop = wparam

                    # Validate the handle — hdrop from wparam should be
                    # non-zero for a real drop.
                    if not hdrop:
                        return 0

                    count = sh.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
                    # Sanity-check: a single drag operation shouldn't
                    # produce more than 10 000 files.
                    if count == 0 or count > 10000:
                        sh.DragFinish(hdrop)
                        return 0

                    files: List[str] = []
                    for i in range(count):
                        buf = ctypes.create_unicode_buffer(260)
                        sh.DragQueryFileW(hdrop, i, buf, 260)
                        files.append(buf.value)

                    sh.DragFinish(hdrop)

                    if files:
                        # Push to pending queue — NEVER call Tkinter here
                        self._pending_drops.append(files)
                    return 0

                # All other messages → continue the subclass chain
                return ctypes.windll.comctl32.DefSubclassProc(
                    hwnd, msg, wparam, lparam
                )
            except Exception:
                # Never let an exception escape a ctypes callback
                import traceback, tempfile
                try:
                    _p = os.path.join(tempfile.gettempdir(),
                                       'project_launcher_dnd_crash.log')
                    with open(_p, 'a', encoding='utf-8') as _f:
                        _f.write(traceback.format_exc() + '\n')
                except Exception:
                    pass
                return 0

        self._subclass_proc_ref = subclass_proc

        # ── Install the subclass ─────────────────────────────────────────

        comctl32 = ctypes.windll.comctl32
        comctl32.SetWindowSubclass.argtypes = [
            ctypes.c_longlong,   # HWND
            SUBCLASSPROC,        # SUBCLASSPROC
            ctypes.c_longlong,   # UINT_PTR uIdSubclass
            ctypes.c_longlong,   # DWORD_PTR dwRefData
        ]
        comctl32.SetWindowSubclass.restype = ctypes.c_int  # BOOL
        comctl32.DefSubclassProc.argtypes = [
            ctypes.c_longlong, ctypes.c_uint, ctypes.c_longlong, ctypes.c_longlong,
        ]
        comctl32.DefSubclassProc.restype = ctypes.c_longlong

        ok = comctl32.SetWindowSubclass(hwnd, subclass_proc, 42, 0)
        if not ok:
            # Fallback: try the old-style WNDPROC replacement
            self._setup_drop_target_fallback(hwnd)
            return

        # Register the window to accept dropped files
        sh.DragAcceptFiles(hwnd, True)

        # Start the polling timer that drains _pending_drops on the
        # Tkinter main thread (never from inside the C callback).
        self._poll_drop_queue()

    def _poll_drop_queue(self):
        """Periodically check for files appended by the subclass proc and
        hand them off to the normal file-copy pipeline on the main thread."""
        try:
            # Process at most one batch per tick to keep the UI responsive
            if self._pending_drops:
                batch = self._pending_drops.pop(0)
                self._handle_dropped_files(batch)
        except Exception:
            pass  # defence in depth — logged inside _handle_dropped_files
        # Poll every 200 ms
        self._drop_poll_id = self.root.after(200, self._poll_drop_queue)

    def _setup_drop_target_fallback(self, hwnd):
        """Fallback: direct WNDPROC replacement when SetWindowSubclass fails
        (extremely rare — only on pre-XP systems or corrupted comctl32)."""
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

        # Keep a separate reference to the fallback callback
        _fallback_ref = WNDPROC_TYPE(self._drop_wndproc_fallback)
        self._fallback_wndproc_ref = _fallback_ref
        self._fallback_original = user32.GetWindowLongPtrW(hwnd, GWL_WNDPROC)

        new_addr = ctypes.cast(_fallback_ref, ctypes.c_void_p).value
        user32.SetWindowLongPtrW(hwnd, GWL_WNDPROC, new_addr)

        ctypes.windll.shell32.DragAcceptFiles(hwnd, True)

    def _drop_wndproc_fallback(self, hwnd, msg, wparam, lparam):
        """Fallback WNDPROC — same logic as the subclass proc above.
        Uses the pending-queue pattern (no Tkinter calls from C callback)."""
        WM_DROPFILES = 0x0233
        try:
            if msg == WM_DROPFILES:
                hdrop = wparam
                if not hdrop:
                    return 0
                shell32 = ctypes.windll.shell32
                count = shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
                if count == 0 or count > 10000:
                    shell32.DragFinish(hdrop)
                    return 0
                files: List[str] = []
                for i in range(count):
                    buf = ctypes.create_unicode_buffer(260)
                    shell32.DragQueryFileW(hdrop, i, buf, 260)
                    files.append(buf.value)
                shell32.DragFinish(hdrop)
                if files:
                    self._pending_drops.append(files)
                return 0
            return ctypes.windll.user32.CallWindowProcW(
                self._fallback_original, hwnd, msg, wparam, lparam
            )
        except Exception:
            import traceback, tempfile
            try:
                _p = os.path.join(tempfile.gettempdir(),
                                   'project_launcher_dnd_crash.log')
                with open(_p, 'a', encoding='utf-8') as _f:
                    _f.write(traceback.format_exc() + '\n')
            except Exception:
                pass
            return 0

    def _handle_dropped_files(self, files: List[str]):
        """Copy dropped files to the current target directory.

        Target directory determination:
        - Directory-browsing mode (_browsing_path not None) → _browsing_path
        - Project-list mode (_browsing_path is None) → base_directory
        - Neither → show a warning
        """
        try:
            self._handle_dropped_files_impl(files)
        except Exception:
            import traceback, tempfile
            try:
                _p = os.path.join(tempfile.gettempdir(),
                                   'project_launcher_dnd_crash.log')
                with open(_p, 'a', encoding='utf-8') as _f:
                    _f.write(traceback.format_exc() + '\n')
            except Exception:
                pass
            messagebox.showerror(
                '拖放错误',
                f'处理拖放文件时出错，详情请查看:\n'
                f'{os.path.join(tempfile.gettempdir(), "project_launcher_dnd_crash.log")}',
                parent=self.root,
            )

    def _handle_dropped_files_impl(self, files: List[str]):
        # ── Determine target directory ───────────────────────────────────

        if self._browsing_path:
            target_dir = self._browsing_path
        else:
            target_dir = self.config.get('base_directory', '')

        if not target_dir:
            messagebox.showwarning(
                '无法复制',
                '请先在设置中配置基础目录，或双击项目进入目录浏览模式。',
                parent=self.root,
            )
            return

        if not os.path.isdir(target_dir):
            messagebox.showwarning(
                '目录不存在',
                f'目标目录不存在:\n{target_dir}',
                parent=self.root,
            )
            return

        # ── Check for filename conflicts ─────────────────────────────────

        existing_names: List[str] = []
        for f in files:
            name = os.path.basename(f)
            if os.path.exists(os.path.join(target_dir, name)):
                existing_names.append(name)

        overwrite = False
        skip_existing = False

        if existing_names:
            # Show a single dialog asking what to do
            if len(existing_names) <= 5:
                names_str = '\n'.join(f'  • {n}' for n in existing_names)
                msg = f'以下项目已存在:\n{names_str}\n\n是否覆盖？'
            else:
                msg = f'{len(existing_names)} 个项目已存在，是否覆盖？'

            answer = messagebox.askyesnocancel(
                '冲突',
                msg + '\n\n"是" = 覆盖全部  |  "否" = 跳过全部  |  "取消" = 放弃复制',
                parent=self.root,
            )
            if answer is None:
                return  # cancelled
            elif answer:
                overwrite = True
            else:
                skip_existing = True

        # ── Copy files & folders ─────────────────────────────────────────

        copied = 0
        skipped = 0
        failed = 0

        total = len(files)
        for i, src in enumerate(files, 1):
            name = os.path.basename(src)
            dst = os.path.join(target_dir, name)

            # Skip if target exists and user chose to skip
            if skip_existing and os.path.exists(dst):
                skipped += 1
                continue

            # Update status bar
            self.status_label.config(text=f'正在复制... {i}/{total}')
            self.root.update_idletasks()

            try:
                if os.path.isdir(src):
                    # Remove existing target before copytree if overwriting
                    if overwrite and os.path.exists(dst):
                        shutil.rmtree(dst)
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
                copied += 1
            except (OSError, shutil.SameFileError, PermissionError):
                failed += 1

        # ── Show summary ─────────────────────────────────────────────────

        parts = [f'成功 {copied} 个']
        if skipped:
            parts.append(f'跳过 {skipped} 个')
        if failed:
            parts.append(f'失败 {failed} 个')
        summary = '，'.join(parts)

        messagebox.showinfo(
            '复制完成',
            f'{summary}\n\n目标: {target_dir}',
            parent=self.root,
        )

        # ── Restore status bar ───────────────────────────────────────────

        base = self.config.get('base_directory', '')
        if self._browsing_path:
            self.status_label.config(text=f'浏览: {self._browsing_path}')
        elif base:
            self.status_label.config(text=f'{len(self.projects)} 个项目 | {base}')
        else:
            self.status_label.config(text='就绪')

        # ── Refresh the view if needed ───────────────────────────────────

        if self._view_mode == 'directory' and self._browsing_path:
            # Refresh the directory listing to show newly copied files
            self._show_directory(self._browsing_path)

    # ── New folder ─────────────────────────────────────────────────────────

    def _on_new_folder(self):
        """Handle 'New Folder' button click — prompt for path and create."""
        dialog = tk.Toplevel(self.root)
        dialog.title('新建文件夹')
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        # Center on parent
        dialog.update_idletasks()
        pw = self.root.winfo_width()
        ph = self.root.winfo_height()
        px = self.root.winfo_x()
        py = self.root.winfo_y()
        dw, dh = 520, 120
        x = px + (pw - dw) // 2
        y = py + (ph - dh) // 2
        dialog.geometry(f'{dw}x{dh}+{x}+{y}')

        frame = ttk.Frame(dialog, padding=(16, 16, 16, 8))
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            frame, text='请输入要创建的文件夹完整路径:',
            font=('Segoe UI', 10),
        ).pack(anchor='w')

        entry_frame = ttk.Frame(frame)
        entry_frame.pack(fill=tk.X, pady=(8, 12))

        path_var = tk.StringVar()
        path_entry = ttk.Entry(
            entry_frame, textvariable=path_var, font=('Segoe UI', 10),
        )
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        def browse():
            from tkinter import filedialog
            result = filedialog.askdirectory(
                parent=dialog, title='选择父文件夹',
            )
            if result:
                path_var.set(result + '/')
            path_entry.focus_set()

        browse_btn = ttk.Button(entry_frame, text='浏览...', command=browse)
        browse_btn.pack(side=tk.LEFT, padx=(8, 0))

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)

        def on_ok():
            path = path_var.get().strip()
            if not path:
                return
            try:
                os.makedirs(path, exist_ok=True)
                dialog.destroy()
                messagebox.showinfo(
                    '成功', f'文件夹已创建:\n{path}', parent=self.root,
                )
                # Refresh if inside the base directory
                base_dir = self.config.get('base_directory', '')
                if base_dir and path.startswith(base_dir):
                    self.refresh()
            except OSError as e:
                show_error(dialog, '创建失败', f'无法创建文件夹:\n{e}')

        ttk.Button(btn_frame, text='确定', command=on_ok).pack(
            side=tk.RIGHT, padx=(8, 0),
        )
        ttk.Button(btn_frame, text='取消', command=dialog.destroy).pack(
            side=tk.RIGHT,
        )

        path_entry.focus_set()
        dialog.wait_window()

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
        # Force Tk to fully materialise the window before we install the
        # drop-target subclass — avoids interfering with Tk's own WNDPROC
        # initialisation.
        self.root.update_idletasks()
        self._setup_drop_target()

        # Enable fault handler for C-level crash diagnostics
        try:
            import faulthandler
            _crash_log = os.path.join(
                os.environ.get('TEMP', '.'), 'project_launcher_fault.log'
            )
            faulthandler.enable(file=open(_crash_log, 'a', encoding='utf-8'))
        except Exception:
            pass

        self.root.mainloop()
