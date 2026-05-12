# TapLite

[English README](README.md)

TapLite 是一个面向 Windows 的轻量级连点器，基于 Python 标准库实现：

- 使用 `tkinter` 构建桌面界面
- 使用 Windows `SendInput` 发送鼠标输入
- 使用 `RegisterHotKey` 提供全局热键
- 使用本地 `json` 保存设置

TapLite 面向普通 Windows 桌面场景，不提供反作弊绕过、进程注入、隐藏式后台自动化或权限规避能力。

## 下载

- 最新版本页面：https://github.com/wxpacc/TapLite/releases/tag/v0.3.1
- 直接下载：https://github.com/wxpacc/TapLite/releases/download/v0.3.1/TapLite.exe

## 版本

当前版本：`v0.3.1`

## 功能特性

- 支持左键、右键和中键
- 支持单击和双击
- 支持毫秒级点击间隔
- 支持无限循环或指定次数
- 支持当前位置点击或固定屏幕坐标点击
- 支持通过取点模式配置固定坐标和多点位置
- 支持多点点击列表，并为每个点设置等待时间
- 支持随机间隔和随机偏移
- 支持启动倒计时和运行时限
- 支持运行中右下角提示
- 支持系统托盘
- 支持单实例启动
- 支持自定义开始/停止热键和紧急停止热键
- 支持本地预设，保存到 `data/settings.json`

## 本地数据

- TapLite 只会把设置和预设保存在软件目录下的 `data/settings.json`。
- TapLite 不会把配置上传到任何服务器。
- TapLite 不会写入开机自启、系统服务、注册表残留项或其他常驻后台组件。
- 如果要卸载并清除全部本地数据，直接删除 TapLite 文件夹即可，不会留下额外残留。

## 从源码运行

```powershell
python main.py
```

如果目标程序以管理员权限运行，请同样以管理员权限启动 TapLite。

## 打包

```powershell
.\scripts\build.ps1
```

构建时会使用 `assets/TapLite.ico` 作为应用图标，并输出：

```text
releases\TapLite.exe
```

## 开发校验

```powershell
python -m pytest
python -m compileall main.py taplite tests
```

## 项目结构

```text
TapLite/
├─ assets/
├─ taplite/
├─ tests/
├─ scripts/
├─ docs/
├─ releases/
├─ .github/
├─ main.py
├─ pyproject.toml
└─ README.md
```

另见：[docs/PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)

## 安全边界

- 不提供反作弊绕过
- 不提供隐藏进程能力
- 不提供后台注入
- 不提供驱动级输入
- 不尝试绕过权限限制
