# TapLite

TapLite 是一个面向 Windows 的轻量级连点器。项目使用 Python 标准库和 Tkinter 构建界面，通过 Windows `SendInput` API 发送鼠标输入，并使用 `RegisterHotKey` 提供全局热键。

TapLite 的目标是提供一个清晰、轻量、可维护的桌面工具，适用于普通窗口、无边框窗口和常见全屏场景。项目不会绕过反作弊系统，不会向游戏进程注入代码，也不会实现后台窗口隐藏点击。

## 功能特性

- 支持左键、右键和中键。
- 支持单击和双击。
- 支持毫秒级点击间隔。
- 支持无限循环或指定点击次数。
- 支持跟随当前鼠标位置或使用固定屏幕坐标。
- 默认全局热键：`F6` 开始/停止，`F8` 紧急停止。
- 使用 `settings.json` 保存本地配置。
- 对管理员权限和游戏输入限制提供明确提示。

## 运行方式

```powershell
python main.py
```

如果目标游戏以管理员权限运行，请同样以管理员权限启动 TapLite。部分游戏或反作弊系统可能会屏蔽模拟输入，TapLite 不会尝试绕过这些限制。

## 测试

```powershell
python -m pytest
python -m compileall main.py taplite tests
```

## 打包

安装 PyInstaller 后可以构建单文件可执行程序：

```powershell
python -m pip install pyinstaller
python -m PyInstaller --onefile --windowed --name TapLite main.py
```

生成文件位于：

```text
dist\TapLite.exe
```

## GitHub 工作流

- 主分支使用 `main`。
- 新功能、修复和文档更新建议通过独立分支开发。
- 分支命名建议使用 `feature/<name>`、`fix/<name>` 或 `docs/<name>`。
- 提交前运行测试和语法编译检查。
- PR 保持聚焦，避免混入无关格式化、重构或生成文件。

## 代码与注释规范

- 代码遵循 Python 社区常见风格，优先保持简单直接。
- 注释只解释必要的业务意图、平台限制或非显而易见的实现原因。
- Windows API 调用集中在 `taplite/win_input.py` 和 `taplite/hotkeys.py`。
- UI、点击状态机、配置读写保持职责分离。

## 项目结构

```text
TapLite/
├── main.py
├── taplite/
│   ├── clicker.py
│   ├── hotkeys.py
│   ├── settings.py
│   ├── ui.py
│   └── win_input.py
├── tests/
├── AGENTS.md
├── README.md
└── .gitignore
```
