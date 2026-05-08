# AGENTS.md

## 项目概览

TapLite 是一个面向 Windows 的轻量级连点器，使用 Python 标准库实现：

- `tkinter` 提供桌面界面。
- `ctypes` 调用 Windows `SendInput` 发送鼠标输入。
- `RegisterHotKey` 提供全局热键。
- `json` 保存本地配置。

项目不实现反作弊绕过、后台窗口注入、游戏规则规避或隐藏式自动化能力。

## 开发约定

- 文档类文件使用中文书写，包括 README、贡献说明、发布说明和设计说明。
- 代码命名遵循 Python 社区惯例：模块、函数、变量使用 `snake_case`，类名使用 `PascalCase`。
- 注释遵循行业内常见标准：只解释业务意图、平台限制或非显而易见的实现原因，避免重复代码本身。
- Windows API 相关逻辑应隔离在 `taplite/win_input.py` 和 `taplite/hotkeys.py`，不要散落到 UI 层。
- UI 层只负责展示、输入校验和状态同步；点击状态机应保留在 `taplite/clicker.py`。
- 不引入第三方运行时依赖，除非有明确收益并同步更新 README 和项目元数据。

## GitHub 工作流

- 默认主分支为 `main`。
- 新功能或修复从 `main` 创建分支，建议命名为 `feature/<name>`、`fix/<name>` 或 `docs/<name>`。
- 每个 PR 聚焦一个目标，避免混入无关格式化或重构。
- 合并前至少运行：

```powershell
python -m pytest
python -m compileall main.py taplite tests
```

- Commit 信息遵循 Conventional Commits 规范，格式为 `<type>(optional scope): <description>`。
- 常用 type 包括：`feat`、`fix`、`docs`、`refactor`、`test`、`chore`、`build`、`ci`。
- description 使用简洁英文或中文均可，但同一 PR 内保持一致。
- PR 标题默认使用同样的 Conventional Commits 风格。
- 如果存在破坏性变更，使用 `!` 标记，例如 `feat(settings)!: change config schema`，并在 PR 描述中说明迁移方式。
- 示例：
  - `feat(clicker): add fixed-position click mode`
  - `fix(hotkeys): handle invalid hotkey strings`
  - `docs: update Windows permission notes`

## 测试要求

- 修改点击状态机时，补充或更新 `tests/test_clicker.py`。
- 修改配置结构时，补充或更新 `tests/test_settings.py`。
- 修改热键解析时，补充或更新 `tests/test_hotkeys.py`。
- 涉及真实 Windows 输入的改动，需要手动验证普通窗口、固定坐标和全局热键。

## 安全边界

- 不添加规避反作弊、隐藏进程、后台注入、驱动级输入或绕过权限限制的能力。
- 如果游戏屏蔽模拟输入，只提供用户提示，不尝试绕过。
- 若目标游戏以管理员权限运行，提示用户同样以管理员权限启动 TapLite。
