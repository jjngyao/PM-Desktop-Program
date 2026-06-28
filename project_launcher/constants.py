"""Shared constants for Project Launcher.

All magic values — strings, colors, sizes, and numeric thresholds — are
centralized here.  Business logic MUST import from this module instead of
writing literals directly.
"""

# ── Application ────────────────────────────────────────────────────────────

APP_TITLE = "项目启动器"
APP_FIND_WINDOW_TITLE = "Project Launcher"
MUTEX_NAME = r"Global\ProjectLauncher_SingleInstance"

DEFAULT_WINDOW_WIDTH = 900
DEFAULT_WINDOW_HEIGHT = 600
MIN_WINDOW_WIDTH = 400
MIN_WINDOW_HEIGHT = 300

# ── Search ─────────────────────────────────────────────────────────────────

SEARCH_DEBOUNCE_MS = 150
SEARCH_PLACEHOLDER = "搜索项目..."

# ── Scanner ────────────────────────────────────────────────────────────────

README_EXTENSIONS = ("", ".md", ".txt", ".rst")
DEFAULT_EXCLUDED_DIRS = [
    "$RECYCLE.BIN",
    "System Volume Information",
    "node_modules",
    ".git",
    "__pycache__",
    ".idea",
    ".venv",
    "venv",
]

# ── Directory browsing ─────────────────────────────────────────────────────

MAX_DIR_ENTRIES = 500

# ── Drag & drop ────────────────────────────────────────────────────────────

WM_DROPFILES = 0x0233
DROP_POLL_INTERVAL_MS = 200
DROP_MAX_FILES = 10_000
DROP_PATH_BUFFER_SIZE = 260
SUBCLASS_ID = 42  # arbitrary non-zero id for SetWindowSubclass

# ── Mouse ──────────────────────────────────────────────────────────────────

MOUSEWHEEL_DIVISOR = 120

# ── UI Colors ──────────────────────────────────────────────────────────────

COLOR_BG_WHITE = "#ffffff"
COLOR_BG_HOVER = "#e8e8e8"
COLOR_BG_TOOLBAR = "#f0f0f0"
COLOR_BG_TOOLBAR_ACTIVE = "#e0e0e0"
COLOR_BG_NAV = "#f5f5f5"
COLOR_TEXT_PRIMARY = "#1e1e1e"
COLOR_TEXT_SECONDARY = "#666666"
COLOR_TEXT_TERTIARY = "#888888"
COLOR_TEXT_PLACEHOLDER = "#aaaaaa"
COLOR_GIT_GREEN = "#2ea043"
COLOR_BLUE = "#58a6ff"

# ── UI Fonts ───────────────────────────────────────────────────────────────

FONT_FAMILY = "Segoe UI"
FONT_SIZE_STATUS = 9
FONT_SIZE_NORMAL = 10
FONT_SIZE_LARGE = 11
FONT_SIZE_GEAR = 14
FONT_SIZE_ICON = 14
FONT_SIZE_EMPTY = 12

# ── View modes ─────────────────────────────────────────────────────────────

VIEW_MODE_PROJECTS = "projects"
VIEW_MODE_DIRECTORY = "directory"

# ── Relative time labels ───────────────────────────────────────────────────

TIME_JUST_NOW = "刚刚"
TIME_MINUTES_AGO = "分钟前"
TIME_HOURS_AGO = "小时前"
TIME_YESTERDAY = "昨天"
TIME_DAYS_AGO = "天前"
TIME_WEEKS_AGO = "周前"
