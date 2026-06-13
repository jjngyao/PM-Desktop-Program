# CLAUDE.md

**沟通语言：始终使用中文进行交流。**

## 项目：Project Launcher（项目快速启动工具）

一款轻量级 Windows 桌面工具（Python 3.10+ / Tkinter），用于集中管理和快速启动分散在磁盘各处的开发项目。双击项目条目即可在 IDE 中打开。

**平台：** 仅限 Windows 10/11 — 使用了 `ctypes` Win32 API 调用（互斥体、DPI、窗口激活）。

---

## 项目结构

```
project_launcher/
├── main.py                  # 入口 — 冻结构建时的 stderr 重定向、崩溃日志
├── app.py                   # 应用编排器 — 串联 config、scanner、launcher、UI；单实例互斥锁
├── config.py                # JSON 配置持久化 — 便携模式（EXE 旁的 config.json）> %APPDATA%
├── scanner.py               # 后台线程目录扫描器 — 将子目录列为"项目"
├── launcher.py              # IDE 自动检测（VS Code、Cursor、Windsurf）+ 子进程启动
├── ui/
│   ├── __init__.py
│   ├── main_window.py       # 主窗口 — 工具栏、可滚动项目列表、状态栏、搜索
│   ├── widgets.py            # 可复用组件 — SearchEntry（防抖）、ProjectItemFrame（悬停/启动/右键菜单）
│   └── settings_dialog.py   # 模态设置对话框 — 基础目录、IDE 选择、排除目录、排序开关
├── build.bat                # PyInstaller 构建脚本 → 生成 dist/ProjectLauncher.exe
├── ProjectLauncher.spec     # PyInstaller 规格文件（--onefile、--windowed、tkinter 隐式导入）
├── icon.png                 # 应用图标
└── README.md                # 用户文档（中文）

requirements.txt             # PyInstaller >= 6.0（根目录）
```

## 架构

### 数据流
```
config.json ──► config.py (加载) ──► App.__init__ ──► MainWindow(config)
                   ▲                                      │
                   │                              scanner.py (后台线程)
                   │                                      │
                   └── config.py (保存) ◄── SettingsDialog ◄── 扫描结果 → UI 列表
```

### 关键设计决策

1. **单实例锁**（`app.py:42-61`）：Windows 命名互斥体（`Global\ProjectLauncher_SingleInstance`）。第二个实例通过 `FindWindowW` / `SetForegroundWindow` 激活已有窗口，而不是再次启动。

2. **配置优先级**（`config.py:37-61`）：便携模式优先 — 如果 EXE 同目录存在 `config.json` 则直接使用，否则回退到 `%APPDATA%/ProjectLauncher/config.json`。通过 `tempfile.mkstemp` + `os.replace` 实现原子化保存。

3. **后台扫描**（`scanner.py:151-168`）：`scan_async()` 启动一个守护线程。回调在后台线程触发；`MainWindow` 通过 `root.after(0, ...)` 将回调调度到 Tkinter 主线程。

4. **IDE 检测**（`launcher.py:87-100`）：检查 `%LOCALAPPDATA%\Programs\` 和 `%ProgramFiles%` 下的已知安装路径，以及通过 `shutil.which` 进行 PATH 查找。始终追加"文件资源管理器"作为兜底选项。

5. **搜索防抖**（`ui/widgets.py:54-63`）：`SearchEntry` 通过 `tk.after` 对按键进行 150ms 防抖处理。导航键（方向键、Tab 等）跳过防抖。

6. **DPI 感知**（`ui/main_window.py:81-97`）：在 Windows 10 1703+ 上调用 `SetProcessDpiAwareness(2)`（逐显示器 V2），并为旧版本提供回退方案。

### 冻结构建（PyInstaller）
- `main.py` 检查 `sys.frozen` — 将 stderr 重定向到 `%TEMP%/ProjectLauncher/error.log`（`--windowed` 模式下无控制台窗口）
- `icon.png` 和 tkinter 隐式导入通过 `--add-data` 和 `--hidden-import` 包含
- 排除 `matplotlib`、`numpy`、`pandas` 以减小二进制体积（约 8–12 MB）

## 开发

### 直接运行（需要 Python 3.10+）
```bash
cd project_launcher
python main.py
```

### 构建独立 EXE
```bash
cd project_launcher
build.bat          # 或：pyinstaller ProjectLauncher.spec
# 输出：dist/ProjectLauncher.exe
```

### 依赖
- **运行时：** 仅 Python 标准库（tkinter、ctypes、json、os、subprocess、threading、dataclasses）
- **构建时：** PyInstaller >= 6.0（见 `requirements.txt`）

## 代码规范

- **语言：** UI 字符串使用中文，代码和注释使用英文
- **类型标注：** 全程完整类型提示（`from typing import ...`、`dataclasses`）
- **配置键命名：** snake_case（`base_directory`、`selected_ide`、`excluded_dirs`、`sort_recent_first`、`window_geometry`、`last_opened`）
- **错误处理：** 优雅降级 — 可能失败的操作均包裹在 try/except 中，静默回退或回退到文件资源管理器
- **UI 模式：** Tkinter + ttk 主题（优先使用 `vista`，回退到 `clam`）；自定义悬停效果通过手动切换背景色实现
- **线程安全：** 扫描器在守护线程中运行；所有 tkinter 组件操作均通过 `root.after` 在主线程执行
