# TapLite

TapLite 是一个面向 Windows 的轻量级连点器，使用 Python 标准库和 Tkinter 构建界面，通过 Windows `SendInput` API 发送鼠标输入，并使用 `RegisterHotKey` 提供全局热键。

项目目标是提供一个清晰、轻量、可直接使用的桌面工具，适用于普通窗口、无边框窗口和常见全屏场景。项目不绕过反作弊系统，不向游戏进程注入代码，也不提供后台窗口隐藏点击。

## 项目状态

当前版本为 `0.3.0`，处于早期可用阶段。

## 功能特性

- 支持左键、右键和中键
- 支持单击和双击
- 支持毫秒级点击间隔
- 支持无限循环或指定点击次数/轮数
- 支持当前位置点击或固定坐标点击
- 支持多点点击列表，每个点可设置独立等待时间
- 支持随机点击间隔和固定坐标随机偏移
- 支持启动倒计时和运行时限
- 支持运行中右下角状态提示
- 支持关闭窗口后驻留系统托盘，可从托盘恢复、开始/停止和退出
- 支持本地预设保存、载入和删除
- 默认全局热键：`F6` 开始/停止，`F8` 紧急停止
- 使用软件目录下的 `data/settings.json` 保存本地配置和预设

## 运行方式

```powershell
python main.py
```

如果目标程序以管理员权限运行，请也用管理员权限启动 TapLite。部分游戏或反作弊系统可能会屏蔽模拟输入，TapLite 不会尝试绕过这些限制。

## 数据位置

运行时配置和预设保存在：

```text
data\settings.json
```

## 测试

首次开发建议安装开发依赖：

```powershell
python -m pip install -e ".[dev]"
```

然后运行：

```powershell
python -m pytest
python -m compileall main.py taplite tests
```

## 打包

推荐使用项目脚本构建发布文件：

```powershell
.\scripts\build.ps1
```

构建时会使用 `assets/TapLite.ico` 作为应用图标，生成文件位于：

```text
releases\TapLite.exe
```

## 项目结构

```text
TapLite/
├─ assets/       # 项目图标等静态资源
├─ taplite/      # 应用源码
├─ tests/        # 自动化测试
├─ scripts/      # 构建和清理脚本
├─ docs/         # 项目说明文档
├─ releases/     # 发布成品
├─ .github/
├─ main.py
├─ pyproject.toml
└─ README.md
```

更多结构说明见 [docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)。

## 安全边界

- 不添加规避反作弊、隐藏进程、后台注入、驱动级输入或绕过权限限制的能力
- 如果目标程序屏蔽模拟输入，只提供用户提示，不尝试绕过
- 若目标程序以管理员权限运行，提示用户同样以管理员权限启动 TapLite
