# 贡献指南

感谢你愿意改进 TapLite。这个项目目标是保持轻量、清晰、可维护，并遵守明确的安全边界。

## 开发环境

建议使用 Python 3.10 或更高版本：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

如果只运行现有源码，也可以直接执行：

```powershell
python main.py
```

## 分支与提交

- 主分支为 `main`。
- 新功能使用 `feature/<name>`。
- 缺陷修复使用 `fix/<name>`。
- 文档或流程更新使用 `docs/<name>`。
- 每个分支聚焦一个目标，避免混入无关改动。

提交信息保持简洁，能说明变更目的即可，例如：

```text
Add fixed-position click validation
更新中文贡献指南
```

## Pull Request 要求

提交 PR 前请确认：

- 变更范围清晰，没有混入无关格式化。
- 新行为有对应测试或手动验证说明。
- 文档与用户可见行为保持一致。
- 没有提交 `settings.json`、缓存目录、构建产物或本地虚拟环境。

## 必跑检查

```powershell
python -m pytest
python -m compileall main.py taplite tests
```

## 注释规范

注释应解释“为什么这样做”，而不是重复“代码做了什么”。适合添加注释的场景包括：

- Windows API 调用的结构体、常量或平台限制。
- 线程、热键、UI 回调之间的边界。
- 为了兼容游戏窗口、管理员权限或系统行为而做的权衡。

不需要为简单赋值、显而易见的条件判断或常规 UI 绑定添加注释。

## 安全边界

TapLite 不接受以下类型的贡献：

- 绕过反作弊或规避游戏规则。
- 驱动级输入、进程注入、隐藏进程或后台窗口注入。
- 绕过权限限制或规避系统安全策略。
- 用于未授权操作的自动化能力。
