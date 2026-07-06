"""Main window for Project Launcher.

Provides the search bar, scrollable project list, status bar, and settings access.
Delegates directory browsing and drag-and-drop to dedicated controller modules.
"""

import ctypes
import os
import shutil
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Any, Optional, Set

from constants import (
    APP_TITLE, MUTEX_NAME, APP_FIND_WINDOW_TITLE,
    DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT,
    SEARCH_PLACEHOLDER, COLOR_BG_WHITE, COLOR_BG_HOVER,
    COLOR_BG_TOOLBAR, COLOR_BG_TOOLBAR_ACTIVE,
    COLOR_TEXT_SECONDARY, COLOR_TEXT_TERTIARY,
    COLOR_TEXT_PLACEHOLDER, FONT_FAMILY,
    FONT_SIZE_STATUS, FONT_SIZE_NORMAL, FONT_SIZE_GEAR,
    FONT_SIZE_EMPTY, FONT_SIZE_SECTION,
    MOUSEWHEEL_DIVISOR,
    VIEW_MODE_PROJECTS, VIEW_MODE_DIRECTORY,
    LEFT_PANEL_DEFAULT_WIDTH, CHART_AREA_DEFAULT_HEIGHT,
)
from scanner import ProjectInfo, scan_async
from launcher import detect_ides, find_ide_by_key, launch, IDEInfo
from config import save_config
from app_paths import get_log_path
from ui.widgets import SearchEntry, ProjectItemFrame, show_error
from ui.settings_dialog import SettingsDialog
from ui.left_panel import LeftPanel
from ui.token_chart import TokenChart
from ui.browse_controller import BrowseController
from ui.drop_handler import DropHandler
from ui.new_folder_dialog import NewFolderDialog
from ui.model_profile_dialog import ModelProfileDialog
from ui.model_profiles_page import ModelProfilesPage
from ui.safety_messages import build_delete_confirmation_message
from claude_settings import (
    apply_profile_to_settings_file,
    get_default_claude_settings_path,
    stop_profile_in_settings_file,
)
from model_profiles import profile_from_summary, profile_to_summary, set_active_profile, toggle_active_profile


class MainWindow:
    """Primary application window."""

    def __init__(self, config: Dict[str, Any], on_config_changed=None):
        self.config = config
        self.on_config_changed = on_config_changed
        self.projects: List[ProjectInfo] = []
        self.current_ide: Optional[IDEInfo] = None
        self.project_frames: List[ProjectItemFrame] = []
        self._scan_thread = None
        self._empty_label: Optional[tk.Label] = None

        # ── Root window ─────────────────────────────────────────────────

        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

        # Restore geometry
        geo = config.get("window_geometry",
                         f"{DEFAULT_WINDOW_WIDTH}x{DEFAULT_WINDOW_HEIGHT}")
        if "+" not in geo:
            self.root.update_idletasks()
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            w, h = DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT
            x = (sw - w) // 2
            y = (sh - h) // 2
            geo = f"{w}x{h}+{x}+{y}"
        self.root.geometry(geo)

        self._set_icon()
        self._set_dpi_aware()
        self._setup_styles()

        # ── Sub-controllers ─────────────────────────────────────────────

        self.browse = BrowseController(self)
        self.drop = DropHandler(self)

        # ── Build layout ────────────────────────────────────────────────
        # Status bar must pack BEFORE main area so it reserves space at bottom

        self._build_toolbar()
        self._build_status_bar()
        self._build_main_area()
        self.left_panel.set_model_settings_callback(self._open_model_profiles_page)
        self.left_panel.set_model_activate_callback(
            lambda index: self._activate_model_profile(index, self.root)
        )
        self.left_panel.set_model_profiles(self.config.get("model_profiles", []))

        # ── Detect IDE ──────────────────────────────────────────────────

        self._detect_ide()

        # ── Bind events ─────────────────────────────────────────────────

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<F5>", lambda e: self.refresh())
        self.root.bind("<Control-r>", lambda e: self.refresh())

        # ── Initial scan ────────────────────────────────────────────────

        self.root.after(100, self.refresh)

    # ── DPI & Styling ───────────────────────────────────────────────────────

    def _set_dpi_aware(self):
        """Enable DPI awareness to prevent blurry text on high-DPI displays."""
        if sys.platform != "win32":
            return
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_AWARE_V2
        except AttributeError:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)  # SYSTEM_AWARE
            except AttributeError:
                try:
                    ctypes.windll.user32.SetProcessDPIAware()
                except AttributeError:
                    pass

    def _set_icon(self):
        """Set the window icon."""
        try:
            if getattr(sys, "frozen", False):
                base = sys._MEIPASS
            else:
                base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            icon_path = os.path.join(base, "icon.png")
            if os.path.exists(icon_path):
                img = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, img)
        except Exception:
            pass  # icon is optional

    def _setup_styles(self):
        """Configure ttk styles."""
        style = ttk.Style()
        try:
            style.theme_use("vista")
        except tk.TclError:
            try:
                style.theme_use("clam")
            except tk.TclError:
                pass

        style.configure("Project.TFrame", background=COLOR_BG_WHITE)
        style.configure("ProjectHover.TFrame", background=COLOR_BG_HOVER)
        style.configure("LeftPanel.TFrame", background="#f8f8f8")
        style.configure("Accent.TButton", font=(FONT_FAMILY, FONT_SIZE_STATUS))
        style.configure("Gear.TButton", font=(FONT_FAMILY, FONT_SIZE_GEAR), padding=(4, 2))

    # ── Layout builders ─────────────────────────────────────────────────────

    def _build_toolbar(self):
        """Build the search bar + settings gear + new-folder + refresh."""
        toolbar = ttk.Frame(self.root, padding=(10, 10, 10, 6))
        toolbar.pack(fill=tk.X)

        # Settings gear
        gear_btn = tk.Button(
            toolbar, text="⚙", font=(FONT_FAMILY, FONT_SIZE_GEAR),
            bg=COLOR_BG_TOOLBAR, bd=0, cursor="hand2",
            activebackground=COLOR_BG_TOOLBAR_ACTIVE,
            command=self._open_settings,
        )
        gear_btn.pack(side=tk.LEFT, padx=(0, 8))

        # New folder
        new_folder_btn = tk.Button(
            toolbar, text="📁 新建文件夹",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            bg=COLOR_BG_TOOLBAR, bd=0, cursor="hand2",
            activebackground=COLOR_BG_TOOLBAR_ACTIVE,
            command=self._on_new_folder,
        )
        new_folder_btn.pack(side=tk.LEFT, padx=(0, 8))

        # Search
        self.search_entry = SearchEntry(
            toolbar, placeholder=SEARCH_PLACEHOLDER,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
        )
        self.search_entry.set_callback(self._on_search)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)

        # Refresh
        refresh_btn = tk.Button(
            toolbar, text="↻", font=(FONT_FAMILY, FONT_SIZE_GEAR),
            bg=COLOR_BG_TOOLBAR, bd=0, cursor="hand2",
            activebackground=COLOR_BG_TOOLBAR_ACTIVE,
            command=self.refresh,
        )
        refresh_btn.pack(side=tk.LEFT, padx=(8, 0))

    def _build_main_area(self):
        """Build the main area: left panel | right (chart top + list bottom)."""
        # ── Horizontal split: left panel | right area ───────────────────
        self._main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self._main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 6))

        # Left panel
        self.left_panel = LeftPanel(self._main_pane)
        self._main_pane.add(self.left_panel, weight=0)

        # Right vertical split: chart top | list bottom
        self._right_pane = ttk.PanedWindow(self._main_pane, orient=tk.VERTICAL)
        self._main_pane.add(self._right_pane, weight=1)

        # Chart area (top-right)
        self._chart_frame = self._build_chart_area(self._right_pane)
        self._right_pane.add(self._chart_frame, weight=0)

        # Project list area (bottom-right)
        list_container = self._build_project_list_area(self._right_pane)
        self._right_pane.add(list_container, weight=1)

        # Defer sash positioning until window manager has fully mapped
        # the window.  Without this, weight=0 panes collapse to 1 px
        # when a saved window_geometry is restored from config.
        self.root.after_idle(self._apply_sash_positions)

    def _build_chart_area(self, parent):
        """Build the token chart area (top-right)."""
        self.token_chart = TokenChart(parent)
        return self.token_chart

    def _apply_sash_positions(self):
        """Set sash positions after window manager has fully mapped the window.

        Called via root.after() to defer until after the geometry restore
        (from saved window_geometry config) has been processed.  Without this
        deferral, weight=0 panes collapse to 1 px on large restored windows.
        """
        try:
            self._main_pane.sashpos(0, LEFT_PANEL_DEFAULT_WIDTH)
            self._right_pane.sashpos(0, CHART_AREA_DEFAULT_HEIGHT)
        except tk.TclError:
            pass  # widget destroyed before callback fired

    def _build_project_list_area(self, parent):
        """Build the scrollable project list area (bottom-right)."""
        list_container = ttk.Frame(parent)

        self.list_canvas = tk.Canvas(
            list_container, bg=COLOR_BG_WHITE, highlightthickness=0,
        )
        self.list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(
            list_container, orient=tk.VERTICAL, command=self.list_canvas.yview,
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.list_canvas.configure(yscrollcommand=scrollbar.set)

        self.list_frame = ttk.Frame(self.list_canvas, style="Project.TFrame")
        self.list_frame_id = self.list_canvas.create_window(
            (0, 0), window=self.list_frame, anchor="nw", tags="list_frame",
        )

        self.list_canvas.bind("<Configure>", self._on_canvas_configure)
        self.list_frame.bind("<Configure>", self._on_frame_configure)
        self.list_canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.list_canvas.bind("<Enter>", self._on_canvas_enter)
        self.list_canvas.bind("<Leave>", self._on_canvas_leave)

        return list_container

    def _build_status_bar(self):
        """Build the status bar at the bottom."""
        status_frame = ttk.Frame(self.root, padding=(12, 4))
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        ttk.Separator(status_frame, orient="horizontal").pack(fill=tk.X)

        label_frame = ttk.Frame(status_frame, padding=(0, 4, 0, 0))
        label_frame.pack(fill=tk.X)

        self.status_label = tk.Label(
            label_frame, text="就绪",
            font=(FONT_FAMILY, FONT_SIZE_STATUS),
            fg=COLOR_TEXT_SECONDARY, bg=self.root.cget("bg"), anchor="w",
        )
        self.status_label.pack(side=tk.LEFT)

        self.ide_label = tk.Label(
            label_frame, text="",
            font=(FONT_FAMILY, FONT_SIZE_STATUS),
            fg=COLOR_TEXT_TERTIARY, bg=self.root.cget("bg"), anchor="e",
        )
        self.ide_label.pack(side=tk.RIGHT)

    # ── Canvas/scroll handling ──────────────────────────────────────────────

    def _on_canvas_configure(self, event):
        self.list_canvas.itemconfig(self.list_frame_id, width=event.width)

    def _on_frame_configure(self, event):
        self.list_canvas.configure(scrollregion=self.list_canvas.bbox("all"))

    def _on_mousewheel(self, event):
        self.list_canvas.yview_scroll(-1 * (event.delta // MOUSEWHEEL_DIVISOR), "units")

    def _on_canvas_enter(self, event):
        self.root.bind("<MouseWheel>", self._on_mousewheel_redirect, add="+")

    def _on_canvas_leave(self, event):
        self.root.unbind("<MouseWheel>")

    def _on_mousewheel_redirect(self, event):
        self.list_canvas.yview_scroll(-1 * (event.delta // MOUSEWHEEL_DIVISOR), "units")

    # ── IDE detection ───────────────────────────────────────────────────────

    def _detect_ide(self):
        """Detect the current IDE based on config."""
        ide_key = self.config.get("selected_ide", "auto")
        custom_path = self.config.get("ide_custom_path", "")

        if ide_key == "auto":
            ides = detect_ides()
            for ide in ides:
                if ide.key != "explorer":
                    self.current_ide = ide
                    break
            else:
                self.current_ide = IDEInfo("explorer", "文件资源管理器", "")
        else:
            self.current_ide = find_ide_by_key(ide_key, custom_path)
            if self.current_ide is None:
                self.current_ide = IDEInfo("explorer", "文件资源管理器", "")
                self.ide_label.config(text="未找到 IDE — 使用文件资源管理器")
                return

        if self.current_ide:
            self.ide_label.config(text=self.current_ide.display_name)

    # ── Project scanning ────────────────────────────────────────────────────

    def refresh(self):
        """Re-scan the base directory and rebuild the project list."""
        self.browse.reset()
        self._clear_all_frames()

        base_dir = self.config.get("base_directory", "")
        if not base_dir:
            self._show_empty("未设置基础目录。\n点击 ⚙ 齿轮图标进行配置。")
            self.status_label.config(text="未配置基础目录")
            return

        excluded = set(self.config.get("excluded_dirs", []))
        sort_recent = self.config.get("sort_recent_first", True)

        self._set_scanning(True)

        def on_callback(phase, data):
            self.root.after(0, lambda: self._handle_scan_callback(phase, data))

        self._scan_thread = scan_async(base_dir, excluded, on_callback, sort_recent)

    def _set_scanning(self, scanning: bool):
        if scanning:
            self.status_label.config(text="正在扫描...")

    def _handle_scan_callback(self, phase: str, data: dict):
        """Handle scanner callbacks on the main thread."""
        if phase == "progress":
            current = data.get("current", 0)
            total = data.get("total", 0)
            self.status_label.config(text=f"正在扫描... {current}/{total}")

        elif phase == "error":
            msg = data.get("message", "未知错误")
            show_error(self.root, "扫描错误", msg)
            self.status_label.config(text="扫描失败")
            self._show_empty(f'无法访问:\n{self.config.get("base_directory", "")}')

        elif phase == "complete":
            self.projects = data.get("projects", [])
            errors = data.get("errors", [])
            skipped = data.get("skipped", 0)
            self._rebuild_list()

            parts = [f"{len(self.projects)} 个项目"]
            if skipped:
                parts.append(f"{skipped} 个已跳过")
            base = self.config.get("base_directory", "")
            parts.append(f"| {base}")
            self.status_label.config(text="  ".join(parts))

            if errors:
                short = errors[0][:40] + ("..." if len(errors[0]) > 40 else "")
                self.ide_label.config(text=f"⚠ {short}")

    # ── Project list display ────────────────────────────────────────────────

    def _rebuild_list(self, filter_query: str = ""):
        """Rebuild the visible project list, optionally filtered."""
        self.browse.reset()
        self._clear_all_frames()

        query = filter_query.lower().strip()
        if query:
            visible = [p for p in self.projects if query in p.name.lower()]
        else:
            visible = self.projects

        if not visible:
            msg = (
                f'未找到匹配 "{filter_query}" 的项目'
                if filter_query
                else "未找到项目。\n点击 ⚙ 齿轮图标更改目录。"
            )
            self._show_empty(msg)
            return

        self._clear_empty()

        for project in visible:
            frame = ProjectItemFrame(
                self.list_frame, project,
                on_enter=self._on_enter_project,
                on_launch_ide=self._on_launch_ide,
                on_delete=self._on_delete_project,
            )
            frame.pack(fill=tk.X)
            self.project_frames.append(frame)

        self.list_canvas.yview_moveto(0)

        if query:
            self.status_label.config(
                text=f'{len(visible)} / {len(self.projects)} 个项目 | {self.config.get("base_directory", "")}'
            )

    def _show_empty(self, message: str):
        """Show the empty-state message."""
        self._clear_empty()
        self._empty_label = tk.Label(
            self.list_frame, text=message,
            font=(FONT_FAMILY, FONT_SIZE_EMPTY),
            fg=COLOR_TEXT_PLACEHOLDER, bg=COLOR_BG_WHITE,
            justify=tk.CENTER,
        )
        self._empty_label.pack(expand=True, fill=tk.BOTH, pady=80)

    def _clear_empty(self):
        """Remove the empty-state label if present."""
        if self._empty_label is not None:
            self._empty_label.destroy()
            self._empty_label = None

    # ── Actions ─────────────────────────────────────────────────────────────

    def _on_search(self, query: str):
        """Handle search query changes (project list view only)."""
        if self.browse.is_active:
            return
        self._rebuild_list(filter_query=query)

    def _on_enter_project(self, project: ProjectInfo):
        """Handle double-click to browse project directory contents."""
        self.browse.enter(project.path)

    def _on_launch_ide(self, project: ProjectInfo):
        """Handle 'Open with IDE' action — launch project in the bound IDE."""
        self.launch_ide_for_path(project.path)

        # Update last_opened timestamp
        last_opened = self.config.setdefault("last_opened", {})
        from datetime import datetime
        last_opened[project.path] = datetime.now().isoformat()
        save_config(self.config)

    def launch_ide_for_path(self, path: str):
        """Launch the bound IDE for a given path (used by browse controller)."""
        if not self.current_ide:
            self.current_ide = IDEInfo("explorer", "文件资源管理器", "")

        success = launch(path, self.current_ide)

        if success:
            self.status_label.config(text=f"已打开: {path}")
            return

        if not os.path.isdir(path):
            show_error(
                self.root, "路径不存在",
                f"目录已不存在:\n{path}\n\n正在刷新列表...",
            )
            self.refresh()
            return

        ide_name = self.current_ide.display_name if self.current_ide else "绑定 IDE"
        show_error(
            self.root,
            "无法打开项目",
            f"无法使用 {ide_name} 打开项目，也无法回退到文件资源管理器:\n{path}",
        )
        self.status_label.config(text=f"打开失败: {path}")

    def _on_delete_project(self, project: ProjectInfo):
        """Handle 'Delete Project' action — remove the project directory."""
        if not os.path.isdir(project.path):
            show_error(
                self.root, "项目不存在",
                f"项目目录已不存在:\n{project.path}\n\n正在刷新列表...",
            )
            self.refresh()
            return

        confirmed = messagebox.askyesno(
            "确认删除",
            build_delete_confirmation_message("项目", project.name, project.path),
            parent=self.root,
        )
        if not confirmed:
            return

        try:
            shutil.rmtree(project.path)
        except OSError as e:
            show_error(
                self.root, "删除失败",
                f"无法删除项目:\n{project.path}\n\n{e}",
            )
            return

        # Remove from last_opened tracking
        last_opened = self.config.get("last_opened", {})
        if project.path in last_opened:
            del last_opened[project.path]
            save_config(self.config)

        self.status_label.config(text=f"已删除: {project.name}")
        self.refresh()

    # ── New folder ─────────────────────────────────────────────────────────

    def _on_new_folder(self):
        """Handle 'New Folder' button — delegate to NewFolderDialog.
        Defaults the path to the current browse directory, or the base directory
        in project-list view."""
        default_path = ""
        if self.browse.is_active and self.browse.current_path:
            default_path = self.browse.current_path + "/"
        else:
            base_dir = self.config.get("base_directory", "")
            if base_dir:
                default_path = base_dir + "/"

        def on_created(path: str):
            base_dir = self.config.get("base_directory", "")
            if base_dir and path.startswith(base_dir):
                self.refresh()

        NewFolderDialog(self.root, on_created=on_created, default_path=default_path)

    def _model_profiles(self) -> List[Dict[str, Any]]:
        return self.config.setdefault("model_profiles", [])

    def _save_model_profiles(self) -> List[Dict[str, Any]]:
        profiles = self._model_profiles()
        save_config(self.config)
        self.left_panel.set_model_profiles(profiles)
        return profiles

    def _open_model_profiles_page(self):
        """Open the first-level model profile management page."""
        ModelProfilesPage(
            self.root,
            self._model_profiles(),
            on_add=self._add_model_profile,
            on_edit=self._edit_model_profile,
            on_delete=self._delete_model_profile,
        )

    def _add_model_profile(self, parent) -> List[Dict[str, Any]]:
        dialog = ModelProfileDialog(parent)
        if dialog.result is None:
            return self._model_profiles()

        profiles = self._model_profiles()
        profiles.append(profile_to_summary(dialog.result))
        self.status_label.config(text=f"已保存模型配置: {dialog.result.name}")
        return self._save_model_profiles()

    def _edit_model_profile(self, index: int, parent) -> List[Dict[str, Any]]:
        profiles = self._model_profiles()
        if index < 0 or index >= len(profiles):
            return profiles

        previous = profiles[index]
        dialog = ModelProfileDialog(parent, profile_from_summary(previous))
        if dialog.result is None:
            return profiles

        summary = profile_to_summary(dialog.result)
        summary["is_active"] = bool(previous.get("is_active", False))
        profiles[index] = summary
        self.status_label.config(text=f"已更新模型配置: {dialog.result.name}")
        return self._save_model_profiles()

    def _delete_model_profile(self, index: int, parent) -> List[Dict[str, Any]]:
        profiles = self._model_profiles()
        if index < 0 or index >= len(profiles):
            return profiles

        name = str(profiles[index].get("name", ""))
        del profiles[index]
        self.status_label.config(text=f"已删除模型配置: {name}")
        return self._save_model_profiles()

    # ── Settings ────────────────────────────────────────────────────────────

    def _activate_model_profile(self, index: int, parent) -> List[Dict[str, Any]]:
        profiles = self._model_profiles()
        if index < 0 or index >= len(profiles):
            return profiles

        was_active = bool(profiles[index].get("is_active", False))
        name = str(profiles[index].get("name", ""))
        settings_path = get_default_claude_settings_path()

        try:
            if was_active:
                stop_profile_in_settings_file(settings_path)
                toggle_active_profile(profiles, index)
                self.status_label.config(text=f"已停止模型配置: {name}")
            else:
                profile = profile_from_summary(profiles[index])
                if not profile.api_key.strip():
                    messagebox.showerror(
                        "无法启动模型配置",
                        "该模型配置缺少 API Key，请先编辑模型配置并保存 API Key。",
                        parent=parent,
                    )
                    return profiles
                apply_profile_to_settings_file(settings_path, profile)
                set_active_profile(profiles, index)
                self.status_label.config(text=f"已启动模型配置: {name}")
        except (OSError, ValueError) as exc:
            messagebox.showerror(
                "无法写入 Claude Code 配置",
                f"写入 {settings_path} 失败：\n{exc}",
                parent=parent,
            )
            return profiles

        return self._save_model_profiles()

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

    # ── Shared helpers (used by sub-controllers) ────────────────────────────

    def _clear_all_frames(self):
        """Clear all item frames (both project and directory entries)."""
        for frame in self.project_frames:
            frame.destroy()
        self.project_frames.clear()
        for frame in self.browse._dir_frames:
            frame.destroy()
        self.browse._dir_frames.clear()

    # ── Lifecycle ───────────────────────────────────────────────────────────

    def _on_close(self):
        """Handle window close — save config and exit."""
        geo = self.root.geometry()
        self.config["window_geometry"] = geo
        save_config(self.config)
        self.root.destroy()

    def run(self):
        """Start the Tkinter main loop."""
        self.root.update_idletasks()
        self.drop.setup()

        # Enable fault handler for C-level crash diagnostics
        try:
            import faulthandler
            faulthandler.enable(file=open(get_log_path("fault.log"), "a", encoding="utf-8"))
        except Exception:
            pass

        self.root.mainloop()
