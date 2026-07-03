"""Shared constants for Project Launcher.

All magic values — strings, colors, sizes, and numeric thresholds — are
centralized here.  Business logic MUST import from this module instead of
writing literals directly.
"""

# ── Application ────────────────────────────────────────────────────────────

APP_TITLE = "项目启动器"
APP_FIND_WINDOW_TITLE = "Project Launcher"
MUTEX_NAME = r"Global\ProjectLauncher_SingleInstance"

DEFAULT_WINDOW_WIDTH = 1000
DEFAULT_WINDOW_HEIGHT = 600
MIN_WINDOW_WIDTH = 780
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

# ── Layout ──────────────────────────────────────────────────────────────────

LEFT_PANEL_MIN_WIDTH = 200
LEFT_PANEL_DEFAULT_WIDTH = 240
CHART_AREA_MIN_HEIGHT = 150
CHART_AREA_DEFAULT_HEIGHT = 200

# ── Left panel colors ───────────────────────────────────────────────────────

COLOR_BG_LEFT_PANEL = "#f8f8f8"
COLOR_SECTION_HEADER = "#333333"
COLOR_SECTION_BORDER = "#dddddd"

# ── Font sizes (additional) ──────────────────────────────────────────────────

FONT_SIZE_SECTION = 11
FONT_SIZE_SMALL = 9

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

# ── Token chart ─────────────────────────────────────────────────────────────

COLOR_CHART_BG = "#ffffff"
COLOR_CHART_LINE = "#58a6ff"
COLOR_CHART_FILL = "#e8f2ff"
COLOR_CHART_POINT = "#58a6ff"
COLOR_CHART_POINT_HOVER = "#1a7fd4"
COLOR_CHART_AXIS = "#cccccc"
COLOR_CHART_TEXT = "#888888"
COLOR_CHART_GRID = "#f0f0f0"

CHART_PADDING_LEFT = 60
CHART_PADDING_RIGHT = 20
CHART_PADDING_TOP = 20
CHART_PADDING_BOTTOM = 40
CHART_POINT_RADIUS = 4
CHART_POINT_HOVER_RADIUS = 6
CHART_LINE_WIDTH = 2
CHART_MAX_DATA_POINTS = 365

CHART_VIEW_DAILY = "daily"
CHART_VIEW_WEEKLY = "weekly"

CHART_EMPTY_TEXT = "暂无 token 消耗数据"

# ── Token formatting ────────────────────────────────────────────────────────

TOKEN_DISPLAY_NONE = "—"
TOKEN_FORMAT_THOUSAND = "K"
TOKEN_FORMAT_MILLION = "M"
TOKEN_DISPLAY_SUFFIX = " tokens"
TOKEN_FONT_SIZE = 8

# ── Skills management ───────────────────────────────────────────────────────

SKILLS_SEARCH_PLACEHOLDER = "搜索 Skills..."
SKILLS_COUNT_FORMAT = "已启用 {} / {}"
SKILLS_HINT_TEXT = "更改将在下次启动 Claude Code 时生效"

# ── Model switching ─────────────────────────────────────────────────────────

MODEL_HINT_FORMAT = "已切换至 {}，下次启动 Claude Code 时生效"
MODEL_NO_CONFIG_HINT = "未检测到 Claude Code 配置"
MODEL_DEFAULT_LIST = [
    {"name": "deepseek-v4-flash", "role": "Haiku", "desc": "快速、轻量"},
    {"name": "deepseek-v4-pro", "role": "Sonnet", "desc": "均衡性能"},
    {"name": "deepseek-v4-pro[1m]", "role": "Opus", "desc": "最大上下文 (1M)"},
]

COLOR_MODEL_ACTIVE_BG = "#e3f2fd"
COLOR_MODEL_INACTIVE_BG = "#f8f8f8"
COLOR_MODEL_ROLE_TAG = "#1976d2"

