# TapLite

TapLite 是一个面向 Windows 的免费轻量级连点器。项目使用 Python 标准库和 Tkinter 构建界面，通过 Windows `SendInput` API 发送鼠标输入，并使用 `RegisterHotKey` 提供全局热键。

TapLite 的目标是提供一个清晰、轻量、功能强大的桌面工具，适用于普通窗口、无边框窗口和常见全屏场景。项目不会绕过反作弊系统，不会向游戏进程注入代码，也不会实现后台窗口隐藏点击。

## 功能特性

- 支持左键、右键和中键。
- 支持单击和双击。
- 支持毫秒级点击间隔。
- 支持无限循环或指定点击次数。
- 支持跟随当前鼠标位置或使用固定屏幕坐标。
- 支持多点点击列表，每个点可设置独立等待时间。
- 支持随机点击间隔和固定坐标随机偏移。
- 支持启动倒计时和运行时限。
- 支持本地预设保存、载入和删除。
- 默认全局热键：`F6` 开始/停止，`F8` 紧急停止。
- 使用软件目录下的 `data/settings.json` 保存本地配置和预设。

## 运行方式

```powershell
python main.py
```

如果目标游戏以管理员权限运行，请同样以管理员权限启动 TapLite。部分游戏或反作弊系统可能会屏蔽模拟输入，TapLite 不会尝试绕过这些限制。

## 数据位置

TapLite 不写入注册表，也不把配置保存到系统用户目录。运行时产生的配置和预设保存在软件所在目录：

```text
data\settings.json
```

删除 TapLite 时直接删除整个文件夹即可，不会留下额外数据。

## 测试

```powershell
python -m pytest
python -m compileall main.py taplite tests
```

## 打包

推荐使用项目脚本构建发布文件：

```powershell
.\scripts\build.ps1
```

生成文件位于：

```text
releases\TapLite.exe
```

临时构建目录和缓存可通过以下命令清理：

```powershell
.\scripts\clean.ps1
```

## 项目结构

```text
TapLite/
├─ taplite/      # 应用源码
├─ tests/        # 自动化测试
├─ scripts/      # 构建和清理脚本
├─ docs/         # 项目说明文档
├─ releases/     # 用户可直接使用的发布成品
├─ main.py
├─ pyproject.toml
└─ README.md
```

更多结构说明见 [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)。

## 安全边界

- 不添加规避反作弊、隐藏进程、后台注入、驱动级输入或绕过权限限制的能力。
- 如果游戏屏蔽模拟输入，只提供用户提示，不尝试绕过。
- 若目标游戏以管理员权限运行，提示用户同样以管理员权限启动 TapLite。
