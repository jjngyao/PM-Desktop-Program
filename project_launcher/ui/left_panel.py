"""Left-side panel for Project Launcher.

Contains two sections: model switching and Skills management.
Each section is a collapsible area with a header and content frame.
The entire panel is scrollable via an outer Canvas.
"""

import tkinter as tk
from tkinter import ttk
from typing import List, Dict, Any, Optional, Callable

from constants import (
    COLOR_BG_LEFT_PANEL, COLOR_SECTION_HEADER, COLOR_SECTION_BORDER,
    COLOR_BG_WHITE, COLOR_BG_HOVER, COLOR_TEXT_PRIMARY, COLOR_TEXT_SECONDARY,
    COLOR_TEXT_TERTIARY, COLOR_TEXT_PLACEHOLDER,
    COLOR_MODEL_ACTIVE_BG, COLOR_MODEL_INACTIVE_BG, COLOR_MODEL_ROLE_TAG,
    COLOR_GIT_GREEN,
    FONT_FAMILY, FONT_SIZE_SECTION, FONT_SIZE_SMALL, FONT_SIZE_NORMAL,
    FONT_SIZE_STATUS,
    LEFT_PANEL_DEFAULT_WIDTH, LEFT_PANEL_MIN_WIDTH,
    SKILLS_SEARCH_PLACEHOLDER, SKILLS_COUNT_FORMAT, SKILLS_HINT_TEXT,
    MODEL_HINT_FORMAT, MODEL_NO_CONFIG_HINT,
    MOUSEWHEEL_DIVISOR,
)


# ── Section Frame ────────────────────────────────────────────────────────────

class SectionFrame(ttk.Frame):
    """A labelled section with a header, separator, and content area."""

    def __init__(self, parent, title: str, icon: str = "", **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(style="LeftPanel.TFrame")

        # ── Header ──────────────────────────────────────────────────────
        header_frame = tk.Frame(self, bg=COLOR_BG_LEFT_PANEL, cursor="arrow")
        header_frame.pack(fill=tk.X)

        header_text = f"{icon}  {title}".strip()
        self._header_label = tk.Label(
            header_frame, text=header_text,
            font=(FONT_FAMILY, FONT_SIZE_SECTION, "bold"),
            fg=COLOR_SECTION_HEADER, bg=COLOR_BG_LEFT_PANEL,
            anchor="w",
        )
        self._header_label.pack(side=tk.LEFT, fill=tk.X, padx=12, pady=(10, 4))

        # ── Separator ───────────────────────────────────────────────────
        sep = ttk.Separator(self, orient="horizontal")
        sep.pack(fill=tk.X, padx=8)

        # ── Content ─────────────────────────────────────────────────────
        self.content_frame = tk.Frame(self, bg=COLOR_BG_LEFT_PANEL)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # ── Empty placeholder (hidden when content exists) ──────────────
        self._placeholder_var = tk.StringVar()
        self._placeholder = tk.Label(
            self.content_frame, textvariable=self._placeholder_var,
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            fg=COLOR_TEXT_TERTIARY, bg=COLOR_BG_LEFT_PANEL,
            anchor="w", justify=tk.LEFT,
        )

    def set_placeholder(self, text: str):
        """Show placeholder text when section has no content."""
        self._placeholder_var.set(text)
        self._placeholder.pack(fill=tk.X, padx=4)

    def clear_content(self):
        """Remove all widgets from the content area except the placeholder."""
        for child in self.content_frame.winfo_children():
            if child is not self._placeholder:
                child.destroy()

    def hide_placeholder(self):
        """Hide the placeholder label."""
        self._placeholder.pack_forget()


# ── Model Row ────────────────────────────────────────────────────────────────

class ModelRow(tk.Frame):
    """A single selectable model row (radio-button style)."""

    def __init__(self, parent, model: dict, is_active: bool = False,
                 on_select: Optional[Callable] = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.model = model
        self._is_active = is_active
        self._on_select = on_select

        self._build()
        self._bind_events()
        self._update_style()

    def _build(self):
        """Build the row layout: indicator + name + role tag."""
        self.configure(bg=COLOR_BG_LEFT_PANEL, cursor="hand2")

        # Radio indicator
        self._indicator = tk.Label(
            self, text="○", font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            bg=COLOR_BG_LEFT_PANEL, fg=COLOR_TEXT_TERTIARY,
            cursor="hand2",
        )
        self._indicator.pack(side=tk.LEFT, padx=(8, 6), pady=5)

        # Model name
        self._name_label = tk.Label(
            self, text=self.model.get("name", ""),
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            fg=COLOR_TEXT_PRIMARY, bg=COLOR_BG_LEFT_PANEL,
            anchor="w", cursor="hand2",
        )
        self._name_label.pack(side=tk.LEFT, pady=5)

        # Role tag
        role = self.model.get("role", "")
        if role:
            self._role_label = tk.Label(
                self, text=role,
                font=(FONT_FAMILY, FONT_SIZE_SMALL),
                fg=COLOR_MODEL_ROLE_TAG, bg=COLOR_BG_LEFT_PANEL,
                cursor="hand2", padx=6,
            )
            self._role_label.pack(side=tk.RIGHT, padx=(0, 8), pady=5)

        # Desc tooltip (shown as subtitle)
        desc = self.model.get("desc", "")
        if desc:
            self._desc_label = tk.Label(
                self, text=f"· {desc}",
                font=(FONT_FAMILY, FONT_SIZE_SMALL),
                fg=COLOR_TEXT_TERTIARY, bg=COLOR_BG_LEFT_PANEL,
                cursor="hand2",
            )
            self._desc_label.pack(side=tk.RIGHT, pady=5)

    def _bind_events(self):
        """Bind click events for selection."""
        widgets = [self, self._indicator, self._name_label]
        if hasattr(self, '_role_label'):
            widgets.append(self._role_label)
        if hasattr(self, '_desc_label'):
            widgets.append(self._desc_label)
        for w in widgets:
            w.bind("<Button-1>", self._on_click)

    def _on_click(self, event):
        """Handle click — notify parent to switch selection."""
        if self._on_select:
            self._on_select(self.model.get("name", ""))

    def set_active(self, active: bool):
        """Update the active state and restyle."""
        self._is_active = active
        self._update_style()

    def _update_style(self):
        """Apply styling based on active state."""
        if self._is_active:
            bg = COLOR_MODEL_ACTIVE_BG
            self._indicator.configure(text="●", bg=bg, fg="#1976d2")
        else:
            bg = COLOR_BG_LEFT_PANEL
            self._indicator.configure(text="○", bg=bg, fg=COLOR_TEXT_TERTIARY)

        self.configure(bg=bg)
        self._name_label.configure(bg=bg)
        if hasattr(self, '_role_label'):
            self._role_label.configure(bg=bg)
        if hasattr(self, '_desc_label'):
            self._desc_label.configure(bg=bg)


# ── Left Panel ───────────────────────────────────────────────────────────────

class LeftPanel(ttk.Frame):
    """Left-side panel containing model switch and Skills management sections.

    Public API (for future phases):
        set_model_list(models: list)  — populate model switching area
        set_skills_list(skills: list) — populate Skills management area
        set_active_model(name: str)   — highlight the active model
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(style="LeftPanel.TFrame")

        self._model_rows: List[ModelRow] = []
        self._skill_vars: Dict[str, tk.BooleanVar] = {}
        self._active_model_name: str = ""
        self._model_select_callback: Optional[Callable] = None
        self._model_settings_callback: Optional[Callable] = None
        self._model_activate_callback: Optional[Callable] = None

        # ── Scrollable canvas ───────────────────────────────────────────
        self._canvas = tk.Canvas(
            self, bg=COLOR_BG_LEFT_PANEL, highlightthickness=0,
            width=LEFT_PANEL_DEFAULT_WIDTH,
        )
        self._scrollbar = ttk.Scrollbar(
            self, orient=tk.VERTICAL, command=self._canvas.yview,
        )
        self._scroll_frame = tk.Frame(self._canvas, bg=COLOR_BG_LEFT_PANEL)

        self._scroll_frame.bind("<Configure>", self._on_scroll_frame_configure)
        self._canvas.create_window(
            (0, 0), window=self._scroll_frame, anchor="nw", tags="scroll_frame",
        )
        self._canvas.configure(yscrollcommand=self._scrollbar.set)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind("<MouseWheel>", self._on_mousewheel)

        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # ── Sections ────────────────────────────────────────────────────
        self.model_section = SectionFrame(
            self._scroll_frame, title="模型切换", icon="🔄",
        )
        self.model_section.pack(fill=tk.X, pady=(0, 8))

        self.skills_section = SectionFrame(
            self._scroll_frame, title="Skills 管理", icon="🧩",
        )
        self.skills_section.pack(fill=tk.X)

        # ── Build initial UI with default data ──────────────────────────
        self._build_model_profiles_section([])
        self._build_skills_section(self._default_skills())

    # ── Scroll handling ─────────────────────────────────────────────────

    def _on_scroll_frame_configure(self, event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        region = self._canvas.bbox("all")
        if region:
            _, _, _, h = region
            canvas_h = self._canvas.winfo_height()
            if h > canvas_h:
                self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            else:
                self._scrollbar.pack_forget()

    def _on_canvas_configure(self, event):
        self._canvas.itemconfig("scroll_frame", width=event.width)

    def _on_mousewheel(self, event):
        self._canvas.yview_scroll(-1 * (event.delta // MOUSEWHEEL_DIVISOR), "units")

    # ── Model section ───────────────────────────────────────────────────

    def _build_model_profiles_section(self, profiles: list):
        """Build the model profile list: name + active status indicator."""
        section = self.model_section
        section.hide_placeholder()
        section.clear_content()
        self._model_rows.clear()

        if not profiles:
            empty = tk.Label(
                section.content_frame,
                text="暂无模型配置",
                font=(FONT_FAMILY, FONT_SIZE_NORMAL),
                fg=COLOR_TEXT_TERTIARY,
                bg=COLOR_BG_LEFT_PANEL,
                anchor="w",
            )
            empty.pack(fill=tk.X, padx=8, pady=(6, 8))
        else:
            for index, profile in enumerate(profiles):
                row = tk.Frame(section.content_frame, bg=COLOR_BG_LEFT_PANEL)
                row.pack(fill=tk.X, padx=8, pady=4)
                name = tk.Label(
                    row,
                    text=profile.get("name", "未命名配置"),
                    font=(FONT_FAMILY, FONT_SIZE_NORMAL),
                    fg=COLOR_TEXT_PRIMARY,
                    bg=COLOR_BG_LEFT_PANEL,
                    anchor="w",
                )
                name.pack(side=tk.LEFT, fill=tk.X, expand=True)
                active = bool(profile.get("is_active", False))
                status = tk.Label(
                    row,
                    text="●",
                    font=(FONT_FAMILY, FONT_SIZE_NORMAL),
                    fg=COLOR_GIT_GREEN if active else "#d1242f",
                    bg=COLOR_BG_LEFT_PANEL,
                    anchor="e",
                )
                status.pack(side=tk.RIGHT)
                activate_btn = tk.Button(
                    row,
                    text="Ⅱ" if active else "▶",
                    font=(FONT_FAMILY, FONT_SIZE_STATUS),
                    fg=COLOR_TEXT_SECONDARY,
                    bg=COLOR_BG_LEFT_PANEL,
                    activebackground=COLOR_BG_HOVER,
                    bd=0,
                    cursor="hand2",
                    command=lambda idx=index: self._on_model_activate(idx),
                )
                activate_btn.pack(side=tk.RIGHT, padx=(0, 6))

        settings_btn = tk.Button(
            section.content_frame,
            text="模型配置...",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            bg=COLOR_BG_WHITE,
            bd=0,
            cursor="hand2",
            command=self._on_model_settings,
        )
        settings_btn.pack(fill=tk.X, padx=8, pady=(8, 4), ipady=4)

    def _build_model_section(self, models: list, active_name: str = ""):
        """Build the model switching radio-button list.

        Args:
            models: list of dicts with keys: name, role, desc
            active_name: name of the currently active model
        """
        section = self.model_section
        section.hide_placeholder()
        section.clear_content()
        self._model_rows.clear()

        self._active_model_name = active_name

        for model in models:
            is_active = (model.get("name", "") == active_name)
            row = ModelRow(
                section.content_frame, model,
                is_active=is_active,
                on_select=self._on_model_select,
            )
            row.pack(fill=tk.X)
            self._model_rows.append(row)

        # Hint label at the bottom of model section
        if active_name:
            hint_text = MODEL_HINT_FORMAT.format(active_name)
        else:
            hint_text = MODEL_NO_CONFIG_HINT

        self._model_hint = tk.Label(
            section.content_frame, text=hint_text,
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            fg=COLOR_TEXT_TERTIARY, bg=COLOR_BG_LEFT_PANEL,
            anchor="w", justify=tk.LEFT,
        )
        self._model_hint.pack(fill=tk.X, padx=8, pady=(6, 4))

        settings_btn = tk.Button(
            section.content_frame,
            text="模型配置...",
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            bg=COLOR_BG_WHITE,
            bd=0,
            cursor="hand2",
            command=self._on_model_settings,
        )
        settings_btn.pack(fill=tk.X, padx=8, pady=(4, 4), ipady=4)

    def _on_model_select(self, name: str):
        """Handle model selection — update highlighting and hint."""
        self._active_model_name = name
        for row in self._model_rows:
            row.set_active(row.model.get("name", "") == name)
        hint_text = MODEL_HINT_FORMAT.format(name)
        self._model_hint.configure(text=hint_text)

        if self._model_select_callback:
            self._model_select_callback(name)

    def _on_model_settings(self):
        """Open the model settings page/dialog."""
        if self._model_settings_callback:
            self._model_settings_callback()

    def _on_model_activate(self, index: int):
        """Activate a saved model profile."""
        if self._model_activate_callback:
            self._model_activate_callback(index)

    # ── Skills section ──────────────────────────────────────────────────

    def _build_skills_section(self, skills: list):
        """Build the Skills management area with search, count, and checkbuttons.

        Args:
            skills: list of dicts with keys: name, description, enabled
        """
        section = self.skills_section
        section.hide_placeholder()
        section.clear_content()
        self._skill_vars.clear()

        cf = section.content_frame

        # ── Search entry ────────────────────────────────────────────────
        search_frame = tk.Frame(cf, bg=COLOR_BG_LEFT_PANEL)
        search_frame.pack(fill=tk.X, padx=4, pady=(2, 4))

        self._skills_search_var = tk.StringVar()
        self._skills_search_var.trace_add("write", self._on_skills_search)

        search_entry = tk.Entry(
            search_frame, textvariable=self._skills_search_var,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            fg=COLOR_TEXT_PLACEHOLDER, bg=COLOR_BG_WHITE,
            relief=tk.FLAT, bd=1,
        )
        search_entry.pack(fill=tk.X, ipady=3)
        self._skills_search_entry = search_entry

        # Placeholder behavior
        self._skills_search_placeholder = SKILLS_SEARCH_PLACEHOLDER
        self._skills_search_active = False

        search_entry.insert(0, self._skills_search_placeholder)
        search_entry.bind("<FocusIn>", self._on_search_focus_in)
        search_entry.bind("<FocusOut>", self._on_search_focus_out)

        # ── Count label ────────────────────────────────────────────────
        enabled_count = sum(1 for s in skills if s.get("enabled", True))
        total_count = len(skills)
        count_text = SKILLS_COUNT_FORMAT.format(enabled_count, total_count)

        self._skills_count_label = tk.Label(
            cf, text=count_text,
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            fg=COLOR_TEXT_SECONDARY, bg=COLOR_BG_LEFT_PANEL,
            anchor="w",
        )
        self._skills_count_label.pack(fill=tk.X, padx=4, pady=(0, 4))

        # ── Separator ──────────────────────────────────────────────────
        inner_sep = ttk.Separator(cf, orient="horizontal")
        inner_sep.pack(fill=tk.X, padx=4)

        # ── Skill checkbuttons ─────────────────────────────────────────
        for skill in skills:
            var = tk.BooleanVar(value=skill.get("enabled", True))
            self._skill_vars[skill.get("name", "")] = var

            cb = tk.Checkbutton(
                cf, text=skill.get("name", ""),
                variable=var,
                font=(FONT_FAMILY, FONT_SIZE_NORMAL),
                fg=COLOR_TEXT_PRIMARY, bg=COLOR_BG_LEFT_PANEL,
                activebackground=COLOR_BG_LEFT_PANEL,
                selectcolor=COLOR_BG_LEFT_PANEL,
                anchor="w", cursor="hand2",
                command=lambda s=skill, v=var: self._on_skill_toggle(s, v),
            )
            cb.pack(fill=tk.X, padx=4, pady=1)
            setattr(self, f"_skill_cb_{skill.get('name', '')}", cb)

        # ── Hint label ─────────────────────────────────────────────────
        self._skills_hint = tk.Label(
            cf, text=SKILLS_HINT_TEXT,
            font=(FONT_FAMILY, FONT_SIZE_SMALL),
            fg=COLOR_TEXT_TERTIARY, bg=COLOR_BG_LEFT_PANEL,
            anchor="w", justify=tk.LEFT,
        )
        self._skills_hint.pack(fill=tk.X, padx=4, pady=(6, 4))

    def _on_search_focus_in(self, event):
        """Clear search placeholder on focus."""
        if not self._skills_search_active:
            self._skills_search_entry.delete(0, tk.END)
            self._skills_search_entry.configure(fg=COLOR_TEXT_PRIMARY)
            self._skills_search_active = True

    def _on_search_focus_out(self, event):
        """Restore search placeholder if empty."""
        if self._skills_search_active and not self._skills_search_var.get().strip():
            self._skills_search_active = False
            self._skills_search_entry.delete(0, tk.END)
            self._skills_search_entry.insert(0, self._skills_search_placeholder)
            self._skills_search_entry.configure(fg=COLOR_TEXT_PLACEHOLDER)

    def _on_skills_search(self, *args):
        """Filter visible skills based on search query."""
        query = self._skills_search_var.get().strip().lower()
        if not self._skills_search_active:
            return  # placeholder text — don't filter

        for name, var in self._skill_vars.items():
            cb = getattr(self, f"_skill_cb_{name}", None)
            if cb is None:
                continue
            if query == "" or query in name.lower():
                cb.pack(fill=tk.X, padx=4, pady=1)
            else:
                cb.pack_forget()

    def _on_skill_toggle(self, skill: dict, var: tk.BooleanVar):
        """Handle skill enable/disable toggle. (Phase 4 — file move)"""
        # Update count label
        enabled_count = sum(1 for v in self._skill_vars.values() if v.get())
        total_count = len(self._skill_vars)
        count_text = SKILLS_COUNT_FORMAT.format(enabled_count, total_count)
        self._skills_count_label.configure(text=count_text)
        # TODO: Phase 4 — execute skill_manager.enable/disable

    # ── Default data (UI placeholder) ───────────────────────────────────

    @staticmethod
    def _default_skills() -> list:
        """Return a hardcoded skills list for UI scaffolding.

        In Phase 4, this will be replaced by SkillManager.list_all().
        """
        skill_names = [
            "algorithmic-art", "brainstorming", "brand-guidelines",
            "canvas-design", "claude-api", "dispatching-parallel-agents",
            "doc-coauthoring", "docx", "executing-plans",
            "finishing-a-development-branch", "frontend-design",
            "internal-comms", "mcp-builder", "pdf", "pptx",
            "receiving-code-review", "requesting-code-review",
            "skill-creator", "slack-gif-creator",
            "subagent-driven-development", "systematic-debugging",
            "test-driven-development", "theme-factory",
            "using-git-worktrees", "using-superpowers",
            "verification-before-completion", "web-artifacts-builder",
            "webapp-testing", "writing-plans", "writing-skills",
            "xlsx",
        ]
        return [
            {"name": name, "description": "", "enabled": (name != "template")}
            for name in skill_names
        ]

    # ── Public API (for future phases) ──────────────────────────────────

    def set_model_list(self, models: list, active_name: str = ""):
        """Populate the model switching section. (Phase 3)

        Args:
            models: list of dicts with keys: name, role, desc
            active_name: name of the currently active model
        """
        self._build_model_section(models, active_name=active_name)

    def set_model_profiles(self, profiles: list):
        """Populate the model profile section."""
        self._build_model_profiles_section(profiles)

    def set_skills_list(self, skills: list):
        """Populate the Skills management section. (Phase 4)

        Args:
            skills: list of dicts with keys: name, description, enabled
        """
        self._build_skills_section(skills)

    def set_active_model(self, name: str):
        """Highlight the given model as active. (Phase 3)"""
        self._active_model_name = name
        for row in self._model_rows:
            row.set_active(row.model.get("name", "") == name)
        hint_text = MODEL_HINT_FORMAT.format(name) if name else MODEL_NO_CONFIG_HINT
        self._model_hint.configure(text=hint_text)

    def set_model_select_callback(self, callback: Callable):
        """Set callback for model selection changes. (Phase 3)"""
        self._model_select_callback = callback

    def set_model_settings_callback(self, callback: Callable):
        """Set callback for opening the model settings UI."""
        self._model_settings_callback = callback

    def set_model_activate_callback(self, callback: Callable):
        """Set callback for activating a model profile."""
        self._model_activate_callback = callback
