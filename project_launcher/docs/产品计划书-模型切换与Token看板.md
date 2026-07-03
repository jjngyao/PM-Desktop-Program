# 产品计划书：模型切换 & Token 消耗看板

**版本**：v1.2  
**日期**：2026-07-03  
**状态**：开发中 — Phase 1 已完成，Phase 1.5 风险底座修复已完成  
**关联项目**：Project Launcher  
**开发分支**：third

---

## 开发进度

| 阶段 | 内容 | 状态 |
|------|------|------|
| **Phase 1** | 布局重构：左右分栏 + 右侧上下分割 + 左侧面板骨架 + 折线图骨架 + 项目列表 token 列 | ✅ 已完成 (2026-07-01) |
| **Phase 1.5** | 风险底座修复：配置写入备份、拖放覆盖回滚、日志路径统一、删除确认文案强化、基础安全测试 | ✅ 已完成 (2026-07-03) |
| **Phase 2** | `token_scanner.py`：数据解析 + 缓存 + 路径映射 | 🔲 待开发 |
| **Phase 3** | 左侧面板：模型切换功能实现 + settings.json 读写 | 🔲 待开发 |
| **Phase 4** | 左侧面板：Skills 管理功能 + `skill_manager.py` + 启用/禁用 | 🔲 待开发 |
| **Phase 5** | 右上折线图：Canvas 手绘 + 日/周切换 + hover | 🔲 待开发 |
| **Phase 6** | 项目列表 token 列数据联通 | 🔲 待开发 |
| **Phase 7** | 集成联调、边界情况处理、测试 | 🔲 待开发 |

### Phase 1 交付成果

**新增文件：**
- `ui/left_panel.py` — 左侧面板组件（`LeftPanel`），包含：
  - `SectionFrame` — 带标题和分隔线的可折叠区域
  - `ModelRow` — 模型单选行（radio 样式，选中高亮）
  - 模型切换区：3 个模型（Flash/Haiku、Pro/Sonnet、Pro[1m]/Opus），点击切换 + 提示文字
  - Skills 管理区：搜索框 + 计数标签（"已启用 X / Y"）+ 31 个 Checkbutton + 底部提示
  - 整个面板置于 Canvas 中，内容超出时可滚动
- `ui/token_chart.py` — Token 折线图组件（`TokenChart`），包含：
  - 标题栏 "📊 Token 消耗趋势"
  - 按日/按周切换按钮（`tk.Button`，切换高亮）
  - Canvas 画布 + 空状态占位（"暂无 token 消耗数据" 图标 + 文字）

**修改文件：**
- `constants.py` — 新增 60+ 个常量：Token 图表色值/尺寸、Token 格式化（K/M）、Skills 搜索/计数/提示、模型列表/颜色、窗口尺寸调整（1000→780）
- `scanner.py` — `ProjectInfo` 新增 `token_count: int = 0` 字段
- `ui/main_window.py` — 布局重构：
  - `_build_main_area()` 替代原 `_build_project_list()`
  - 水平 `PanedWindow`（左面板 240px | 右侧区域）
  - 右侧垂直 `PanedWindow`（图表 200px | 项目列表）
  - 集成 `LeftPanel` + `TokenChart` 组件
  - 状态栏 `side=tk.BOTTOM` 修复塌缩问题
  - `after_idle` 延迟 sash 定位，修复窗口尺寸恢复后面板塌缩为 1px 的 bug
- `ui/widgets.py` — `ProjectItemFrame` 新增 token 消耗显示行（路径下方），`_format_tokens()` 方法

### Phase 1.5 交付成果（风险底座修复）

**新增文件：**
- `app_paths.py` — 统一应用临时目录与日志路径，所有日志收敛到 `%TEMP%\ProjectLauncher\`
- `ui/safety_messages.py` — 统一删除确认文案，明确提示“直接从磁盘删除，不会进入回收站”
- `tests/test_config_safety.py` — 覆盖配置保存前备份旧配置
- `tests/test_drop_handler_safety.py` — 覆盖拖放覆盖目录失败时恢复原目录
- `tests/test_app_paths.py` — 覆盖日志路径统一到应用临时目录
- `tests/test_safety_messages.py` — 覆盖删除确认文案必须包含风险提示

**修改文件：**
- `config.py` — `save_config()` 在替换现有配置前创建 `.bak` 备份，降低后续写入 Claude Code 配置时的数据损坏风险
- `ui/drop_handler.py` — 覆盖复制改为“先移动旧目标到临时备份；复制成功后清理；复制失败时恢复旧目标”
- `main.py`、`ui/drop_handler.py`、`ui/main_window.py` — 崩溃日志、拖放日志、fault 日志统一使用 `app_paths.get_log_path()`
- `ui/main_window.py`、`ui/browse_controller.py` — 删除项目/文件/文件夹时使用统一高风险确认文案

**验证结果：**
- `python -m unittest tests.test_config_safety tests.test_drop_handler_safety tests.test_app_paths tests.test_safety_messages` 通过（4 个测试）

---

## 一、概述

### 1.1 背景

当前 Project Launcher 是一个轻量级 Windows 桌面工具，专注于项目目录管理和快速启动。用户在 AI 辅助开发过程中，频繁需要在 Claude Code 中切换 AI 模型、并关注各项目的 token 消耗情况。目前这些操作需要在 CLI 中手动完成，缺乏可视化界面。

### 1.2 目标

在 Project Launcher 中新增四个核心能力：

1. **模型切换**：在 GUI 中一键切换 Claude Code 使用的 AI 模型
2. **Skills 统一管理**：集中管理 Claude Code Skills，一键启用/禁用，无需手动操作文件
3. **Token 消耗看板**：以折线图形式展示 token 消耗趋势
4. **项目级 Token 统计**：在每个项目条目中展示该项目的累计 token 消耗

### 1.3 非目标（本期不做）

- 不实现 Claude Code 进程管理（启动/停止）
- 不实现跨设备的 token 数据同步
- 不实现费用计算（仅展示 token 数量）

---

## 二、功能详情

### 2.1 模型切换（左侧面板）

#### 2.1.1 功能描述

在应用界面左侧提供一个模型选择面板，列出所有可用的 AI 模型，用户点击即可切换。

#### 2.1.2 交互流程

```
用户点击模型选项 → 写入 ~/.claude/settings.json → 提示"下次启动 Claude Code 生效"
```

#### 2.1.3 数据来源

`~/.claude/settings.json` 中的 `env` 字段：

| 配置键 | 含义 | 示例值 |
|--------|------|--------|
| `ANTHROPIC_MODEL` | 当前使用的模型 | `deepseek-v4-pro[1m]` |
| `ANTHROPIC_DEFAULT_HAIKU_MODEL` | 默认 Haiku 模型 | `deepseek-v4-flash` |
| `ANTHROPIC_DEFAULT_OPUS_MODEL` | 默认 Opus 模型 | `deepseek-v4-pro[1m]` |
| `ANTHROPIC_DEFAULT_SONNET_MODEL` | 默认 Sonnet 模型 | `deepseek-v4-pro` |
| `ANTHROPIC_BASE_URL` | API 端点 | `https://api.deepseek.com/anthropic` |

#### 2.1.4 可切换的模型列表

根据当前 settings.json 分析，可用模型包括：

| 模型名称 | 角色 | 特点 |
|----------|------|------|
| `deepseek-v4-flash` | Haiku | 快速、轻量 |
| `deepseek-v4-pro` | Sonnet | 均衡性能 |
| `deepseek-v4-pro[1m]` | Opus | 最大上下文 (1M) |

#### 2.1.5 UI 规格

- 以单选列表（RadioButton 样式）展示模型列表
- 当前激活的模型高亮显示
- 每个模型项显示：模型名称 + 角色标签（Haiku / Sonnet / Opus）
- 切换后底部显示提示文字："已切换至 xxx，下次启动 Claude Code 时生效"

#### 2.1.6 边界情况

| 场景 | 处理方式 |
|------|----------|
| settings.json 不存在 | 显示"未检测到 Claude Code 配置"，隐藏模型面板 |
| settings.json 格式异常 | 显示错误提示，提供默认模型列表 |
| 写入 settings.json 失败 | 显示错误对话框，保持原有选择 |
| Claude Code 正在运行中 | 正常写入配置，提示用户重启 CLI 生效 |

---

### 2.2 Skills 统一管理（左侧面板）

#### 2.2.1 功能描述

在左侧面板中集中管理 Claude Code 的所有 Skills。用户可以：
- 查看所有已安装 Skills 的名称和描述
- 一键启用 / 禁用任意 Skill（无需手动操作文件系统）
- 搜索过滤 Skills
- 查看当前启用 / 禁用的 Skill 数量

#### 2.2.2 数据来源

`~/.claude/skills/<skill-name>/SKILL.md`

每个 Skill 是一个目录，其中 `SKILL.md` 带有 YAML frontmatter：

```markdown
---
name: brainstorming
description: "You MUST use this before any creative work..."
---

# Brainstorming Ideas Into Designs
...
```

当前环境已安装 **32 个 Skills**：

| Skill | 描述 |
|-------|------|
| algorithmic-art | 使用 p5.js 创建算法艺术 |
| brainstorming | 创意工作前的需求探索与设计 |
| brand-guidelines | Anthropic 品牌色与排版 |
| canvas-design | 创建海报、设计等静态视觉作品 |
| claude-api | Claude API / Anthropic SDK 参考 |
| dispatching-parallel-agents | 并行独立任务分发 |
| doc-coauthoring | 结构化文档协作 |
| docx | Word 文档创建与编辑 |
| executing-plans | 实施计划的独立执行 |
| finishing-a-development-branch | 开发分支完成与合并 |
| frontend-design | 前端视觉设计指导 |
| internal-comms | 内部沟通文档模板 |
| mcp-builder | MCP 服务器创建指导 |
| pdf | PDF 文件处理 |
| pptx | PowerPoint 演示文稿处理 |
| receiving-code-review | 接收代码审查反馈 |
| requesting-code-review | 请求代码审查 |
| skill-creator | 创建和优化 Skills |
| slack-gif-creator | Slack 动图生成 |
| subagent-driven-development | 子代理驱动开发 |
| systematic-debugging | 系统化调试 |
| test-driven-development | 测试驱动开发 |
| theme-factory | 主题样式工厂 |
| using-git-worktrees | Git Worktree 隔离开发 |
| using-superpowers | 超级能力使用指南 |
| verification-before-completion | 完成前验证 |
| web-artifacts-builder | 多组件 Web 构件 |
| webapp-testing | Playwright Web 应用测试 |
| writing-plans | 实现计划编写 |
| writing-skills | Skills 编写指南 |
| xlsx | Excel 电子表格处理 |
| template | Skill 模板（参考） |

#### 2.2.3 启用/禁用机制

**核心原理**：Claude Code 在启动时扫描 `~/.claude/skills/` 目录，所有子目录中的 Skill 均会被加载。启用/禁用的本质是移入/移出该目录。

```
启用状态：~/.claude/skills/<skill-name>/SKILL.md     ← Claude Code 可见
禁用状态：~/.claude/skills_disabled/<skill-name>/SKILL.md  ← Claude Code 不可见
```

**操作流程**：
```
用户点击开关
  ├─ 启用 → 将目录从 skills_disabled/ 移回 skills/
  └─ 禁用 → 将目录从 skills/ 移到 skills_disabled/
           ↓
     提示"Skill xxx 已启用/禁用，下次启动 Claude Code 时生效"
```

#### 2.2.4 UI 规格

左侧面板采用垂直三段布局：

```
┌──────────────────┐
│                  │
│   模型切换        │  ← 模型列表（RadioButton）
│   ○ Flash        │
│   ● Pro          │
│   ○ Pro[1m]      │
│                  │
│ ──────────────── │  ← 分隔线
│                  │
│   Skills 管理     │  ← 标题 + 搜索框 + 计数 "已启用 28 / 32"
│   [🔍 搜索...]   │
│                  │
│   ☑ brainstorming│  ← 每个 Skill 一行：Checkbutton + 名称
│   ☑ canvas-design│     勾选 = 启用，取消 = 禁用
│   ☐ docx         │     hover 显示完整描述 tooltip
│   ☑ pdf          │
│   ☑ pptx         │
│   ☐ template     │
│   ...            │  ← 可滚动
│                  │
└──────────────────┘
```

**交互细节**：
- 使用 `Checkbutton` 样式，勾选 = 启用，未勾选 = 禁用
- 点击切换时，即时执行文件移动操作
- 搜索框支持按名称模糊过滤
- 统计行显示 "已启用 X / Y"
- 左侧面板整体可滚动（模型区 + Skills 区共用一个滚动区域）
- 底部显示操作提示："更改将在下次启动 Claude Code 时生效"

#### 2.2.5 技术实现

**文件操作**：
```python
import shutil, os

SKILLS_DIR = os.path.expanduser("~/.claude/skills")
DISABLED_DIR = os.path.expanduser("~/.claude/skills_disabled")

def enable_skill(name: str):
    """启用 Skill：从 disabled 移回 skills"""
    src = os.path.join(DISABLED_DIR, name)
    dst = os.path.join(SKILLS_DIR, name)
    if os.path.isdir(src):
        shutil.move(src, dst)

def disable_skill(name: str):
    """禁用 Skill：从 skills 移到 disabled"""
    src = os.path.join(SKILLS_DIR, name)
    dst = os.path.join(DISABLED_DIR, name)
    os.makedirs(DISABLED_DIR, exist_ok=True)
    if os.path.isdir(src):
        shutil.move(src, dst)
```

**Skill 元数据解析**：
```python
import yaml  # 或手写简单的 YAML frontmatter 解析
import re

def parse_skill_md(path: str) -> dict:
    """从 SKILL.md 中提取 name 和 description"""
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    # 匹配 YAML frontmatter: ---\n...\n---
    m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if m:
        # 简单解析（避免引入 PyYAML 依赖）
        meta = {}
        for line in m.group(1).split('\n'):
            if ':' in line:
                k, v = line.split(':', 1)
                meta[k.strip()] = v.strip().strip('"')
        return meta
    return {}
```

#### 2.2.6 边界情况

| 场景 | 处理方式 |
|------|----------|
| skills/ 目录不存在 | 显示"未检测到 Claude Code Skills"，隐藏 Skills 面板 |
| skills_disabled/ 不存在 | 首次禁用时自动创建 |
| SKILL.md 无 frontmatter | 使用目录名作为显示名，描述为空 |
| 移动文件失败（权限等） | 显示错误提示，Checkbutton 回弹到原状态 |
| Claude Code 正在运行中 | 正常移动，提示用户重启 CLI 生效 |
| Skill 目录名含特殊字符 | 正常处理，文件系统操作不受影响 |

---

### 2.3 Token 消耗趋势图（右上方面板）

#### 2.3.1 功能描述

以折线图形式展示所有项目的 token 消耗趋势，支持按时间维度（按日/按周）切换。

#### 2.3.2 交互流程

```
打开应用 → 扫描 ~/.claude/projects/ → 聚合 token 数据 → 渲染折线图
                                                          ↓
                                              用户切换日/周视图 → 重新渲染
```

#### 2.3.3 数据来源

`~/.claude/projects/<项目路径编码>/<session-id>.jsonl`

每个会话文件中的 `type: "assistant"` 事件包含：

```json
{
  "type": "assistant",
  "timestamp": 1782882686091,
  "message": {
    "model": "deepseek-v4-pro",
    "usage": {
      "input_tokens": 28733,
      "output_tokens": 189,
      "cache_creation_input_tokens": 0,
      "cache_read_input_tokens": 0
    }
  }
}
```

**数据提取逻辑**：
1. 遍历 `~/.claude/projects/` 下所有子目录
2. 每个子目录代表一个项目，读取其中所有 `.jsonl` 文件
3. 筛选 `type == "assistant"` 的事件
4. 按 `timestamp` 聚合 `input_tokens + output_tokens`
5. 按日/周汇总，生成时间序列数据

#### 2.3.4 路径编码映射

Claude Code 对项目路径做了编码处理：

| 原始字符 | 编码后 |
|----------|--------|
| `\` | `--` |
| `:` | `-` |

示例：`D:\My_projects\vibe_coding` → `D--My-projects-vibe-coding`

需要实现双向映射，以便将 token 数据与项目启动器中的项目匹配。

#### 2.3.5 图表规格

- **渲染方式**：tk.Canvas 手绘（不引入 matplotlib，保持 EXE 轻量）
- **X 轴**：日期 / 周次
- **Y 轴**：token 消耗量
- **数据线**：一条折线表示每日/每周的总 token 消耗
- **数据点**：圆点标记，hover 显示具体数值
- **颜色方案**：使用项目现有的蓝色调（`COLOR_BLUE`）

#### 2.3.6 图表组件清单

| 组件 | 说明 |
|------|------|
| 标题栏 | "Token 消耗趋势" + 日/周切换按钮 |
| 坐标轴 | X 轴（时间）、Y 轴（token 数，自动缩放到 K/M） |
| 折线 | 连接各数据点，使用项目主色调 |
| 数据填充 | 折线下方半透明填充，增强视觉效果 |
| 数据点 | 圆形标记，hover 时放大并显示 tooltip |
| 图例 | 右上角小标签 "总消耗" |

#### 2.3.7 边界情况

| 场景 | 处理方式 |
|------|----------|
| 无 token 数据 | 显示空状态："暂无 token 消耗数据" |
| 仅有单日数据 | 显示单点 + 提示"数据不足，需更多使用后生成趋势" |
| 数据量极大（>1000 点） | 自动降采样，按周聚合 |
| 项目目录不存在于 token 记录中 | 该项目的 token 显示为 0 |

---

### 2.4 项目 Token 消耗列（右下方项目列表）

#### 2.4.1 功能描述

在现有项目列表中新增一列，显示每个项目从首次使用 Claude Code 至今的累计 token 消耗。

#### 2.4.2 UI 规格

在 `ProjectItemFrame` 中，路径下方或右侧新增一行：

```
📁 vibe-coding                           1,916,039 tokens
   D:\My_projects\vibe_coding
```

- Token 数值使用紧凑格式：`1.9M`（百万）、`293K`（千）、`416`（小于千）
- 颜色使用 `COLOR_TEXT_TERTIARY`，字号与路径一致

#### 2.4.3 匹配逻辑

```
项目路径 → 路径编码 → 查找 ~/.claude/projects/ 下对应目录 → 汇总所有会话的 token
```

1. 将项目启动器中的项目路径按 Claude Code 规则编码
2. 在 `~/.claude/projects/` 中查找匹配的目录
3. 如果找到，解析所有 `.jsonl` 会话文件，汇总 token
4. 如果未找到，显示 `—` 或不显示 token 行

#### 2.4.4 性能优化

为避免每次刷新都重新解析所有 JSONL 文件，引入缓存机制：

| 策略 | 说明 |
|------|------|
| **缓存文件** | 将聚合结果缓存到 `~/.claude/projects/.token_cache.json` |
| **增量更新** | 记录最后扫描时间，仅解析新的/修改过的 `.jsonl` 文件 |
| **后台线程** | token 扫描在后台线程执行，不阻塞 UI |
| **扫描间隔** | 手动刷新（F5）时触发，或启动后自动扫描一次 |

**缓存文件结构**：
```json
{
  "last_scan": "2026-07-01T12:00:00",
  "projects": {
    "D--My-projects-vibe-coding": {
      "total_tokens": 1916039,
      "input_tokens": 1369687,
      "output_tokens": 543532,
      "daily": {
        "2026-06-11": 45210,
        "2026-06-12": 89320,
        ...
      }
    }
  }
}
```

---

## 三、界面布局

### 3.1 整体结构

```
┌──────────────┬────────────────────────────────────────┐
│              │                                        │
│  ☰ 模型切换   │         Token 消耗趋势（折线图）          │
│              │         [ 按日 ◉ ] [ 按周 ○ ]           │
│  ○ Flash     │                                        │
│  ● Pro       │                                        │
│  ○ Pro[1m]   ├────────────────────────────────────────┤
│              │                                        │
│ ──────────── │   项目列表                         Token │
│              │   ─────────────────────────────────    │
│  ☰ Skills   │   ● labelme-main             3.0M tk   │
│  管理 [🔍]   │     C:\Users\...\labelme-main           │
│  已启用 28/32│   ● vibe-coding              1.9M tk   │
│              │     D:\My_projects\vibe_coding          │
│  ☑ brain... │   ● game                     960K tk   │
│  ☑ canvas.. │     D:\My_projects\game                 │
│  ☐ docx     │   ● my-knowledge-base        698K tk   │
│  ☑ pdf      │     ...                                │
│  ☐ template │                                        │
│  ...        │                                        │
└──────────────┴────────────────────────────────────────┘
```

### 3.2 布局实现方案

| 层级 | 控件 | 说明 |
|------|------|------|
| 主分割 | `PanedWindow`（水平） | 左右可拖拽调整宽度 |
| 左面板 | `Frame` + 内嵌 Canvas 滚动 | 固定最小宽度 200px，默认 240px，内部包含模型切换区 + Skills 管理区，整体可滚动 |
| 右上 | `Frame` | 固定高度 200px（可拖拽） |
| 右下 | 现有 `list_canvas` | 项目列表区域 |
| 右侧分割 | `PanedWindow`（垂直） | 上下可拖拽调整 |

### 3.3 窗口尺寸调整

- 默认窗口宽度从现在的默认值增加到 **1000px**（原 780px）
- 最小宽度增加到 **780px**
- 左侧面板最小宽度 200px，最大宽度 350px
- 右上折线图最小高度 150px，默认 200px

---

## 四、数据流

```
                    ┌──────────────────────────┐
                    │   ~/.claude/              │
                    │   ├── settings.json       │── 读取/写入模型配置
                    │   ├── skills/             │── 读取 Skills 元数据
                    │   │   ├── brainstorming/  │    移入/移出 启用/禁用
                    │   │   │   └── SKILL.md    │
                    │   │   └── ... (32个)      │
                    │   ├── skills_disabled/    │── 存放已禁用的 Skills
                    │   ├── projects/           │── 读取 token 数据
                    │   │   ├── proj-A/         │
                    │   │   │   ├── s1.jsonl    │
                    │   │   │   └── s2.jsonl    │
                    │   │   └── proj-B/         │
                    │   └── sessions/           │
                    └──────────┬───────────────┘
                               │
     ┌─────────────────────────┼─────────────────────────┐
     │                         │                         │
     ▼                         ▼                         ▼
┌─────────────┐    ┌──────────────────────┐    ┌──────────────┐
│ skill_mgr.py│    │   token_scanner.py   │    │settings_rw.py│
│ - 解析 SKILL │    │ - 解析 JSONL         │    │ - 读写 config│
│   .md 元数据 │    │ - 路径编码/解码       │    │ - 模型列表    │
│ - 启用/禁用  │    │ - 缓存管理           │    │               │
│   文件移动   │    │ - 后台线程扫描        │    │               │
└──────┬──────┘    └──────────┬───────────┘    └──────┬───────┘
       │                      │                      │
       └──────────────────────┼──────────────────────┘
                              │
                 ┌────────────▼───────────────┐
                 │     MainWindow             │
                 │  - 左侧：模型切换 + Skills  │
                 │  - 右上：折线图 Canvas      │
                 │  - 右下：项目列表 + token列 │
                 └────────────────────────────┘
```

---

## 五、技术方案

### 5.1 新增文件

| 文件 | 职责 |
|------|------|
| `ui/left_panel.py` | 左侧面板容器：模型切换区 + Skills 管理区，含整体滚动 |
| `ui/token_chart.py` | 右上 Token 折线图组件（Canvas 手绘） |
| `token_scanner.py` | Token 数据解析、聚合、缓存模块 |
| `skill_manager.py` | Skills 元数据解析、启用/禁用（文件移动）、状态管理 |

### 5.2 修改文件

| 文件 | 变更内容 |
|------|----------|
| `ui/main_window.py` | 布局重构（左右分栏）、集成左侧面板和折线图组件 |
| `ui/widgets.py` | `ProjectItemFrame` 新增 token 消耗显示行 |
| `constants.py` | 新增颜色、尺寸、路径常量 |
| `ProjectLauncher.spec` | 无需修改（不引入新第三方依赖） |

### 5.3 Skills 管理实现要点

```python
class SkillManager:
    """管理 Claude Code Skills 的启用/禁用状态。"""
    
    def __init__(self):
        self.skills_dir = os.path.expanduser("~/.claude/skills")
        self.disabled_dir = os.path.expanduser("~/.claude/skills_disabled")
    
    def list_all(self) -> list[SkillInfo]:
        """列出所有 Skills（启用的 + 禁用的），含元数据。"""
        ...
    
    def enable(self, name: str):
        """将 Skill 从 disabled/ 移回 skills/。"""
        shutil.move(
            os.path.join(self.disabled_dir, name),
            os.path.join(self.skills_dir, name),
        )
    
    def disable(self, name: str):
        """将 Skill 从 skills/ 移到 disabled/。"""
        os.makedirs(self.disabled_dir, exist_ok=True)
        shutil.move(
            os.path.join(self.skills_dir, name),
            os.path.join(self.disabled_dir, name),
        )
    
    def parse_metadata(self, skill_dir: str) -> dict:
        """从 SKILL.md 的 YAML frontmatter 提取 name/description。
        使用正则解析，避免引入 PyYAML 依赖。"""
        ...
```

### 5.4 折线图实现要点

```python
class TokenChart(tk.Canvas):
    """在 Canvas 上手绘折线图。"""
    
    # 核心绘制步骤：
    # 1. 计算边距（左侧给 Y 轴标签留空间）
    # 2. 绘制 X/Y 轴线和刻度
    # 3. 将 token 数据映射到像素坐标
    # 4. create_line 画折线
    # 5. create_oval 画数据点
    # 6. 绑定 <Motion> 事件实现 hover tooltip
```

### 5.5 不引入新依赖

保持项目"仅 Python 标准库"的特性：

- 折线图 → `tk.Canvas.create_line` + `create_oval` + `create_text`
- JSON 解析 → `json`（标准库）
- 时间处理 → `datetime`（标准库）
- 后台扫描 → `threading`（标准库，已有模式）

---

## 六、开发计划

| 阶段 | 内容 | 预估工作量 | 状态 |
|------|------|------------|------|
| **Phase 1** | 布局重构：左右分栏 + 右侧上下分割 + 左侧面板骨架 + 折线图骨架 + 项目列表 token 列 | 中 | ✅ 已完成 |
| **Phase 1.5** | 风险底座修复：配置备份、覆盖回滚、日志路径统一、删除确认文案、安全测试 | 小 | ✅ 已完成 |
| **Phase 2** | `token_scanner.py`：数据解析 + 缓存 + 路径映射 | 中 | 🔲 待开发 |
| **Phase 3** | 左侧面板：模型切换功能 + settings.json 读写 | 小 | 🔲 待开发 |
| **Phase 4** | 左侧面板：Skills 管理功能 + `skill_manager.py` + 启用/禁用 | 中 | 🔲 待开发 |
| **Phase 5** | 右上折线图：Canvas 手绘 + 日/周切换 + hover | 中 | 🔲 待开发 |
| **Phase 6** | 项目列表 token 列 + 数据联通 | 小 | 🔲 待开发 |
| **Phase 7** | 集成联调、边界情况处理、测试 | 中 | 🔲 待开发 |

---

## 七、风险与注意事项

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| JSONL 文件体积大（单文件可达 1MB+） | 扫描慢 | 缓存 + 增量更新 |
| settings.json / 应用配置写入失败或被覆盖 | 配置损坏、用户配置丢失 | ✅ 已缓解：应用配置保存前创建 `.bak` 备份；后续 Claude Code settings 写入沿用同一策略 |
| Skills 目录移动失败（权限/占用） | 启用/禁用不生效 | 操作前校验权限，失败时回弹 UI + 错误提示 |
| 拖放覆盖目录过程中复制失败 | 原目录被删除或半覆盖 | ✅ 已缓解：覆盖前移动旧目标到临时备份，失败时恢复，成功后清理备份 |
| 删除项目/文件夹/文件误操作 | 用户数据不可恢复 | ✅ 已缓解：删除确认文案明确“直接从磁盘删除，不会进入回收站”，并要求确认路径 |
| 崩溃日志路径分散 | 排障困难 | ✅ 已缓解：统一写入 `%TEMP%\ProjectLauncher\` |
| 路径编码歧义（路径名含 `--`） | 匹配失败 | 按最长路径优先匹配，记录日志 |
| Canvas 折线图性能 | 重绘卡顿 | 仅在数据变化时重绘，限制最多 365 个数据点 |
| 新布局对小屏幕不友好 | 显示拥挤 | PanedWindow 支持拖拽 + 折叠侧栏按钮 |
| YAML frontmatter 解析不完整 | Skill 描述缺失 | 正则兜底 + 使用目录名作为 fallback 显示名 |

---

## 八、附录

### A. 当前项目 Token 数据快照（2026-07-01）

| 项目 | Token 消耗 |
|------|------------|
| labelme-main | 3,029,955 |
| vibe-coding | 1,916,039 |
| game | 959,624 |
| my-knowledge-base | 697,752 |
| data-projects | 296,911 |
| model-test | 293,109 |
| my-web | 278,890 |
| labelme-standalone | 255,091 |
| model-test-Game-projects | 160,576 |
| system32 | 154,393 |
| MarkItDown | 137,183 |
| bili-video-merger-main | 75,942 |
| Obsidian-Vault | 46,436 |
| Obsidian-COMPLETE-verified | 41,816 |

### B. Claude Code 配置路径参考

| 用途 | 路径 |
|------|------|
| 设置（模型、API key） | `~/.claude/settings.json` |
| Skills 目录（已启用） | `~/.claude/skills/<skill-name>/` |
| Skills 目录（已禁用） | `~/.claude/skills_disabled/<skill-name>/` |
| Skill 元数据 | `~/.claude/skills/<skill-name>/SKILL.md` |
| 项目会话数据 | `~/.claude/projects/<编码路径>/` |
| 当前会话元信息 | `~/.claude/sessions/<pid>.json` |
| 全局对话历史 | `~/.claude/history.jsonl` |

### C. 当前已安装 Skills 列表（32个）

| Skill 目录名 | 描述 |
|-------------|------|
| algorithmic-art | 使用 p5.js 创建算法艺术，支持种子随机性和交互式参数探索 |
| brainstorming | 创意工作前的强制性需求探索 — 在任何代码编写之前使用 |
| brand-guidelines | 将 Anthropic 品牌颜色和排版应用于各类产出物 |
| canvas-design | 使用设计哲学创建精美的 PNG/PDF 静态视觉作品 |
| claude-api | Claude API / Anthropic SDK 参考：模型 ID、定价、参数、流式等 |
| dispatching-parallel-agents | 处理 2+ 个独立任务时的并行代理分发 |
| doc-coauthoring | 结构化文档协作编写工作流 |
| docx | Word 文档 (.docx) 的创建、读取、编辑和操作 |
| executing-plans | 在独立会话中执行实现计划，含审查检查点 |
| finishing-a-development-branch | 开发完成后的合并/PR/清理决策指导 |
| frontend-design | 构建新 UI 或改造现有 UI 时的独特视觉设计指导 |
| internal-comms | 内部沟通文档模板（状态报告、领导层更新、FAQ 等） |
| mcp-builder | 创建高质量 MCP 服务器的指导 |
| pdf | PDF 文件的读取、合并、拆分、加水印、表单填写、OCR |
| pptx | PowerPoint 演示文稿的创建、读取、编辑 |
| receiving-code-review | 接收代码审查反馈时的技术验证处理 |
| requesting-code-review | 完成任务或重大功能后验证工作正确性 |
| skill-creator | 创建新 Skills、修改和优化现有 Skills、性能评估 |
| slack-gif-creator | 为 Slack 创建优化的动画 GIF |
| subagent-driven-development | 使用子代理在当前会话中执行独立任务 |
| systematic-debugging | 遇到 bug/测试失败/意外行为时的系统化调试 |
| test-driven-development | 功能或 bug 修复前先编写测试 |
| theme-factory | 为幻灯片、文档、报告、HTML 页面等应用主题样式 |
| using-git-worktrees | 使用 Git Worktree 进行隔离的功能开发 |
| using-superpowers | 建立如何查找和使用 Skills 的会话起始指南 |
| verification-before-completion | 声称工作完成/修复/通过前的强制验证 |
| web-artifacts-builder | 使用 React/Tailwind/shadcn 创建复杂的多组件 HTML 构件 |
| webapp-testing | 使用 Playwright 测试和交互本地 Web 应用 |
| writing-plans | 有多步骤任务规格时的实现计划编写 |
| writing-skills | Skills 的创建、编辑和部署前验证 |
| xlsx | Excel 电子表格 (.xlsx/.csv/.tsv) 的创建、读取、编辑 |
| template | Skill 模板（仅供参考，默认禁用） |
