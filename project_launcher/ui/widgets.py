"""Reusable UI widgets for Project Launcher."""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from scanner import ProjectInfo


# ── Search Entry ────────────────────────────────────────────────────────────

class SearchEntry(ttk.Entry):
    """Entry widget with placeholder text and debounced search callback."""

    def __init__(self, parent, placeholder: str = "搜索项目...", **kwargs):
        super().__init__(parent, **kwargs)
        self.placeholder = placeholder
        self._debounce_id: str | None = None
        self._on_search_callback = None
        self._showing_placeholder = False

        self.insert(0, placeholder)
        self._showing_placeholder = True
        self.configure(foreground='gray')

        # Bindings
        self.bind('<FocusIn>', self._on_focus_in)
        self.bind('<FocusOut>', self._on_focus_out)
        self.bind('<KeyRelease>', self._on_key_release)
        self.bind('<Escape>', self._on_escape)
        self.bind('<Control-a>', self._on_select_all)

    def set_callback(self, callback):
        """Set the callback(query: str) to call on search."""
        self._on_search_callback = callback

    def get_query(self) -> str:
        """Return the current search query (empty string if showing placeholder)."""
        if self._showing_placeholder:
            return ''
        return self.get()

    def _on_focus_in(self, event):
        if self._showing_placeholder:
            self.delete(0, tk.END)
            self.configure(foreground='black')
            self._showing_placeholder = False

    def _on_focus_out(self, event):
        if not self.get().strip():
            self.insert(0, self.placeholder)
            self.configure(foreground='gray')
            self._showing_placeholder = True

    def _on_key_release(self, event):
        # Skip debounce for navigation keys
        if event.keysym in ('Up', 'Down', 'Left', 'Right', 'Tab', 'Return',
                            'Shift_L', 'Shift_R', 'Control_L', 'Control_R',
                            'Alt_L', 'Alt_R', 'Escape'):
            return

        if self._debounce_id is not None:
            self.after_cancel(self._debounce_id)
        self._debounce_id = self.after(150, self._fire_callback)

    def _on_escape(self, event):
        self.delete(0, tk.END)
        self._fire_callback()
        self.focus_set()

    def _on_select_all(self, event):
        self.select_range(0, tk.END)
        return 'break'

    def _fire_callback(self):
        if self._on_search_callback:
            self._on_search_callback(self.get_query())


# ── Project Item Frame ──────────────────────────────────────────────────────

class ProjectItemFrame(ttk.Frame):
    """A single project row in the list. Supports double-click to launch."""

    # Colors
    COLOR_GIT = '#2ea043'       # green dot for git repos
    COLOR_DEFAULT = '#58a6ff'   # blue dot for regular projects
    COLOR_HOVER = '#e8e8e8'     # light hover background
    COLOR_BG = '#ffffff'        # normal background

    def __init__(self, parent, project: ProjectInfo, on_enter=None, on_launch_ide=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.project = project
        self.on_enter = on_enter
        self.on_launch_ide = on_launch_ide
        self._hovering = False

        self.configure(style='Project.TFrame', cursor='hand2')

        # Build layout
        self._build()
        self._bind_events()

    def _build(self):
        """Build the widget layout."""
        # Icon dot (colored circle indicator)
        self.icon_label = tk.Label(
            self,
            text='●',
            fg=self.COLOR_GIT if self.project.has_git else self.COLOR_DEFAULT,
            bg=self.COLOR_BG,
            font=('Segoe UI', 14),
        )
        self.icon_label.pack(side=tk.LEFT, padx=(12, 8), pady=8)

        # Text area
        text_frame = tk.Frame(self, bg=self.COLOR_BG, cursor='hand2')
        text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=6)

        self.name_label = tk.Label(
            text_frame,
            text=self.project.name,
            font=('Segoe UI', 11, 'bold'),
            fg='#1e1e1e',
            bg=self.COLOR_BG,
            anchor='w',
            cursor='hand2',
        )
        self.name_label.pack(fill=tk.X)

        self.path_label = tk.Label(
            text_frame,
            text=self.project.path,
            font=('Segoe UI', 8),
            fg='#888888',
            bg=self.COLOR_BG,
            anchor='w',
            cursor='hand2',
        )
        self.path_label.pack(fill=tk.X)

        # Right-side: last modified time
        time_str = self._format_time(self.project.last_modified)
        self.time_label = tk.Label(
            self,
            text=time_str,
            font=('Segoe UI', 9),
            fg='#888888',
            bg=self.COLOR_BG,
            cursor='hand2',
        )
        self.time_label.pack(side=tk.RIGHT, padx=(8, 12), pady=8)

        # Separator line
        sep = ttk.Separator(self, orient='horizontal')
        sep.place(relx=0, rely=0.98, relwidth=1, height=1)

    def _bind_events(self):
        """Bind mouse events for hover and click."""
        all_widgets = [self, self.icon_label, self.name_label, self.path_label, self.time_label]
        # Also find the text_frame
        for child in self.winfo_children():
            if isinstance(child, tk.Frame):
                all_widgets.append(child)

        for w in all_widgets:
            w.bind('<Enter>', self._on_enter)
            w.bind('<Leave>', self._on_leave)
            w.bind('<Double-Button-1>', self._on_double_click)
            w.bind('<Button-3>', self._on_right_click)

        self.bind('<Enter>', self._on_enter)
        self.bind('<Leave>', self._on_leave)
        self.bind('<Double-Button-1>', self._on_double_click)
        self.bind('<Button-3>', self._on_right_click)

    def _format_time(self, timestamp: float) -> str:
        """Format a timestamp as a human-readable relative string."""
        if timestamp == 0.0:
            return ''
        try:
            dt = datetime.fromtimestamp(timestamp)
            now = datetime.now()
            delta = now - dt

            if delta.days == 0:
                if delta.seconds < 60:
                    return '刚刚'
                elif delta.seconds < 3600:
                    return f'{delta.seconds // 60}分钟前'
                else:
                    return f'{delta.seconds // 3600}小时前'
            elif delta.days == 1:
                return '昨天'
            elif delta.days < 7:
                return f'{delta.days}天前'
            elif delta.days < 30:
                return f'{delta.days // 7}周前'
            else:
                return dt.strftime('%Y-%m-%d')
        except (OSError, ValueError):
            return ''

    def _on_enter(self, event):
        if not self._hovering:
            self._hovering = True
            self.configure(style='ProjectHover.TFrame')
            for child in self._all_recolor_targets():
                try:
                    child.configure(bg=self.COLOR_HOVER)
                except tk.TclError:
                    pass

    def _on_leave(self, event):
        if self._hovering:
            self._hovering = False
            self.configure(style='Project.TFrame')
            for child in self._all_recolor_targets():
                try:
                    child.configure(bg=self.COLOR_BG)
                except tk.TclError:
                    pass

    def _all_recolor_targets(self):
        """Yield all widgets whose background should change on hover."""
        yield self.icon_label
        yield self.name_label
        yield self.path_label
        yield self.time_label
        for child in self.winfo_children():
            if isinstance(child, tk.Frame):
                yield child

    def _on_double_click(self, event):
        if self.on_enter:
            self.on_enter(self.project)

    def _on_right_click(self, event):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(
            label='🚀 启动程序',
            command=lambda: self._launch_explorer()
        )
        menu.add_command(
            label='💻 使用绑定 IDE 打开项目',
            command=lambda: self.on_launch_ide(self.project) if self.on_launch_ide else None
        )
        menu.tk_popup(event.x_root, event.y_root)

    def _launch_explorer(self):
        import os
        try:
            os.startfile(self.project.path)
        except OSError:
            pass


# ── Directory Entry Frame ────────────────────────────────────────────────────

class DirectoryEntryFrame(ttk.Frame):
    """A single entry in the directory browser view. Supports double-click to
    navigate into subdirectories."""

    COLOR_DIR = '#58a6ff'
    COLOR_HOVER = '#e8e8e8'
    COLOR_BG = '#ffffff'

    def __init__(self, parent, name: str, path: str, is_dir: bool = False,
                 on_click=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.entry_name = name
        self.entry_path = path
        self.is_dir = is_dir
        self.on_click = on_click
        self._hovering = False

        self.configure(style='Project.TFrame',
                       cursor='hand2' if is_dir else 'arrow')

        # Icon
        icon = '📁' if is_dir else '📄'
        self.icon_label = tk.Label(
            self,
            text=icon,
            font=('Segoe UI', 14),
            bg=self.COLOR_BG,
        )
        self.icon_label.pack(side=tk.LEFT, padx=(12, 8), pady=6)

        # Name
        self.name_label = tk.Label(
            self,
            text=name,
            font=('Segoe UI', 11),
            fg='#1e1e1e',
            bg=self.COLOR_BG,
            anchor='w',
        )
        self.name_label.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, pady=6)

        # Separator
        sep = ttk.Separator(self, orient='horizontal')
        sep.place(relx=0, rely=0.98, relwidth=1, height=1)

        if is_dir:
            self._bind_events()

    def _bind_events(self):
        """Bind hover and click events for directory entries."""
        targets = [self, self.icon_label, self.name_label]
        for w in targets:
            w.bind('<Enter>', self._on_enter)
            w.bind('<Leave>', self._on_leave)
            w.bind('<Double-Button-1>', self._on_double_click)

    def _on_enter(self, event):
        if not self._hovering:
            self._hovering = True
            self.configure(style='ProjectHover.TFrame')
            for child in (self.icon_label, self.name_label):
                try:
                    child.configure(bg=self.COLOR_HOVER)
                except tk.TclError:
                    pass

    def _on_leave(self, event):
        if self._hovering:
            self._hovering = False
            self.configure(style='Project.TFrame')
            for child in (self.icon_label, self.name_label):
                try:
                    child.configure(bg=self.COLOR_BG)
                except tk.TclError:
                    pass

    def _on_double_click(self, event):
        if self.on_click:
            self.on_click(self.entry_path)


# ── helpers ─────────────────────────────────────────────────────────────────

def show_error(parent, title: str, message: str):
    """Show an error dialog."""
    messagebox.showerror(title, message, parent=parent)


def show_info(parent, title: str, message: str):
    """Show an info dialog."""
    messagebox.showinfo(title, message, parent=parent)
