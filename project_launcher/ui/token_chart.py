"""Token consumption trend chart component.

A Canvas-based line chart that displays daily/weekly token usage trends.
UI skeleton only — actual chart drawing is implemented in later phases.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional

from constants import (
    COLOR_BG_WHITE, COLOR_BG_TOOLBAR, COLOR_BG_TOOLBAR_ACTIVE,
    COLOR_TEXT_SECONDARY, COLOR_TEXT_TERTIARY, COLOR_TEXT_PLACEHOLDER,
    COLOR_CHART_BG, COLOR_CHART_TEXT,
    FONT_FAMILY, FONT_SIZE_SECTION, FONT_SIZE_NORMAL, FONT_SIZE_STATUS,
    CHART_VIEW_DAILY, CHART_VIEW_WEEKLY, CHART_EMPTY_TEXT,
    CHART_AREA_DEFAULT_HEIGHT,
)


class TokenChart(tk.Frame):
    """Token consumption trend chart with day/week toggle.

    Public API (for future phases):
        set_data(points: list)  — update chart data and redraw
        set_view(view: str)     — switch between daily/weekly view
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(bg=COLOR_BG_WHITE, bd=1, relief=tk.GROOVE)

        self._current_view = CHART_VIEW_DAILY
        self._data_points: list = []

        self._build_title_bar()
        self._build_canvas()
        self._build_empty_state()

    # ── Title bar ─────────────────────────────────────────────────────────

    def _build_title_bar(self):
        """Build the title bar with view toggle buttons."""
        title_frame = tk.Frame(self, bg=COLOR_BG_WHITE)
        title_frame.pack(fill=tk.X, padx=12, pady=(8, 4))

        # Title
        title_label = tk.Label(
            title_frame, text="📊  Token 消耗趋势",
            font=(FONT_FAMILY, FONT_SIZE_SECTION, "bold"),
            fg=COLOR_TEXT_SECONDARY, bg=COLOR_BG_WHITE,
            anchor="w",
        )
        title_label.pack(side=tk.LEFT)

        # View toggle buttons container
        toggle_frame = tk.Frame(title_frame, bg=COLOR_BG_WHITE)
        toggle_frame.pack(side=tk.RIGHT)

        self._btn_daily = tk.Button(
            toggle_frame, text="按日",
            font=(FONT_FAMILY, FONT_SIZE_STATUS),
            bg=COLOR_BG_TOOLBAR_ACTIVE, bd=0, cursor="hand2",
            activebackground=COLOR_BG_TOOLBAR_ACTIVE,
            padx=8, pady=2,
            command=lambda: self._on_view_toggle(CHART_VIEW_DAILY),
        )
        self._btn_daily.pack(side=tk.LEFT, padx=(0, 2))

        self._btn_weekly = tk.Button(
            toggle_frame, text="按周",
            font=(FONT_FAMILY, FONT_SIZE_STATUS),
            bg=COLOR_BG_TOOLBAR, bd=0, cursor="hand2",
            activebackground=COLOR_BG_TOOLBAR_ACTIVE,
            padx=8, pady=2,
            command=lambda: self._on_view_toggle(CHART_VIEW_WEEKLY),
        )
        self._btn_weekly.pack(side=tk.LEFT)

    # ── Canvas ────────────────────────────────────────────────────────────

    def _build_canvas(self):
        """Build the chart canvas."""
        canvas_frame = tk.Frame(self, bg=COLOR_CHART_BG)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))

        self.chart_canvas = tk.Canvas(
            canvas_frame, bg=COLOR_CHART_BG,
            highlightthickness=0, cursor="cross",
        )
        self.chart_canvas.pack(fill=tk.BOTH, expand=True)

        # Store canvas_frame reference for empty-state placement
        self._canvas_frame = canvas_frame

    # ── Empty state ───────────────────────────────────────────────────────

    def _build_empty_state(self):
        """Show empty-state message on the canvas."""
        # We defer positioning until first <Configure> event on the canvas
        self.chart_canvas.bind("<Configure>", self._on_canvas_configure, add="+")

        self._empty_text_id: Optional[int] = None
        self._empty_sub_id: Optional[int] = None

    def _on_canvas_configure(self, event):
        """Reposition empty-state text when canvas resizes."""
        self._draw_empty_state()

    def _draw_empty_state(self):
        """Draw or redraw the empty-state message centered on the canvas."""
        self.chart_canvas.delete("empty_state")

        w = self.chart_canvas.winfo_width()
        h = self.chart_canvas.winfo_height()
        if w < 10 or h < 10:
            return

        cx, cy = w // 2, h // 2

        self.chart_canvas.create_text(
            cx, cy - 12, text="📈",
            font=(FONT_FAMILY, 28), fill=COLOR_TEXT_PLACEHOLDER,
            anchor="center", tags="empty_state",
        )
        self.chart_canvas.create_text(
            cx, cy + 22, text=CHART_EMPTY_TEXT,
            font=(FONT_FAMILY, FONT_SIZE_NORMAL),
            fill=COLOR_CHART_TEXT, anchor="center", tags="empty_state",
        )

    # ── View toggle ───────────────────────────────────────────────────────

    def _on_view_toggle(self, view: str):
        """Handle day/week toggle button click."""
        self._current_view = view
        self._update_toggle_buttons()
        self._draw_empty_state()  # redraw empty state (chart drawing in later phase)

    def _update_toggle_buttons(self):
        """Highlight the active toggle button."""
        active_bg = COLOR_BG_TOOLBAR_ACTIVE
        inactive_bg = COLOR_BG_TOOLBAR

        if self._current_view == CHART_VIEW_DAILY:
            self._btn_daily.configure(bg=active_bg)
            self._btn_weekly.configure(bg=inactive_bg)
        else:
            self._btn_daily.configure(bg=inactive_bg)
            self._btn_weekly.configure(bg=active_bg)

    # ── Public API ────────────────────────────────────────────────────────

    def set_data(self, points: list):
        """Set chart data and redraw. (Phase 5)

        Args:
            points: list of (date_label, token_count) tuples
        """
        self._data_points = points
        # TODO: Phase 5 — implement actual chart drawing

    def set_view(self, view: str):
        """Switch between daily/weekly view. (Phase 5)

        Args:
            view: CHART_VIEW_DAILY or CHART_VIEW_WEEKLY
        """
        self._on_view_toggle(view)
